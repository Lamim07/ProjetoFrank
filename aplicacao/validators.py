"""Input checks for uploaded text files."""

from pathlib import Path

MAX_FILE_BYTES = 1_000_000


class UploadValidationError(ValueError):
    """An uploaded file cannot be analyzed."""


def validate_upload(filename: str, data: bytes) -> None:
    if not filename or Path(filename).suffix.lower() != ".txt":
        raise UploadValidationError("Selecione um arquivo com extensão .txt.")
    if not data:
        raise UploadValidationError("O arquivo está vazio. Envie um TXT com conteúdo.")
    if len(data) > MAX_FILE_BYTES:
        raise UploadValidationError(
            "O arquivo excede o limite de 1 MB. Envie um TXT menor."
        )
