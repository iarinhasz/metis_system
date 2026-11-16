"""Transporte HTTP compartilhado pelos clientes acadêmicos."""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from time import sleep
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from redis import Redis

from projects.correction.metis.config import settings
from projects.correction.scholarly.cache import DOIResponseCache, RedisCacheClient
from projects.correction.scholarly.errors import ScholarlyClientError, ScholarlyTransientError
from projects.correction.scholarly.rate_limit import (
    PROVIDER_RATES,
    RateLimiter,
    RedisRateLimitClient,
    RedisTokenBucket,
)

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 3


class ScholarlyRedisClient(RedisCacheClient, RedisRateLimitClient, Protocol):
    pass


@dataclass(frozen=True)
class HTTPResponse:
    """Resposta HTTP mínima, independente do cliente urllib."""

    status: int
    body: bytes
    headers: dict[str, str]


class ScholarlyHTTPClient:
    """Aplica rate limit, cache por DOI, timeout e retries às APIs acadêmicas."""

    def __init__(
        self,
        provider: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        limiter: RateLimiter | None = None,
        cache: DOIResponseCache | None = None,
        redis_client: ScholarlyRedisClient | None = None,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        if provider not in PROVIDER_RATES:
            raise ValueError(f"Provedor desconhecido: {provider}")
        if timeout <= 0 or max_retries < 0:
            raise ValueError("Timeout positivo e retries não negativos são obrigatórios.")
        self.provider = provider
        self.timeout = timeout
        self.max_retries = max_retries
        if redis_client is None:
            default_redis = Redis.from_url(settings.redis_url)
            self.limiter = limiter or RedisTokenBucket(default_redis)
            self.cache = cache or DOIResponseCache(default_redis)
        else:
            self.limiter = limiter or RedisTokenBucket(redis_client)
            self.cache = cache or DOIResponseCache(redis_client)
        self.sleeper = sleeper

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int | list[str]] | None = None,
        headers: dict[str, str] | None = None,
        doi: str | None = None,
        not_found_ok: bool = False,
    ) -> HTTPResponse | None:
        request_url = f"{url}?{urlencode(params, doseq=True)}" if params else url
        cache_resource = request_url
        if doi:
            cached = self.cache.get(self.provider, doi, cache_resource)
            if cached is not None:
                return HTTPResponse(200, cached, {})

        request_headers = {"Accept": "*/*", "User-Agent": "Metis-scholarly/1"}
        request_headers.update(headers or {})
        for retry in range(self.max_retries + 1):
            request = Request(request_url, headers=request_headers)
            with self.limiter.permit(self.provider):
                self.limiter.acquire(self.provider)
                try:
                    with urlopen(request, timeout=self.timeout) as response:
                        result = HTTPResponse(
                            response.status,
                            response.read(),
                            {key.lower(): value for key, value in response.headers.items()},
                        )
                except HTTPError as exc:
                    result = HTTPResponse(
                        exc.code,
                        exc.read(),
                        {key.lower(): value for key, value in exc.headers.items()},
                    )
                except (TimeoutError, URLError, OSError) as exc:
                    if retry >= self.max_retries:
                        raise ScholarlyTransientError(
                            f"{self.provider} indisponível após {retry + 1} tentativas."
                        ) from exc
                    self._wait(retry, None)
                    continue

            if result.status == 429 or result.status >= 500:
                if retry >= self.max_retries:
                    raise ScholarlyTransientError(
                        f"{self.provider} respondeu HTTP {result.status} "
                        f"após {retry + 1} tentativas."
                    )
                self._wait(retry, result.headers.get("retry-after"))
                continue
            if result.status == 404 and not_found_ok:
                return None
            if not 200 <= result.status < 300:
                raise ScholarlyClientError(f"{self.provider} respondeu HTTP {result.status}.")
            if doi:
                self.cache.set(self.provider, doi, cache_resource, result.body)
            return result
        raise ScholarlyTransientError(f"{self.provider} excedeu as tentativas configuradas.")

    def _wait(self, retry: int, retry_after: str | None) -> None:
        delay = self._retry_after(retry_after)
        if delay is None:
            delay = min(0.5 * (2**retry), 8.0)
        self.sleeper(delay)

    @staticmethod
    def _retry_after(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                target = parsedate_to_datetime(value)
            except TypeError, ValueError, OverflowError:
                return None
            if target.tzinfo is None:
                target = target.replace(tzinfo=UTC)
            return max(0.0, (target - datetime.now(UTC)).total_seconds())


def json_payload(response: HTTPResponse) -> dict[str, Any]:
    """Parseia um objeto JSON e converte payload inválido em erro do cliente."""
    try:
        payload = json.loads(response.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ScholarlyClientError("A API acadêmica devolveu JSON inválido.") from exc
    if not isinstance(payload, dict):
        raise ScholarlyClientError("A API acadêmica devolveu um JSON que não é objeto.")
    return payload
