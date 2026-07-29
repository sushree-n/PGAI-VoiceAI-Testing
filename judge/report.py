"""Aggregate all judge outputs into a single markdown bug report."""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from judge.rubric import Finding, JudgeResult

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT / "deliverables" / "judge_outputs"
TRANSCRIPTS_DIR = ROOT / "deliverables" / "transcripts"
REPORT_PATH = ROOT / "deliverables" / "bugs" / "summary.md"

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Substrings that indicate a quote is test-framework behavior (not a PGAI logic
# bug), so it should NOT be surfaced as a cross-scenario pattern. Individual
# per-scenario findings are still kept — this only affects the aggregated
# reproducibility view.
CROSS_SCENARIO_EXCLUDE = [
    "test line",  # PGAI's handoff destination in the test env; a real deployment would transfer to a human coordinator
    "908 772 8235",  # our own Twilio caller ID — PGAI reading this back is caller-ID contamination, but "fabricated phone" mislabels it
]

# Number of leading words to use as a normalized bucket key. Merges minor
# trailing variants (e.g. "Connecting you to a representative" and
# "Connecting you to a representative. Please wait.") into one pattern.
PATTERN_PREFIX_WORDS = 6


def load_results() -> list[JudgeResult]:
    return [
        JudgeResult.model_validate_json(p.read_text())
        for p in sorted(OUTPUTS_DIR.glob("*.json"))
    ]


def _normalize_quote(q: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace, keep only leading words.
    Two quotes match if their first PATTERN_PREFIX_WORDS words are identical after cleaning.
    """
    cleaned = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", q.lower())).strip()
    return " ".join(cleaned.split()[:PATTERN_PREFIX_WORDS])


def _should_exclude_pattern(quote: str) -> bool:
    """True if this quote represents test-framework behavior, not a PGAI logic bug."""
    normalized = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", quote.lower())).strip()
    return any(marker in normalized for marker in CROSS_SCENARIO_EXCLUDE)


def _latency_stats() -> tuple[list[float], list[float]]:
    """Extract per-turn latencies from all transcripts.

    Returns (our_bot_e2e_latencies, pgai_response_gaps).

    - our_bot_e2e_latency: assistant items' metrics.e2e_latency (our full LLM→TTS turnaround)
    - pgai_response_gap: seconds between our bot's stopped_speaking_at and PGAI's next
      started_speaking_at (i.e. how long PGAI took to start responding)
    """
    our_lat: list[float] = []
    pgai_lat: list[float] = []
    for path in sorted(TRANSCRIPTS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        items = data.get("chat_history", {}).get("items", [])
        # Latencies per assistant item
        for item in items:
            if item.get("role") == "assistant":
                e2e = item.get("metrics", {}).get("e2e_latency")
                if isinstance(e2e, (int, float)):
                    our_lat.append(float(e2e))
        # PGAI response gap = next user's start - prior assistant's stop
        for prev, curr in zip(items, items[1:]):
            if prev.get("role") == "assistant" and curr.get("role") == "user":
                stopped = prev.get("metrics", {}).get("stopped_speaking_at")
                started = curr.get("metrics", {}).get("started_speaking_at")
                if isinstance(stopped, (int, float)) and isinstance(started, (int, float)):
                    gap = started - stopped
                    if 0 < gap < 30:  # sanity-clip absurd values (call setup, etc.)
                        pgai_lat.append(gap)
    return our_lat, pgai_lat


def render_report(results: list[JudgeResult]) -> str:
    lines: list[str] = ["# PGAI Voice AI — Bug Report", ""]

    all_findings: list[tuple[str, str, Finding]] = [
        (r.scenario_id, r.room_name, f) for r in results for f in r.findings
    ]
    severity_counts = Counter(f.severity for _, _, f in all_findings)
    category_counts = Counter(f.category for _, _, f in all_findings)

    # ---- Executive summary ----
    lines += [
        "## Executive Summary",
        "",
        f"- **Scenarios evaluated:** {len(results)}",
        f"- **Total findings:** {len(all_findings)}",
        f"  - HIGH: {severity_counts.get('high', 0)}",
        f"  - MEDIUM: {severity_counts.get('medium', 0)}",
        f"  - LOW: {severity_counts.get('low', 0)}",
        "- **By category:**",
    ]
    for cat, count in category_counts.most_common():
        lines.append(f"  - {cat}: {count}")
    lines.append("")

    # ---- Cross-scenario reproduction (by normalized quote) ----
    lines += [
        "## Cross-Scenario Patterns",
        "",
        "Bugs where PGAI produced the same (or near-identical) response in multiple calls — grouped by normalized quote. These are systematic defects, not one-off flakes.",
        "",
    ]
    quote_groups: dict[str, list[tuple[str, str, Finding]]] = defaultdict(list)
    for entry in all_findings:
        if _should_exclude_pattern(entry[2].quote):
            continue  # test-framework artifact; skip in cross-scenario view
        quote_groups[_normalize_quote(entry[2].quote)].append(entry)
    # Only surface patterns that appear across MULTIPLE scenarios — within-scenario
    # reproductions are already visible in the per-scenario section below.
    reproduced = [
        (k, v) for k, v in quote_groups.items()
        if len(v) >= 2 and len({e[0] for e in v}) >= 2
    ]
    if reproduced:
        for _, entries in sorted(reproduced, key=lambda x: -len(x[1])):
            scenarios = sorted({e[0] for e in entries})
            # Use the actual quote from the first finding as the header (readable)
            sample_quote = entries[0][2].quote
            sample_desc = entries[0][2].description
            lines.append(
                f"- **\"{sample_quote}\"** — {len(entries)} calls across {len(scenarios)} scenarios "
                f"({', '.join(scenarios)}). Example description: {sample_desc}"
            )
    else:
        lines.append("_No exact-quote duplicates detected._")
    lines.append("")

    # ---- Latency observations ----
    our_lat, pgai_lat = _latency_stats()
    lines += ["## Latency Observations", ""]
    if our_lat:
        lines.append(
            f"- **Our caller bot (end-to-end LLM→TTS response):** avg **{mean(our_lat):.2f}s**, "
            f"max **{max(our_lat):.2f}s** across {len(our_lat)} turns"
        )
    if pgai_lat:
        lines.append(
            f"- **PGAI receptionist (time from our bot finishing speaking to PGAI starting):** "
            f"avg **{mean(pgai_lat):.2f}s**, max **{max(pgai_lat):.2f}s** across {len(pgai_lat)} turns"
        )
    lines.append("")
    lines.append(
        "PGAI's response latency is measured from our audio stream and includes SIP+network jitter, so it is not a pure LLM-latency metric. It is provided as a soft signal, not a bug — real callers notice long pauses regardless of cause."
    )
    lines.append("")

    # ---- Per-scenario details ----
    lines += ["## Findings by Scenario", ""]
    for r in sorted(results, key=lambda x: (x.scenario_id, x.room_name)):
        lines.append(f"### `{r.scenario_id}`  \n_Call: `{r.room_name}`_")
        lines.append("")

        if not r.findings:
            lines.append("_No bugs found in this call._")
            lines.append("")
        else:
            for f in sorted(r.findings, key=lambda x: SEVERITY_ORDER[x.severity]):
                lines += [
                    f"#### Bug: {f.description}",
                    "",
                    f"- **Severity:** {f.severity.upper()}",
                    f"- **Category:** {f.category}",
                    f"- **Call:** `{r.room_name}` — turn `{f.turn_ref}`",
                    f'- **Quote (PGAI):** "{f.quote}"',
                    f"- **Expected:** {f.expected}",
                    "",
                ]

        if r.passed_criteria:
            lines.append("**PGAI handled correctly:**")
            lines.append("")
            for pc in r.passed_criteria:
                lines.append(f"- {pc}")
            lines.append("")

        if r.notes:
            lines.append(f"**Notes:** {r.notes}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results = load_results()
    print(f"Aggregating {len(results)} judge outputs...")
    REPORT_PATH.write_text(render_report(results))
    print(f"Wrote report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
