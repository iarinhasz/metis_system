"""Leitura e escrita imutável dos artefatos offline, sem chamadas externas."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from projects.correction.evals.contracts import EvaluationReport

RESULTS_DIR = Path(__file__).parent / "results"


def output_path(
    benchmark: str, *, output: Path | None = None, directory: Path = RESULTS_DIR
) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", benchmark):
        raise ValueError("Nome de benchmark inválido.")
    if output is None:
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / f"{benchmark}-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}-{uuid4().hex}.json"
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise ValueError("Escolha um arquivo novo em um diretório existente para o relatório.")
    return output


def write_artifact(report: BaseModel, path: Path) -> Path:
    # Serializa antes de abrir o destino: falha de validação não deixa arquivo vazio.
    serialized = report.model_dump_json(indent=2) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
    return path


def read_report(path: Path) -> EvaluationReport:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "format" not in data:
        # A medição histórica da 2.7 permanece intacta; a adaptação é feita em memória.
        from projects.correction.evals.profiling import BenchmarkReport, evaluation_report

        return evaluation_report(BenchmarkReport.model_validate(data), legacy=True)
    return EvaluationReport.model_validate(data)
