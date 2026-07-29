"""Load and validate scenario JSON files."""

from pathlib import Path

from .schema import Scenario

DEFINITIONS = Path(__file__).parent / "definitions"


def load(scenario_id: str) -> Scenario:
    path = DEFINITIONS / f"{scenario_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No scenario at {path}")
    scenario = Scenario.model_validate_json(path.read_text())
    if scenario.id != scenario_id:
        raise ValueError(
            f"Scenario id mismatch: file '{scenario_id}.json' declares id={scenario.id!r}"
        )
    return scenario
