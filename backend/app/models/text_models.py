# backend/app/models/text_models.py
"""
Pydantic schemas for the Text-to-Text translation endpoint.
"""

from pydantic import BaseModel, Field
from typing import Optional


class TranslationRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The source text to translate.",
        examples=["Hello, how are you?"],
    )
    source_language: str = Field(
        default="auto",
        description="BCP-47 language code of the source text, or 'auto' to detect.",
        examples=["en", "auto"],
    )
    target_language: str = Field(
        ...,
        description="BCP-47 language code for the translation output.",
        examples=["es", "fr", "de", "hi", "ja"],
    )
    provider: Optional[str] = Field(
        default=None,
        description="Override the default translation provider ('google' | 'openai').",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "Hello, how are you?",
                    "source_language": "en",
                    "target_language": "es",
                }
            ]
        }
    }


class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str          # detected or provided
    target_language: str
    provider: str                 # which backend served the request
    character_count: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "original_text": "Hello, how are you?",
                    "translated_text": "Hola, ¿cómo estás?",
                    "source_language": "en",
                    "target_language": "es",
                    "provider": "google",
                    "character_count": 19,
                }
            ]
        }
    }


class SupportedLanguagesResponse(BaseModel):
    languages: dict[str, str] = Field(
        description="Mapping of BCP-47 code → human-readable name."
    )