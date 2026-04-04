# backend/app/api/routes_text.py
"""
Text-to-Text Translation Routes
--------------------------------
POST  /api/v1/text/translate       – translate a piece of text
GET   /api/v1/text/languages       – list all supported languages
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.models.text_models import (
    TranslationRequest,
    TranslationResponse,
    SupportedLanguagesResponse,
)
from app.services.translation_service import TranslationService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── POST /translate ─────────────────────────────────────────────────────────

@router.post(
    "/translate",
    response_model=TranslationResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate text from one language to another",
    responses={
        200: {
            "description": "Translation successful",
            "content": {
                "application/json": {
                    "example": {
                        "original_text": "Hello, how are you?",
                        "translated_text": "Hola, ¿cómo estás?",
                        "source_language": "en",
                        "target_language": "es",
                        "provider": "google",
                        "character_count": 19,
                    }
                }
            },
        },
        400: {"description": "Invalid language code or empty text"},
        503: {"description": "Translation provider unavailable"},
    },
)
async def translate_text(request: TranslationRequest) -> TranslationResponse:
    """
    Translates `text` from `source_language` to `target_language`.

    - Set `source_language` to `"auto"` for automatic detection.
    - Optionally override the default provider with `"google"` or `"openai"`.

    **Example request**
    ```json
    {
      "text": "Hello, how are you?",
      "source_language": "en",
      "target_language": "es"
    }
    ```

    **Example response**
    ```json
    {
      "original_text": "Hello, how are you?",
      "translated_text": "Hola, ¿cómo estás?",
      "source_language": "en",
      "target_language": "es",
      "provider": "google",
      "character_count": 19
    }
    ```
    """
    # Basic guard: target language must be a known code
    supported = TranslationService.get_supported_languages()
    if request.target_language not in supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported target_language '{request.target_language}'. "
                "Call GET /api/v1/text/languages for the full list."
            ),
        )

    try:
        result = await TranslationService.translate(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language,
            provider=request.provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        logger.error("Translation provider error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected translation error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during translation.",
        )

    return TranslationResponse(**result)


# ── GET /languages ──────────────────────────────────────────────────────────

@router.get(
    "/languages",
    response_model=SupportedLanguagesResponse,
    summary="List all supported languages",
)
async def list_languages() -> SupportedLanguagesResponse:
    """Returns a mapping of BCP-47 language codes to human-readable names."""
    return SupportedLanguagesResponse(
        languages=TranslationService.get_supported_languages()
    )