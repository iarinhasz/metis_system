"""Validação e identificação do PDF recebido, antes de ele virar uma versão do artigo."""

import hashlib
from pathlib import PurePath

from django.core.files.uploadedfile import UploadedFile

PDF_HEADER = b"%PDF-"


class InvalidUpload(ValueError):
    """O envio foi recusado; a mensagem explica o motivo a quem enviou."""


def check_pdf(upload: UploadedFile, *, max_bytes: int) -> int:
    """Confere o tamanho e o cabeçalho do PDF e devolve o tamanho em bytes."""
    size = upload.size
    if size is None or size <= 0 or size > max_bytes:
        raise InvalidUpload("Arquivo vazio ou acima do limite de tamanho.")
    upload.seek(0)
    header = upload.read(len(PDF_HEADER))
    upload.seek(0)
    if header != PDF_HEADER:
        raise InvalidUpload("O arquivo enviado não tem cabeçalho PDF válido.")
    return size


def sha256_of(upload: UploadedFile) -> str:
    digest = hashlib.sha256()
    upload.seek(0)
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()


def safe_filename(name: str | None) -> str:
    """Só o nome do arquivo, sem pastas, com no máximo 255 caracteres."""
    return PurePath((name or "").replace("\\", "/")).name[:255] or "submission.pdf"
