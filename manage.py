#!/usr/bin/env python
"""Compatibilidade para executar o manage.py da aplicação no monorepo."""

from projects.correction.manage import main

if __name__ == "__main__":
    main()
