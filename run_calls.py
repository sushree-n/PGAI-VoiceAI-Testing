"""Dispatcher CLI: places one outbound call to the PGAI test line."""

import asyncio
from datetime import datetime

import click
from livekit import api
from livekit.api.twirp_client import ServerError

import config
from scenarios.loader import load as load_scenario

AGENT_NAME = "pgai-caller"
CALL_TIMEOUT_SECS = 600  # 10-min safety cap; real end is usually PGAI hanging up


async def place_call(scenario_id: str) -> None:
    scenario = load_scenario(scenario_id)
    room_name = f"{scenario.id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    lkapi = api.LiveKitAPI(
        url=config.LIVEKIT_URL,
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
    )

    try:
        # Scenario JSON rides along as job metadata; the agent parses it back
        # to build its persona-specific system prompt and any per-scenario overrides.
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room_name,
                metadata=scenario.model_dump_json(),
            )
        )

        print(f"[{scenario.id}] Dialing {config.TARGET_NUMBER}...")
        await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=config.LIVEKIT_SIP_TRUNK_ID,
                sip_call_to=config.TARGET_NUMBER,
                room_name=room_name,
                participant_identity="pgai-agent",
                participant_name="PGAI",
                wait_until_answered=True,
            )
        )
        print(f"[{scenario.id}] Connected. Room: {room_name}")

        # Poll for PGAI leaving the room; break early on natural hangup so we
        # don't waste minutes idling after the call actually ended. A 404 here
        # means the agent's end_call tool already deleted the room — treat as
        # end-of-call, same outcome.
        elapsed = 0
        while elapsed < CALL_TIMEOUT_SECS:
            await asyncio.sleep(3)
            elapsed += 3
            try:
                participants = await lkapi.room.list_participants(
                    api.ListParticipantsRequest(room=room_name)
                )
            except ServerError as e:
                if e.code == "not_found":
                    print(f"[{scenario.id}] Call ended (room already closed by agent).")
                    break
                raise
            if not any(p.identity == "pgai-agent" for p in participants.participants):
                print(f"[{scenario.id}] Call ended (PGAI disconnected).")
                break
        else:
            print(f"[{scenario.id}] Hit {CALL_TIMEOUT_SECS}s cap, tearing down.")
    finally:
        # Room may already be gone (end_call tool). Ignore 404; anything else
        # bubbles up. Aclose runs regardless to avoid leaking the http session.
        try:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
        except ServerError as e:
            if e.code != "not_found":
                raise
        await lkapi.aclose()


@click.command()
@click.option("--scenario", "-s", "scenario_id", required=True, help="Scenario id (matches filename in scenarios/definitions/).")
def main(scenario_id: str) -> None:
    """Place one outbound roleplay call to the PGAI test line."""
    asyncio.run(place_call(scenario_id))


if __name__ == "__main__":
    main()
