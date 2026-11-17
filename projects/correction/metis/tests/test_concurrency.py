"""O pool fecha conexões reais, saudáveis ou com tarefa encerrada por erro."""

from threading import Lock
from typing import Any

import pytest
from django.db import connection

from projects.correction.attempts.models import Article
from projects.correction.metis.concurrency import bounded_map


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("fail", [False, True])
def test_worker_connections_are_closed_after_every_task(fail: bool) -> None:
    opened: list[Any] = []
    lock = Lock()

    def work(index: int) -> int:
        Article.get_or_create_by_external_id(f"pool-{index}")
        with lock:
            opened.append(connection.connection)
        if fail and index == 1:
            raise RuntimeError("falha sintética")
        return index

    if fail:
        with pytest.raises(RuntimeError, match="sintética"):
            bounded_map(work, range(5), max_workers=2)
    else:
        assert bounded_map(work, range(5), max_workers=2) == list(range(5))
        assert Article.find_by_external_id("pool-4") is not None
    assert opened and all(handle is not None and handle.closed for handle in opened)


def test_invalid_worker_count() -> None:
    with pytest.raises(ValueError):
        bounded_map(str, [], max_workers=0)
