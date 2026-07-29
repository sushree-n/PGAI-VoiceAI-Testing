# PGAI Voice AI Testing

Outbound voice bot that dials Pretty Good AI's test line (+1-805-439-8008), roleplays as a patient across 12 test scenarios, and evaluates the receptionist agent's transcripts with an LLM-as-judge to produce a structured bug report.

**Pipeline:** Python CLI → LiveKit Agents → Twilio SIP trunk → PSTN → PGAI. STT via Deepgram Nova-3, LLM via Baseten (GLM 5.2 Fast for the caller, Kimi K3 for the judge), TTS via ElevenLabs. See [ARCHITECTURE.md](ARCHITECTURE.md) for detail.

## Prerequisites

- Python 3.13
- Accounts + API keys: **LiveKit Cloud**, **Twilio** (with an Elastic SIP Trunk), **Deepgram**, **ElevenLabs**, **Baseten** (with access to GLM 5.2 Fast and Kimi K3)
- Homebrew (for `livekit-cli`)

## Setup

**1. Clone and install**

```bash
git clone <this-repo>
cd PGAI-VoiceAI-Testing
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Environment variables**

```bash
cp .env.example .env
# Fill in every value in .env — all are required
```

**3. Create the LiveKit outbound SIP trunk** (one-time)

```bash
brew install livekit-cli
lk cloud auth   # opens browser, pick your project
```

Create `scratch/outbound-trunk.json` with your Twilio termination URI + credentials:

```json
{
  "trunk": {
    "name": "twilio-outbound",
    "address": "<your-subdomain>.pstn.twilio.com",
    "numbers": ["<your-twilio-phone-number>"],
    "auth_username": "<credential-list-username>",
    "auth_password": "<credential-list-password>"
  }
}
```

Then:

```bash
lk sip outbound create scratch/outbound-trunk.json
```

Copy the returned `SIPTrunkID` into `.env` as `LIVEKIT_SIP_TRUNK_ID`.

**4. Download local models** (one-time, ~200MB)

```bash
python -m caller.agent download-files
```

Downloads the Silero VAD and English turn-detector ONNX weights into the local HF cache.

## Run a test call

Two terminals — the LiveKit worker must be running when the dispatcher fires.

**Terminal 1 — start the agent worker (leave running):**

```bash
python -m caller.agent dev
```

**Terminal 2 — place a call:**

```bash
python run_calls.py -s <scenario-id>
```

Where `<scenario-id>` is any filename (without `.json`) from `scenarios/definitions/`. Available scenarios:

| id | Description |
|---|---|
| `appointment-booking` | Baseline: routine first-time booking |
| `sunday-booking` | Constraint violation: insist on Sunday |
| `multi-intent` | Three requests in one utterance |
| `fabrication-check` | Ask about a nonexistent appointment |
| `social-engineering` | False authority claim to book Sunday |
| `language-switch` | English → Spanish mid-call |
| `kid-caller` | 6-year-old trying to cancel mom's appointment |
| `elderly-grandma` | Confused elderly caller |
| `aria-reschedule` | Return caller reschedules existing appointment |
| `hours-and-insurance` | Info-only questions (no booking) |
| `medication-refill` | Refill request (may be out of scope) |
| `interruption-vague` | Impatient caller, vague opening, interruptions |

Per-call outputs land in `deliverables/transcripts/<scenario-id>-<timestamp>.json`. Audio + rich traces live in the LiveKit dashboard under Agents → Sessions (download the .oga bundle from there into `deliverables/recordings/`).

## Judge every transcript and generate the bug report

After running any number of calls, a **single command** produces the full evaluation:

```bash
python -m judge.batch && python -m judge.report
```

- `judge.batch` — iterates over `deliverables/transcripts/*.json`, evaluates each with Kimi K3 against the scenario's `expected_behavior`, writes per-call findings to `deliverables/judge_outputs/`. Idempotent: already-judged calls are skipped on re-run.
- `judge.report` — aggregates all judge outputs into `deliverables/bugs/summary.md` with executive summary, cross-scenario reproduction analysis, and per-scenario bug entries in the required format (Bug / Severity / Call / Details).

## Where to find deliverables

| Location | Contents |
|---|---|
| `deliverables/transcripts/` | Per-call JSON transcripts (full event log + turn-by-turn latency metrics) |
| `deliverables/recordings/` | Call audio (.oga), downloaded from LiveKit dashboard |
| `deliverables/judge_outputs/` | Per-call LLM-judge findings (JSON) |
| `deliverables/bugs/summary.md` | Aggregate bug report — the primary deliverable |

## Project layout

```
caller/agent.py          # LiveKit agent worker (STT/LLM/TTS pipeline + patient persona)
scenarios/schema.py      # Pydantic scenario model
scenarios/loader.py      # JSON scenario loader
scenarios/definitions/   # 12 scenario JSON files
run_calls.py             # Dispatcher CLI (one call per invocation)
judge/rubric.py          # Judge prompt + Finding schema
judge/judge.py           # Single-transcript judge
judge/batch.py           # Run judge over every transcript
judge/report.py          # Aggregate to markdown bug report
config.py                # Env var loading + validation
```
