import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


REQUIRED_MANIFEST_FIELDS = {
    "schema_version",
    "workflow_type",
    "name",
    "version",
    "agents",
    "steps",
    "outputs",
}


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a YAML object.")
    return parsed


def load_agent_names(agents_dir: Path) -> set[str]:
    names: set[str] = set()
    for manifest_path in sorted(agents_dir.glob("*/manifest.yaml")):
        manifest = read_yaml(manifest_path)
        name = manifest.get("name")
        if isinstance(name, str) and name:
            names.add(name)
    return names


def validate_manifest(workflow_dir: Path, agents_dir: Path, runtime_script: Path) -> None:
    manifest_path = workflow_dir / "manifest.yaml"
    manifest = read_yaml(manifest_path)

    missing = sorted(REQUIRED_MANIFEST_FIELDS - manifest.keys())
    if missing:
        raise ValueError(
            f"{manifest_path} is missing required field(s): {', '.join(missing)}"
        )

    agents = manifest["agents"]
    if not isinstance(agents, dict) or not agents:
        raise ValueError(f"{manifest_path} field 'agents' must be a non-empty object.")

    known_agent_names = load_agent_names(agents_dir)
    referenced_agent_keys = set()
    for agent_key, agent_config in agents.items():
        if not isinstance(agent_config, dict):
            raise ValueError(f"agents.{agent_key} must be an object.")

        agent_name = agent_config.get("name")
        if not isinstance(agent_name, str) or not agent_name:
            raise ValueError(f"agents.{agent_key}.name must be a non-empty string.")

        if agent_name not in known_agent_names:
            raise ValueError(
                f"agents.{agent_key}.name references '{agent_name}', but no matching "
                f"agent manifest was found under {agents_dir}."
            )

    steps = manifest["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"{manifest_path} field 'steps' must be a non-empty list.")

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"steps[{index}] must be an object.")

        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id:
            raise ValueError(f"steps[{index}].id must be a non-empty string.")

        agent_key = step.get("agent")
        if not isinstance(agent_key, str) or not agent_key:
            raise ValueError(f"steps[{index}].agent must be a non-empty string.")

        if agent_key not in agents:
            raise ValueError(
                f"steps[{index}].agent references '{agent_key}', but that key is not "
                "defined under agents."
            )
        referenced_agent_keys.add(agent_key)

    unused_agents = sorted(set(agents) - referenced_agent_keys)
    if unused_agents:
        raise ValueError(
            "Every workflow agent should be referenced by a step. Unused agent key(s): "
            + ", ".join(unused_agents)
        )

    outputs = manifest["outputs"]
    if not isinstance(outputs, dict):
        raise ValueError(f"{manifest_path} field 'outputs' must be an object.")

    for output_field in ("directory", "summary"):
        if not isinstance(outputs.get(output_field), str) or not outputs[output_field]:
            raise ValueError(f"outputs.{output_field} must be a non-empty string.")

    if not runtime_script.exists():
        raise FileNotFoundError(f"Required runtime script not found: {runtime_script}")

    print(f"Validated workflow manifest: {manifest_path}")
    print(f"Validated referenced agents: {', '.join(sorted(referenced_agent_keys))}")
    print(f"Validated runtime script: {runtime_script}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the source-controlled AI workflow manifest."
    )
    parser.add_argument(
        "--workflow-dir",
        required=True,
        help="Path to the workflow source directory, for example workflows/service-catalogue.",
    )
    parser.add_argument(
        "--agents-dir",
        default="agents",
        help="Path to the source-controlled agents directory.",
    )
    parser.add_argument(
        "--runtime-script",
        default="scripts/run-ai-source-control-workflow.py",
        help="Path to the workflow runtime script.",
    )

    args = parser.parse_args()

    try:
        validate_manifest(
            workflow_dir=Path(args.workflow_dir),
            agents_dir=Path(args.agents_dir),
            runtime_script=Path(args.runtime_script),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
