"""Batch runner: judge every transcript and persist per-scenario results."""

from pathlib import Path

from judge.judge import judge_transcript

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = ROOT / "deliverables" / "transcripts"
OUTPUTS_DIR = ROOT / "deliverables" / "judge_outputs"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    transcripts = sorted(TRANSCRIPTS_DIR.glob("*.json"))
    total = len(transcripts)
    print(f"Judging {total} transcripts...")

    for i, path in enumerate(transcripts, 1):
        out_path = OUTPUTS_DIR / path.name
        if out_path.exists():
            print(f"[{i}/{total}] {path.name} — already judged, skipping")
            continue
        print(f"[{i}/{total}] {path.name} — judging...")
        try:
            result = judge_transcript(path)
            out_path.write_text(result.model_dump_json(indent=2))
            print(
                f"    → {len(result.findings)} findings ({sum(1 for f in result.findings if f.severity == 'high')} HIGH), "
                f"{len(result.passed_criteria)} passed criteria"
            )
        except Exception as e:
            # Don't kill the batch for one bad transcript — log and continue.
            print(f"    ✗ Failed: {e}")


if __name__ == "__main__":
    main()
