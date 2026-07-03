import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Workflow manifest not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def get_agent_name(workflow: dict[str, Any], key: str, fallback: str) -> str:
    agent = workflow.get("agents", {}).get(key, {})
    return str(agent.get("name") or fallback)


def load_agent_models(agents_dir: Path) -> dict[str, str]:
    models: dict[str, str] = {}
    for manifest_path in sorted(agents_dir.glob("*/manifest.yaml")):
        manifest = read_yaml(manifest_path)
        name = manifest.get("name")
        model = manifest.get("agent", {}).get("model")
        if isinstance(name, str) and name and isinstance(model, str) and model:
            models[name] = model
    return models


def get_agent_model(agent_models: dict[str, str], agent_name: str) -> str:
    model = agent_models.get(agent_name)
    if not model:
        raise ValueError(
            f"No local agent manifest found for deployed agent '{agent_name}', "
            "or the manifest does not declare agent.model."
        )
    return model


def get_output_dir(workflow: dict[str, Any], fallback: str) -> Path:
    return Path(str(workflow.get("outputs", {}).get("directory") or fallback))


def get_summary_file(workflow: dict[str, Any], fallback: str) -> str:
    return str(workflow.get("outputs", {}).get("summary") or fallback)


def get_step_value(workflow: dict[str, Any], step_id: str, key: str, fallback: str) -> str:
    for step in workflow.get("steps", []):
        if step.get("id") == step_id:
            return str(step.get(key) or fallback)
    return fallback


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


def normalize_scan_path(value: str) -> str:
    scan_path = value.strip()
    if scan_path in {"", ".", "./"}:
        return ""
    return scan_path.strip("/")


def validate_repository_detector_output(payload: dict[str, Any]) -> None:
    repositories = payload.get("repositories")
    if not isinstance(repositories, list):
        raise ValueError("Repository detector response must contain a repositories array.")

    for index, repository in enumerate(repositories):
        if not isinstance(repository, dict):
            raise ValueError(f"repositories[{index}] must be an object.")
        if set(repository) != {"repoName", "repoURL", "repository"}:
            raise ValueError(
                f"repositories[{index}] must contain only repoName, repoURL, and repository."
            )
        if not isinstance(repository["repoName"], str) or not repository["repoName"]:
            raise ValueError(f"repositories[{index}].repoName must be a non-empty string.")
        if not isinstance(repository["repoURL"], str) or not repository["repoURL"]:
            raise ValueError(f"repositories[{index}].repoURL must be a non-empty string.")
        if not isinstance(repository["repository"], str) or not repository["repository"]:
            raise ValueError(f"repositories[{index}].repository must be a non-empty string.")


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


def validate_pull_request_output(payload: dict[str, Any]) -> None:
    required = {
        "success",
        "repository",
        "branchName",
        "commitSha",
        "pullRequestUrl",
        "pullRequestNumber",
        "filesWritten",
        "errors",
    }
    if set(payload) != required:
        raise ValueError(f"Pull request response must contain only {sorted(required)}.")
    if not isinstance(payload["success"], bool):
        raise ValueError("Pull request response success must be a boolean.")
    if not isinstance(payload["repository"], str):
        raise ValueError("Pull request response repository must be a string.")
    if not isinstance(payload["branchName"], str):
        raise ValueError("Pull request response branchName must be a string.")
    if not isinstance(payload["commitSha"], str):
        raise ValueError("Pull request response commitSha must be a string.")
    if not isinstance(payload["pullRequestUrl"], str):
        raise ValueError("Pull request response pullRequestUrl must be a string.")
    if not isinstance(payload["pullRequestNumber"], int):
        raise ValueError("Pull request response pullRequestNumber must be an integer.")
    if not isinstance(payload["filesWritten"], list):
        raise ValueError("Pull request response filesWritten must be an array.")
    if not isinstance(payload["errors"], list) or not all(
        isinstance(error, str) for error in payload["errors"]
    ):
        raise ValueError("Pull request response errors must be an array of strings.")

    file_required = {"path", "action"}
    for index, file_written in enumerate(payload["filesWritten"]):
        if not isinstance(file_written, dict):
            raise ValueError(f"filesWritten[{index}] must be an object.")
        if set(file_written) != file_required:
            raise ValueError(
                f"filesWritten[{index}] must contain only {sorted(file_required)}."
            )
        if not isinstance(file_written["path"], str) or not file_written["path"]:
            raise ValueError(f"filesWritten[{index}].path must be a non-empty string.")
        if file_written["action"] not in {"created", "updated", "unchanged"}:
            raise ValueError(f"filesWritten[{index}].action is invalid.")


def invoke_agent(
    project: AIProjectClient,
    agent_name: str,
    model: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    openai_client = project.get_openai_client(agent_name=agent_name)
    response = openai_client.responses.create(
        model=model,
        input=json.dumps(payload, separators=(",", ":")),
    )
    return parse_json_response(extract_response_text(response))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the AI source-control workflow: repository-change-detector first, "
            "then OpenAPI specs generation and pull request creation for changed repositories."
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
        "--workflow-dir",
        default="workflows/service-catalogue",
        help="Directory containing the workflow manifest.yaml.",
    )
    parser.add_argument(
        "--agents-dir",
        default="agents",
        help="Directory containing local agent manifests used to resolve deployed agent models.",
    )
    parser.add_argument(
        "--repository-agent-name",
        default=None,
        help="Deployed Foundry agent name for repository change detection.",
    )
    parser.add_argument(
        "--openapi-agent-name",
        default=None,
        help="Deployed Foundry agent name for OpenAPI spec generation.",
    )
    parser.add_argument(
        "--pr-creator-agent-name",
        default=None,
        help="Deployed Foundry agent name for creating pull requests with generated OpenAPI specs.",
    )
    parser.add_argument(
        "--project-endpoint",
        default=os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("PROJECT_ENDPOINT"),
        help="Azure AI Foundry project endpoint.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory where workflow outputs are written.",
    )

    args = parser.parse_args()

    if not args.project_endpoint:
        raise ValueError(
            "Missing project endpoint. Set AZURE_AI_PROJECT_ENDPOINT or PROJECT_ENDPOINT, "
            "or pass --project-endpoint."
        )
    scan_path = normalize_scan_path(args.scan_path)

    workflow = read_yaml(Path(args.workflow_dir) / "manifest.yaml")
    agent_models = load_agent_models(Path(args.agents_dir))

    repository_agent_name = args.repository_agent_name or get_agent_name(
        workflow, "repository_change_detector", "repository-change-detector"
    )
    openapi_agent_name = args.openapi_agent_name or get_agent_name(
        workflow, "openapi_specs_generator", "openapi-spec-generator"
    )
    pr_creator_agent_name = args.pr_creator_agent_name or get_agent_name(
        workflow, "repository_file_pr_creator", "repository-file-pr-creator"
    )
    repository_agent_model = get_agent_model(agent_models, repository_agent_name)
    openapi_agent_model = get_agent_model(agent_models, openapi_agent_name)
    pr_creator_agent_model = get_agent_model(agent_models, pr_creator_agent_name)
    output_dir = Path(args.output_dir) if args.output_dir else get_output_dir(
        workflow, "outputs/ai-source-control-workflow"
    )
    summary_file = get_summary_file(workflow, "workflow-output.json")
    specs_dir = output_dir / get_step_value(
        workflow, "generate_openapi_specs", "output_dir", "openapi-specs"
    )
    pull_requests_dir = output_dir / get_step_value(
        workflow, "create_openapi_specs_pull_request", "output_dir", "openapi-pull-requests"
    )
    detector_output_file = get_step_value(
        workflow, "detect_changed_repositories", "output", "repositories-to-update.json"
    )

    project = AIProjectClient(
        endpoint=args.project_endpoint,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )

    detector_input = {
        "manifestRepository": args.manifest_repository,
        "manifestPath": args.manifest_path,
    }
    detector_output = invoke_agent(
        project,
        repository_agent_name,
        repository_agent_model,
        detector_input,
    )
    validate_repository_detector_output(detector_output)
    write_json(output_dir / detector_output_file, detector_output)

    workflow_output: dict[str, Any] = {
        "repositories": detector_output["repositories"],
        "specs": [],
        "pullRequests": [],
    }

    for repository in detector_output["repositories"]:
        repository_name = repository["repoName"]
        repository_ref = repository["repository"]
        generator_input = {
            "repository": repository_ref,
            "scanPath": scan_path,
            "openApiTitle": repository_name,
            "openApiVersion": args.openapi_version,
        }

        openapi_output = invoke_agent(
            project,
            openapi_agent_name,
            openapi_agent_model,
            generator_input,
        )
        validate_openapi_output(openapi_output)

        repo_output = {
            "repoName": repository_name,
            "repoURL": repository["repoURL"],
            "repository": repository_ref,
            "specs": openapi_output["specs"],
            "pullRequest": None,
        }
        workflow_output["specs"].append(repo_output)

        for spec in openapi_output["specs"]:
            file_name = safe_file_name(
                spec.get("fileName", ""),
                f"{safe_file_name(repository_name, 'repository')}-openapi.yml",
            )
            spec_path = specs_dir / safe_file_name(repository_name, "repository") / file_name
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(spec["open-api"], encoding="utf-8")

        pr_input = {
            "repository": repository_ref,
            "path": "openapi-specs",
            "openApiGeneratorResponse": openapi_output,
            "pullRequestTitle": f"Add generated OpenAPI specs for {repository_name}",
            "pullRequestBody": (
                f"Generated OpenAPI specifications for {repository_name}."
            ),
        }
        pr_output = invoke_agent(
            project,
            pr_creator_agent_name,
            pr_creator_agent_model,
            pr_input,
        )
        validate_pull_request_output(pr_output)
        if not pr_output["success"]:
            errors = "; ".join(pr_output["errors"]) or "Pull request creator reported failure."
            raise ValueError(
                f"Pull request creation failed for {repository_ref}: {errors}"
            )

        repo_output["pullRequest"] = pr_output
        workflow_output["pullRequests"].append(
            {
                "repoName": repository_name,
                "repoURL": repository["repoURL"],
                "repository": repository_ref,
                "pullRequest": pr_output,
            }
        )

        pr_path = (
            pull_requests_dir
            / safe_file_name(repository_name, "repository")
            / "pull-request.json"
        )
        write_json(pr_path, pr_output)

    write_json(output_dir / summary_file, workflow_output)

    print(f"Repository detector returned {len(detector_output['repositories'])} repositories.")
    print(f"Generated specs for {len(workflow_output['specs'])} repositories.")
    print(f"Created {len(workflow_output['pullRequests'])} pull request result(s).")
    print(f"Wrote workflow output to {output_dir / summary_file}")


if __name__ == "__main__":
    main()
