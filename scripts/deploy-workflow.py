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

    args = parser.parse_args()

    if not args.project_endpoint:
        raise ValueError(
            "Missing project endpoint. Set AZURE_AI_PROJECT_ENDPOINT or PROJECT_ENDPOINT, "
            "or pass --project-endpoint."
        )

    workflow_dir = Path(args.workflow_dir)
    manifest_path = workflow_dir / "manifest.yaml"
    manifest = read_yaml(manifest_path)
    workflow_yaml = read_text(manifest_path)

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
