"""LLM-as-judge: evaluate one transcript against its scenario."""

import json
import re
from pathlib import Path

from openai import OpenAI

import config
from judge.rubric import JudgeResult, build_prompt
from scenarios.loader import load as load_scenario

DELIVERABLES = Path(__file__).resolve().parent.parent / "deliverables"


def _extract_json(text: str) -> str:
    """Strip markdown code fences or preamble the model may add before/after JSON."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    # Otherwise assume the first `{` … last `}` is the object.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model output: {text[:200]}...")
    return text[start : end + 1]


def judge_transcript(transcript_path: Path) -> JudgeResult:
    """Judge one transcript file against its scenario. Returns structured result."""
    data = json.loads(transcript_path.read_text())
    room_name = data["room"]
    scenario_id = room_name.rsplit("-", 2)[0]  # strip "-YYYYMMDD-HHMMSS"

    scenario = load_scenario(scenario_id)
    chat_history = data.get("chat_history", {}).get("items", [])

    prompt = build_prompt(
        scenario_json=scenario.model_dump_json(indent=2),
        transcript_json=json.dumps(chat_history, indent=2),
        scenario_id=scenario_id,
        room_name=room_name,
    )

    client = OpenAI(
        api_key=config.BASETEN_API_KEY,
        base_url=config.BASETEN_MODEL_URL,
    )
    response = client.chat.completions.create(
        model=config.BASETEN_JUDGE_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,  # deterministic scoring
    )
    raw = response.choices[0].message.content or ""
    return JudgeResult.model_validate_json(_extract_json(raw))


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m judge.judge <transcript.json>")
        sys.exit(1)

    result = judge_transcript(Path(sys.argv[1]))
    print(result.model_dump_json(indent=2))
