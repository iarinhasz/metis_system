"""Saúde do banco, usada pelo healthcheck do container."""

from django.db import DatabaseError, connection


def database_is_available() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return False
    return True
