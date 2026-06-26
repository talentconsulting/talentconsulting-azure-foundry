import argparse
import os
from pathlib import Path
from typing import Any

import yaml
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(read_text(path))


def build_instructions(agent_dir: Path, manifest: dict[str, Any]) -> str:
    files = manifest.get("files", {})
    instructions_file = files.get("instructions", "instructions.md")
    guardrails_file = files.get("guardrails", "guardrails.md")

    instructions = read_text(agent_dir / instructions_file)
    guardrails = read_text(agent_dir / guardrails_file)

    return f"{instructions}\n\n---\n\n{guardrails}"


def find_existing_agent(project: AIProjectClient, name: str):
    try:
        agents = project.agents.list_agents()
    except AttributeError:
        return None

    for agent in agents:
        if getattr(agent, "name", None) == name:
            return agent

    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy an Azure AI Foundry agent from split source files."
    )
    parser.add_argument(
        "--agent-dir",
        required=True,
        help="Path to the agent source directory, for example agents/repository-change-detector."
    )
    parser.add_argument(
        "--project-endpoint",
        default=os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("PROJECT_ENDPOINT"),
        help="Azure AI Foundry project endpoint."
    )
    parser.add_argument(
        "--create-new-version",
        action="store_true",
        help="Always create a new agent/version instead of trying to update an existing one."
    )

    args = parser.parse_args()

    if not args.project_endpoint:
        raise ValueError(
            "Missing project endpoint. Set AZURE_AI_PROJECT_ENDPOINT or PROJECT_ENDPOINT, "
            "or pass --project-endpoint."
        )

    agent_dir = Path(args.agent_dir)
    manifest = read_yaml(agent_dir / "manifest.yaml")
    tools_config = read_yaml(agent_dir / manifest.get("files", {}).get("tools", "tools.yaml"))

    agent_name = manifest["name"]
    model = manifest["agent"]["model"]
    instructions = build_instructions(agent_dir, manifest)
    response_format = manifest["outputs"]
    tools = tools_config.get("tools", [])

    project = AIProjectClient(
        endpoint=args.project_endpoint,
        credential=DefaultAzureCredential()
    )

    existing_agent = None if args.create_new_version else find_existing_agent(project, agent_name)

    if existing_agent and hasattr(project.agents, "update_agent"):
        updated_agent = project.agents.update_agent(
            assistant_id=existing_agent.id,
            model=model,
            name=agent_name,
            instructions=instructions,
            tools=tools,
            response_format=response_format,
        )
        print(f"Updated agent: {updated_agent.id}")
    else:
        created_agent = project.agents.create_agent(
            model=model,
            name=agent_name,
            instructions=instructions,
            tools=tools,
            response_format=response_format,
        )
        if existing_agent:
            print(f"Created new agent because update_agent is not available in this SDK version: {created_agent.id}")
        else:
            print(f"Created agent: {created_agent.id}")


if __name__ == "__main__":
    main()
