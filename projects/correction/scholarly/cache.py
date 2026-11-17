"""Cache Redis de respostas acadêmicas associadas a DOI."""

import hashlib
from typing import Protocol
from urllib.parse import unquote


class RedisCacheClient(Protocol):
    def get(self, name: str) -> bytes | str | None: ...

    def set(self, name: str, value: bytes, ex: int | None = None) -> object: ...


def normalize_doi(doi: str) -> str:
    """Normaliza formas comuns de DOI para uma chave estável."""
    normalized = unquote(doi.strip())
    lowered = normalized.lower()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if lowered.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    normalized = normalized.strip().strip("/").lower()
    if not normalized:
        raise ValueError("O DOI não pode ser vazio.")
    return normalized


class DOIResponseCache:
    """Armazena apenas corpos de respostas bem-sucedidas, separados por provedor."""

    def __init__(
        self, client: RedisCacheClient, *, ttl_seconds: int = 86_400, prefix: str = "metis"
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("O TTL do cache deve ser positivo.")
        self.client = client
        self.ttl_seconds = ttl_seconds
        self.prefix = prefix

    def _key(self, provider: str, doi: str, resource: str) -> str:
        digest = hashlib.sha256(resource.encode()).hexdigest()
        return f"{self.prefix}:scholarly:doi:{provider}:{normalize_doi(doi)}:{digest}"

    def get(self, provider: str, doi: str, resource: str) -> bytes | None:
        value = self.client.get(self._key(provider, doi, resource))
        return value.encode() if isinstance(value, str) else value

    def set(self, provider: str, doi: str, resource: str, body: bytes) -> None:
        self.client.set(self._key(provider, doi, resource), body, ex=self.ttl_seconds)
