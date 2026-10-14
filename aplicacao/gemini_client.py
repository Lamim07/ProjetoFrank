"""Small boundary around the Gemini API."""

import os
import re
from typing import Any

from .models import gemini_response_schema


class GeminiError(RuntimeError):
    """A safe, user-facing Gemini failure."""


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        sdk_client: Any | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self._sdk_client = sdk_client

    def analyze(self, prompt: str, schema: dict | None = None) -> str:
        if not self.api_key.strip() and self._sdk_client is None:
            raise GeminiError(
                "A chave Gemini não está configurada. Defina GEMINI_API_KEY no ambiente."
            )
        try:
            from google import genai
            from google.genai import errors
        except ImportError as exc:
            raise GeminiError(
                "O SDK Gemini não está instalado. Instale as dependências do projeto."
            ) from exc

        try:
            client = self._sdk_client or genai.Client(api_key=self.api_key)
            try:
                interaction = client.interactions.create(
                    model=self.model,
                    input=prompt,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": schema or gemini_response_schema(),
                    },
                )
            except Exception as exc:
                code, body = _error_status(exc)
                if not _is_format_error(code, body):
                    raise
                # Some model/API combinations reject structured response_format.
                # The prompt still requests JSON; Pydantic validates the result.
                interaction = client.interactions.create(model=self.model, input=prompt)
        except errors.APIError as exc:
            raise GeminiError(
                _status_message(exc.code, getattr(exc, "details", None), self.api_key)
            ) from exc
        except (TimeoutError, ConnectionError) as exc:
            raise GeminiError(
                "A conexão com o Gemini falhou. Verifique a rede e tente novamente."
            ) from exc
        except Exception as exc:
            code, body = _error_status(exc)
            if code is not None:
                raise GeminiError(_status_message(code, body, self.api_key)) from exc
            raise GeminiError(
                f"Falha inesperada ao chamar o Gemini ({type(exc).__name__})."
            ) from exc

        response = getattr(interaction, "output_text", None)
        if not response or not response.strip():
            raise GeminiError("O Gemini retornou uma resposta vazia. Tente novamente.")
        return response


def _status_message(code: int | None, body: object = None, api_key: str = "") -> str:
    if code in (401, 403):
        return "A chave Gemini foi recusada. Verifique a chave e as permissões do projeto."
    if code == 429:
        return "O limite de uso do Gemini foi atingido. Tente novamente mais tarde."
    if code == 400:
        detail = body.get("error", body) if isinstance(body, dict) else {}
        reason = str(detail.get("message", "")).lower() if isinstance(detail, dict) else ""
        if "api key" in reason or "api_key" in reason:
            return "A chave Gemini parece inválida ou bloqueada (HTTP 400). Gere uma nova chave no Google AI Studio."
        if "model" in reason:
            return "O Gemini recusou o modelo configurado (HTTP 400). Verifique GEMINI_MODEL."
        if "schema" in reason or "response_format" in reason or "json" in reason:
            detail_text = str(detail.get("message", "")) if isinstance(detail, dict) else ""
            if api_key:
                detail_text = detail_text.replace(api_key, "[chave oculta]")
            detail_text = re.sub(r"AIza[A-Za-z0-9_-]{20,}", "[chave oculta]", detail_text)
            detail_text = " ".join(detail_text.split())[:280]
            return f"O Gemini recusou o formato da resposta (HTTP 400). Detalhe: {detail_text}"
        return "O Gemini recusou a requisição (HTTP 400). Verifique a chave, o modelo e o formato solicitado."
    if code == 404:
        return "O modelo Gemini configurado não foi encontrado (HTTP 404)."
    if code in (500, 502, 503, 504):
        return "O Gemini está indisponível no momento. Tente novamente."
    return f"O Gemini recusou a análise (HTTP {code})." if code else "Não foi possível concluir a análise com o Gemini."


def _is_format_error(code: int | None, body: object) -> bool:
    if code != 400 or not isinstance(body, dict):
        return False
    detail = body.get("error", body)
    if not isinstance(detail, dict):
        return False
    reason = str(detail.get("message", "")).lower()
    return any(term in reason for term in ("schema", "response_format", "json"))


def _error_status(exc: Exception) -> tuple[int | None, object]:
    """Support both legacy SDK errors and Interactions API status errors."""
    code = getattr(exc, "status_code", None)
    if code is None:
        code = getattr(exc, "code", None)
    body = getattr(exc, "body", None)
    if body is None:
        body = getattr(exc, "details", None)
    return (code if isinstance(code, int) else None, body)
