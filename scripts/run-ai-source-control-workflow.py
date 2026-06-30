import argparse
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(text)

    if parts:
        return "\n".join(parts)

    return str(response)


def parse_json_response(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def safe_file_name(value: str, fallback: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-").lower()
    return candidate or fallback


def repository_from_url(repo_url: str, repo_name: str) -> str:
    parsed = urlparse(repo_url)
    if parsed.netloc.lower() == "github.com":
        path = parsed.path.strip("/").removesuffix(".git")
        if path.count("/") >= 1:
            return path
    return repo_name


def validate_repository_detector_output(payload: dict[str, Any]) -> None:
    repositories = payload.get("repositories")
    if not isinstance(repositories, list):
        raise ValueError("Repository detector response must contain a repositories array.")

    for index, repository in enumerate(repositories):
        if not isinstance(repository, dict):
            raise ValueError(f"repositories[{index}] must be an object.")
        if set(repository) != {"repoName", "repoURL"}:
            raise ValueError(
                f"repositories[{index}] must contain only repoName and repoURL."
            )
        if not isinstance(repository["repoName"], str) or not repository["repoName"]:
            raise ValueError(f"repositories[{index}].repoName must be a non-empty string.")
        if not isinstance(repository["repoURL"], str) or not repository["repoURL"]:
            raise ValueError(f"repositories[{index}].repoURL must be a non-empty string.")


def validate_openapi_output(payload: dict[str, Any]) -> None:
    specs = payload.get("specs")
    if not isinstance(specs, list):
        raise ValueError("OpenAPI generator response must contain a specs array.")

    required = {"domain-api", "open-api", "fileName", "serviceName", "sourcePath", "contentType"}
    for index, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise ValueError(f"specs[{index}] must be an object.")
        if set(spec) != required:
            raise ValueError(f"specs[{index}] must contain only {sorted(required)}.")
        if spec["contentType"] != "application/yaml":
            raise ValueError(f"specs[{index}].contentType must be application/yaml.")
        if not isinstance(spec["open-api"], str) or not spec["open-api"].strip():
            raise ValueError(f"specs[{index}].open-api must be a non-empty string.")


def validate_review_output(payload: dict[str, Any]) -> None:
    required = {
        "domain-api",
        "fileName",
        "valid",
        "severity",
        "recommendedAction",
        "summary",
        "findings",
    }
    if set(payload) != required:
        raise ValueError(f"Review response must contain only {sorted(required)}.")
    if not isinstance(payload["domain-api"], str) or not payload["domain-api"]:
        raise ValueError("Review response domain-api must be a non-empty string.")
    if not isinstance(payload["fileName"], str) or not payload["fileName"]:
        raise ValueError("Review response fileName must be a non-empty string.")
    if not isinstance(payload["valid"], bool):
        raise ValueError("Review response valid must be a boolean.")
    if payload["severity"] not in {"none", "low", "medium", "high"}:
        raise ValueError("Review response severity is invalid.")
    if payload["recommendedAction"] not in {"accept", "review", "regenerate"}:
        raise ValueError("Review response recommendedAction is invalid.")
    if not isinstance(payload["summary"], str):
        raise ValueError("Review response summary must be a string.")
    if not isinstance(payload["findings"], list):
        raise ValueError("Review response findings must be an array.")

    finding_required = {"category", "severity", "message", "path"}
    for index, finding in enumerate(payload["findings"]):
        if not isinstance(finding, dict):
            raise ValueError(f"findings[{index}] must be an object.")
        if set(finding) != finding_required:
            raise ValueError(f"findings[{index}] must contain only {sorted(finding_required)}.")
        if finding["severity"] not in {"low", "medium", "high"}:
            raise ValueError(f"findings[{index}].severity is invalid.")


def invoke_agent(project: AIProjectClient, agent_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    openai_client = project.get_openai_client(agent_name=agent_name)
    response = openai_client.responses.create(
        model=agent_name,
        input=json.dumps(payload, separators=(",", ":")),
    )
    return parse_json_response(extract_response_text(response))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the AI source-control workflow: repository-change-detector first, "
            "then OpenAPI specs generation for changed repositories."
        )
    )
    parser.add_argument(
        "--manifest-repository",
        required=True,
        help="GitHub repository containing the manifest, for example TalentConsulting/DomainExplorer.",
    )
    parser.add_argument(
        "--manifest-path",
        required=True,
        help="Path to the manifest file within the repository, for example repoManifest.json.",
    )
    parser.add_argument(
        "--scan-path",
        default=".",
        help="Path passed to the OpenAPI specs generator for each changed repository.",
    )
    parser.add_argument(
        "--openapi-version",
        default="1.0.0",
        help="Default OpenAPI info.version passed to the specs generator.",
    )
    parser.add_argument(
        "--repository-agent-name",
        default="repository-change-detector",
        help="Deployed Foundry agent name for repository change detection.",
    )
    parser.add_argument(
        "--openapi-agent-name",
        default="openapi-spec-generator",
        help="Deployed Foundry agent name for OpenAPI spec generation.",
    )
    parser.add_argument(
        "--reviewer-agent-name",
        default="openapi-spec-reviewer",
        help="Deployed Foundry agent name for reviewing generated OpenAPI specs.",
    )
    parser.add_argument(
        "--project-endpoint",
        default=os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("PROJECT_ENDPOINT"),
        help="Azure AI Foundry project endpoint.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/ai-source-control-workflow",
        help="Directory where workflow outputs are written.",
    )

    args = parser.parse_args()

    if not args.project_endpoint:
        raise ValueError(
            "Missing project endpoint. Set AZURE_AI_PROJECT_ENDPOINT or PROJECT_ENDPOINT, "
            "or pass --project-endpoint."
        )

    output_dir = Path(args.output_dir)
    specs_dir = output_dir / "openapi-specs"

    project = AIProjectClient(
        endpoint=args.project_endpoint,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )

    detector_input = {
        "manifestRepository": args.manifest_repository,
        "manifestPath": args.manifest_path,
    }
    detector_output = invoke_agent(project, args.repository_agent_name, detector_input)
    validate_repository_detector_output(detector_output)
    write_json(output_dir / "repositories-to-update.json", detector_output)

    workflow_output: dict[str, Any] = {
        "repositories": detector_output["repositories"],
        "specs": [],
        "reviews": [],
    }

    for repository in detector_output["repositories"]:
        repository_name = repository["repoName"]
        repository_ref = repository_from_url(repository["repoURL"], repository_name)
        generator_input = {
            "repository": repository_ref,
            "scanPath": args.scan_path,
            "openApiTitle": repository_name,
            "openApiVersion": args.openapi_version,
        }

        openapi_output = invoke_agent(project, args.openapi_agent_name, generator_input)
        validate_openapi_output(openapi_output)

        repo_output = {
            "repoName": repository_name,
            "repoURL": repository["repoURL"],
            "repository": repository_ref,
            "specs": openapi_output["specs"],
            "reviews": [],
        }
        workflow_output["specs"].append(repo_output)

        for spec in openapi_output["specs"]:
            review_input = {
                "repoName": repository_name,
                "repoURL": repository["repoURL"],
                **spec,
            }
            review_output = invoke_agent(project, args.reviewer_agent_name, review_input)
            validate_review_output(review_output)

            repo_output["reviews"].append(review_output)
            workflow_output["reviews"].append(
                {
                    "repoName": repository_name,
                    "repoURL": repository["repoURL"],
                    "repository": repository_ref,
                    "review": review_output,
                }
            )

            file_name = safe_file_name(
                spec.get("fileName", ""),
                f"{safe_file_name(repository_name, 'repository')}-openapi.yml",
            )
            spec_path = specs_dir / safe_file_name(repository_name, "repository") / file_name
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(spec["open-api"], encoding="utf-8")

            review_path = (
                output_dir
                / "openapi-reviews"
                / safe_file_name(repository_name, "repository")
                / f"{file_name}.review.json"
            )
            write_json(review_path, review_output)

    write_json(output_dir / "workflow-output.json", workflow_output)

    print(f"Repository detector returned {len(detector_output['repositories'])} repositories.")
    print(f"Generated specs for {len(workflow_output['specs'])} repositories.")
    print(f"Reviewed {len(workflow_output['reviews'])} generated specs.")
    print(f"Wrote workflow output to {output_dir / 'workflow-output.json'}")


if __name__ == "__main__":
    main()
