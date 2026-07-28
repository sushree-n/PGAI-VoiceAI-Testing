"""LiveKit agent worker: patient roleplay bot for outbound PGAI calls."""

import json
from pathlib import Path

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, elevenlabs, openai, silero
from livekit.plugins.turn_detector.english import EnglishModel

import config

PATIENT_INSTRUCTIONS = """You are a patient calling a healthcare clinic to learn what services they offer.
You have no immediate medical issue — you're just curious what the clinic does.

Wait for the receptionist to greet you first. Then:
1. Politely say you're just calling to ask what services the clinic offers.
2. Listen to their answer. Ask AT MOST one short follow-up question if something is unclear.
3. Thank them and say goodbye. Keep the whole call under two minutes.

Speak like a real person on the phone: short, natural, one or two sentences per turn."""

DELIVERABLES = Path(__file__).resolve().parent.parent / "deliverables"


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", api_key=config.DEEPGRAM_API_KEY),
        llm=openai.LLM(
            model=config.BASETEN_MODEL_NAME,
            base_url=config.BASETEN_MODEL_URL,
            api_key=config.BASETEN_API_KEY,
        ),
        tts=elevenlabs.TTS(
            voice_id=config.ELEVENLABS_VOICE_ID,
            api_key=config.ELEVENLABS_API_KEY,
            model="eleven_flash_v2_5",
        ),
        vad=silero.VAD.load(),
        turn_detection=EnglishModel(),
    )

    async def _flush():
        # Full session report: turns + timestamps + latencies + recording metadata.
        # Audio bytes stay in LiveKit observability (downloadable from dashboard).
        report = ctx.make_session_report()
        transcript_path = DELIVERABLES / "transcripts" / f"{ctx.room.name}.json"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(json.dumps(report.to_dict(), indent=2))

    ctx.add_shutdown_callback(_flush)

    # No generate_reply() — bot listens; PGAI greets first, session replies after.
    await session.start(
        agent=Agent(instructions=PATIENT_INSTRUCTIONS),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="pgai-caller"))
