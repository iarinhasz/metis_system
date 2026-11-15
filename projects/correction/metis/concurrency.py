"""Pool com fila limitada e descarte das conexões abertas por cada tarefa."""

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, connections


def bounded_map[T, R](fn: Callable[[T], R], items: Iterable[T], max_workers: int) -> list[R]:
    """Preserva a ordem e espera a limpeza das tarefas em andamento mesmo numa falha."""
    if max_workers < 1:
        raise ValueError("max_workers deve ser maior que zero.")

    def invoke(item: T) -> R:
        try:
            close_old_connections()
            return fn(item)
        finally:
            # close_old_connections sozinho mantém conexões saudáveis abertas.
            connections.close_all()

    executor = ThreadPoolExecutor(max_workers=max_workers)
    try:
        return list(executor.map(invoke, items, buffersize=max_workers))
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
