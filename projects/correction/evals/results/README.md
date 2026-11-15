# Relatórios locais

Os comandos offline gravam aqui por padrão, somente com `--execute`. Cada execução
gera um arquivo JSON novo, sem sobrescrever medições anteriores. JSONs gerados
ficam fora do Git; para publicar uma medição revisada, escolha um destino explícito
com `--output` e registre a origem dos dados.

O contrato comum está em `evals/contracts.py`; a operação e a comparação estão
descritas em [Evals offline](../../../../docs/evals.md).
