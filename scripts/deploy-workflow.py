import argparse
import os
from pathlib import Path
from typing import Any

import yaml
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(read_text(path))


def resolve_workflow_source(workflow_dir: Path, manifest: dict[str, Any]) -> Path:
    workflow_file = manifest.get("files", {}).get("workflow", "workflow.yaml")
    workflow_path = workflow_dir / workflow_file
    if not workflow_path.exists():
        raise FileNotFoundError(
            "Deployable Foundry workflow YAML was not found. "
            f"Expected {workflow_path}. The source-control manifest is not the same "
            "as the CSDL workflow body required by Azure AI Foundry."
        )
    return workflow_path


def validate_workflow_yaml(workflow_yaml: str, workflow_path: Path) -> None:
    parsed = yaml.safe_load(workflow_yaml)
    if not isinstance(parsed, dict):
        raise ValueError(
            f"{workflow_path} must contain the deployable Azure AI Foundry CSDL workflow YAML. "
            "The current file is empty, comments-only, or not a YAML object."
        )

    if "schema_version" in parsed or "workflow_type" in parsed:
        raise ValueError(
            f"{workflow_path} appears to contain the source-control manifest shape, "
            "not the Azure AI Foundry CSDL workflow body."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy an Azure AI Foundry workflow from a workflow manifest."
    )
    parser.add_argument(
        "--workflow-dir",
        required=True,
        help="Path to the workflow source directory, for example workflows/service-catalogue.",
    )
    parser.add_argument(
        "--project-endpoint",
        default=os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("PROJECT_ENDPOINT"),
        help="Azure AI Foundry project endpoint.",
    )
    parser.add_argument(
        "--generated-workflow",
        default=None,
        help="Optional path to write the generated Foundry workflow YAML before deployment.",
    )

    args = parser.parse_args()

    if not args.project_endpoint:
        raise ValueError(
            "Missing project endpoint. Set AZURE_AI_PROJECT_ENDPOINT or PROJECT_ENDPOINT, "
            "or pass --project-endpoint."
        )

    workflow_dir = Path(args.workflow_dir)
    manifest_path = workflow_dir / "manifest.yaml"
    manifest = read_yaml(manifest_path)
    workflow_path = resolve_workflow_source(workflow_dir, manifest)
    workflow_yaml = read_text(workflow_path)
    validate_workflow_yaml(workflow_yaml, workflow_path)

    if args.generated_workflow:
        generated_path = Path(args.generated_workflow)
        generated_path.parent.mkdir(parents=True, exist_ok=True)
        generated_path.write_text(workflow_yaml, encoding="utf-8")

    workflow_name = manifest["name"]
    definition = {
        "kind": "workflow",
        "workflow": workflow_yaml,
    }

    project = AIProjectClient(
        endpoint=args.project_endpoint,
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )

    created_workflow = project.agents.create_version(
        agent_name=workflow_name,
        definition=definition,
        description=manifest.get("description"),
        metadata={
            "version": str(manifest.get("version", "1.0.0")),
            "display_name": str(manifest.get("display_name", workflow_name)),
            "workflow_type": str(manifest.get("workflow_type", "workflow")),
        },
    )

    print(f"Created workflow version: {created_workflow}")


if __name__ == "__main__":
    main()
