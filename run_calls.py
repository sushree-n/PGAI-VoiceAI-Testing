"""Dispatcher CLI: places one outbound call to the PGAI test line."""

import asyncio
from datetime import datetime

import click
from livekit import api

import config

AGENT_NAME = "pgai-caller"
CALL_TIMEOUT_SECS = 180


async def place_call() -> None:
    room_name = f"pgai-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    lkapi = api.LiveKitAPI(
        url=config.LIVEKIT_URL,
        api_key=config.LIVEKIT_API_KEY,
        api_secret=config.LIVEKIT_API_SECRET,
    )

    try:
        # 1. Dispatch the caller agent into the room (it joins and waits for audio).
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(agent_name=AGENT_NAME, room=room_name)
        )

        # 2. Dial PGAI via the Twilio SIP trunk; blocks until the call is answered.
        print(f"Dialing {config.TARGET_NUMBER}...")
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
        print(f"Connected. Room: {room_name}")

        # 3. Hard cap so the call can't run forever.
        await asyncio.sleep(CALL_TIMEOUT_SECS)
        print(f"Hit {CALL_TIMEOUT_SECS}s cap, tearing down.")
    finally:
        # Deleting the room disconnects everyone (agent + SIP participant).
        await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
        await lkapi.aclose()


@click.command()
def main() -> None:
    """Place one outbound roleplay call to the PGAI test line."""
    asyncio.run(place_call())


if __name__ == "__main__":
    main()
