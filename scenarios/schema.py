"""Scenario schema: what a scripted patient roleplay looks like."""

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    id: str = Field(..., description="Kebab-case unique id, e.g. 'schedule-sunday'")
    title: str = Field(..., description="Human-readable name")
    persona: str = Field(..., description="Who the patient is: name, age, personality, backstory")
    goal: str = Field(..., description="What the patient is trying to accomplish on this call")
    context: str | None = Field(None, description="Medical background or situational context")
    hidden_info: dict[str, str] = Field(
        default_factory=dict,
        description="Info the patient knows but only reveals when explicitly asked (DOB, insurance, etc.)",
    )
    expected_behavior: str = Field(
        ...,
        description="What the PGAI agent should do to handle this correctly — feeds the judge",
    )
    voice_id: str | None = Field(None, description="Override ELEVENLABS_VOICE_ID for this scenario")
    tts_model: str | None = Field(None, description="Override the default ElevenLabs TTS model")
