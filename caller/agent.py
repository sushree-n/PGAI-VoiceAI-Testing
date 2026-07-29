"""LiveKit agent worker: patient roleplay bot for outbound PGAI calls."""

import json
from pathlib import Path

from livekit import api
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool
from livekit.plugins import deepgram, elevenlabs, openai, silero
from livekit.plugins.turn_detector.english import EnglishModel

import config
from scenarios.schema import Scenario

DELIVERABLES = Path(__file__).resolve().parent.parent / "deliverables"

PROMPT_TEMPLATE = """You are {persona}.

You are calling a healthcare clinic. What you want to accomplish on this call: {goal}
{context_block}{hidden_info_block}
HOW TO BEHAVE:
- Wait for them to greet you before you say anything.
- Speak like a real person on the phone: one or two short sentences per turn, natural pacing.
- When saying phone numbers, spelling names, or reading dates aloud, separate digits and letters with spaces, not hyphens. Say "four one five, five five five, zero one four two" or "C H E N" — never "four-one-five" or "C-H-E-N" (hyphens sound wrong when spoken).
- Answer only what's asked. Do not volunteer information they haven't requested.
- If the agent states something specific and wrong about you (a birthday, name, phone number, insurance), correct them — a real person would notice and speak up.
- If they ask something outside what you know about yourself, improvise plausibly — you're a real person with a real life.
- When your goal is achieved or the call clearly can't go further, thank them politely and say goodbye — then call the `end_call` tool in the SAME turn to actually hang up. Do not narrate hanging up in words like "*hangs up*"; do not say goodbye and then keep talking; invoke the tool.

Stay fully in character throughout the call. You are the person described above, calling with a genuine need. Never mention AI, bots, testing, or simulations, even if challenged."""


def build_prompt(scenario: Scenario) -> str:
    context_block = f"\nBackground: {scenario.context}\n" if scenario.context else ""
    if scenario.hidden_info:
        lines = "\n".join(f"- {k}: {v}" for k, v in scenario.hidden_info.items())
        hidden_info_block = (
            "\nInformation about yourself to share ONLY when specifically asked "
            f"(do not volunteer any of this):\n{lines}\n"
        )
    else:
        hidden_info_block = ""
    return PROMPT_TEMPLATE.format(
        persona=scenario.persona,
        goal=scenario.goal,
        context_block=context_block,
        hidden_info_block=hidden_info_block,
    )


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    scenario = Scenario.model_validate_json(ctx.job.metadata)
    room_name = ctx.room.name  # captured for end_call tool

    @function_tool
    async def end_call() -> None:
        """Hang up the call. Use this ONLY after you have said goodbye and the conversation is genuinely complete or dead-ended."""
        lkapi = api.LiveKitAPI(
            url=config.LIVEKIT_URL,
            api_key=config.LIVEKIT_API_KEY,
            api_secret=config.LIVEKIT_API_SECRET,
        )
        try:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
        finally:
            await lkapi.aclose()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", api_key=config.DEEPGRAM_API_KEY),
        llm=openai.LLM(
            model=config.BASETEN_MODEL_NAME,
            base_url=config.BASETEN_MODEL_URL,
            api_key=config.BASETEN_API_KEY,
        ),
        tts=elevenlabs.TTS(
            voice_id=scenario.voice_id or config.ELEVENLABS_VOICE_ID,
            api_key=config.ELEVENLABS_API_KEY,
            model=scenario.tts_model or "eleven_flash_v2_5",
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
        agent=Agent(instructions=build_prompt(scenario), tools=[end_call]),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="pgai-caller"))
