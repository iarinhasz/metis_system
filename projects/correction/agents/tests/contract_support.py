"""Entradas sintéticas e clientes usados apenas pelo spike, sem dados de artigos."""

import json
from typing import Any, Literal

from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from pydantic import BaseModel

from projects.correction.agents.tests.http_stub import Response

type Provider = Literal["openai", "google"]


class Finding(BaseModel):
    label: Literal["valid", "invalid"]
    reason: str


class ContractAnswer(BaseModel):
    findings: list[Finding]
    language: Literal["pt", "en"]


ANSWER = ContractAnswer(findings=[Finding(label="valid", reason="Teste sintético.")], language="pt")
PROMPT = (
    'Responda em português: findings=[{label: "valid", reason: "Teste sintético."}], language="pt".'
)


def model(
    provider: Provider,
    *,
    key: str = "chave-sintetica",
    url: str | None = None,
    model_id: str | None = None,
    timeout: float = 5,
    retries: int = 0,
) -> OpenAIChat | Gemini:
    if provider == "openai":
        return OpenAIChat(
            id=model_id or "gpt-5.4-nano",
            api_key=key,
            base_url=f"{url}/v1" if url else None,
            timeout=timeout,
            max_retries=0,  # O retry da SDK não pode multiplicar o do Agno.
            retries=retries,
            delay_between_retries=0,
            exponential_backoff=True,
        )
    http_options: dict[str, Any] = {
        "timeout": max(1, int(timeout * 1000)),
        "retry_options": {"attempts": 1},
    }
    if url:
        http_options["base_url"] = url
    return Gemini(
        id=model_id or "gemini-2.5-flash",
        api_key=key,
        timeout=timeout,
        client_params={"http_options": http_options},
        retries=retries,
        delay_between_retries=0,
        exponential_backoff=True,
    )


def agent(provider_model: OpenAIChat | Gemini) -> Agent:
    return Agent(
        model=provider_model,
        output_schema=ContractAnswer,
        telemetry=False,
        store_media=False,
        retries=0,
    )


def answer(provider: Provider, text: str | None = None) -> Response:
    content = ANSWER.model_dump_json() if text is None else text
    if provider == "openai":
        return Response(
            {
                "id": "chatcmpl-spike",
                "object": "chat.completion",
                "created": 1,
                "model": "gpt-5.4-nano",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 5,
                    "total_tokens": 25,
                    "prompt_tokens_details": {"cached_tokens": 4},
                },
            }
        )
    return Response(
        {
            "candidates": [
                {
                    "content": {"role": "model", "parts": [{"text": content}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 20,
                "candidatesTokenCount": 5,
                "totalTokenCount": 25,
                "cachedContentTokenCount": 4,
            },
        }
    )


def error(provider: Provider, status: int) -> Response:
    payload: dict[str, Any]
    if provider == "openai":
        payload = {"error": {"message": "Falha sintética", "type": "api_error", "code": None}}
    else:
        payload = {"error": {"code": status, "message": "Falha sintética", "status": "UNKNOWN"}}
    return Response(payload, status)


def assert_usage(run: Any, *, exact: bool = False) -> None:
    assert run.content == ANSWER
    assert run.metrics is not None
    assert run.metrics.input_tokens > 0 and run.metrics.output_tokens > 0
    assert run.metrics.duration is not None and run.metrics.duration >= 0
    assert run.metrics.cache_read_tokens >= 0
    if exact:
        assert (run.metrics.input_tokens, run.metrics.output_tokens) == (20, 5)
        assert run.metrics.cache_read_tokens == 4


def sent_schema(request: dict[str, Any]) -> str:
    return json.dumps(request.get("response_format") or request.get("generationConfig"))
