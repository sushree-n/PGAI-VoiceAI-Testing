"""Typed configuration loaded from environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


LIVEKIT_URL: str = _require("LIVEKIT_URL")
LIVEKIT_API_KEY: str = _require("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET: str = _require("LIVEKIT_API_SECRET")

LIVEKIT_SIP_TRUNK_ID: str = _require("LIVEKIT_SIP_TRUNK_ID")

TWILIO_ACCOUNT_SID: str = _require("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN: str = _require("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER: str = _require("TWILIO_PHONE_NUMBER")

TARGET_NUMBER: str = _require("TARGET_NUMBER")

DEEPGRAM_API_KEY: str = _require("DEEPGRAM_API_KEY")

ELEVENLABS_API_KEY: str = _require("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID: str = _require("ELEVENLABS_VOICE_ID")

BASETEN_API_KEY: str = _require("BASETEN_API_KEY")
BASETEN_MODEL_URL: str = _require("BASETEN_MODEL_URL")
BASETEN_MODEL_NAME: str = _require("BASETEN_MODEL_NAME")
BASETEN_JUDGE_MODEL_NAME: str = _require("BASETEN_JUDGE_MODEL_NAME")