"""Decode TXT uploads without executing their content."""

from .validators import UploadValidationError


def read_text(data: bytes) -> str:
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UploadValidationError(
            "Não foi possível ler o arquivo como UTF-8. Converta-o para UTF-8 e tente novamente."
        ) from exc
    if not content.strip():
        raise UploadValidationError("O arquivo não contém texto para analisar.")
    return content
