"""Uso: copie um JSON {rótulo: run_id} para /tmp/runs.json no container web e rode
`docker compose exec -T web python manage.py shell < scripts/collect.py`; a linha que começa
com `JSON>` é o collected.json.

Roda no `manage.py shell` do container: junta, para cada run, as notas brutas de cada
avaliador (última rodada), o custo e o tempo por estágio. Escreve um JSON no stdout.

Quando o E1 foi reaproveitado de outro run (mesmo PDF), o custo e o tempo da extração vêm do
run que de fato extraiu, marcados como `e1_reused`."""

import json
from collections import defaultdict

from projects.correction.attempts.models import LLMCall, Run
from projects.correction.evaluation.models import ReviewRound

STAGES = {
    "extraction": ("extracting", "extracted"),
    "profiling": ("profiling", "profiled"),
    "integrity": ("checking_integrity", "integrity_checked"),
    "evaluation": ("evaluating", "evaluated"),
    "consolidation": ("consolidating", "done"),
}


def costs(run_id):
    cost = defaultdict(float)
    for call in LLMCall.objects.filter(run_id=run_id):
        cost[call.stage] += float(call.cost_usd or 0)
    return cost


def timeline(run):
    """Segundos de processamento por estágio: soma dos trechos entre o início do estágio e o
    fim (ou uma falha). O tempo parado com erro, esperando o reprocessamento, não conta."""
    events = list(run.events.order_by("created_at").values("created_at", "to_status"))
    starts = {start: stage for stage, (start, _) in STAGES.items()}
    ends = {end for _, end in STAGES.values()}
    seconds = {}
    open_stage, opened_at = None, None
    for event in events:
        status = event["to_status"]
        if open_stage and (status in ends or status.startswith("error") or status in starts):
            seconds[open_stage] = seconds.get(open_stage, 0) + (
                event["created_at"] - opened_at
            ).total_seconds()
            open_stage = None
        if status in starts:
            open_stage, opened_at = starts[status], event["created_at"]
    return seconds, sum(seconds.values())


RUNS = json.loads(open("/tmp/runs.json").read())
out = {}
for label, run_id in RUNS.items():
    run = Run.objects.get(pk=run_id)
    latest = {}
    for row in ReviewRound.objects.filter(run_id=run_id).order_by("evaluator_slot", "-round_number"):
        latest.setdefault(row.evaluator_slot, row)
    raw = {
        slot: {
            "round": row.round_number,
            "model": row.model_spec.get("model_id"),
            "grades": {c.criterion_key.value: c.grade for c in row.state.criteria},
        }
        for slot, row in latest.items()
    }
    cost = costs(run_id)
    seconds, total = timeline(run)
    e1_reused = cost.get("extraction", 0) == 0 and run.extraction_id is not None
    if e1_reused:
        source = next(
            (
                other
                for other in Run.objects.filter(extraction_id=run.extraction_id)
                .exclude(pk=run.pk)
                .order_by("created_at")
                if costs(other.pk).get("extraction", 0) > 0
            ),
            None,
        )
        if source is not None:
            cost["extraction"] = costs(source.pk)["extraction"]
            source_seconds, _ = timeline(source)
            if "extraction" in source_seconds:
                # O tempo total passa a contar a extração original no lugar da reaproveitada.
                total = (total or 0) - seconds.get("extraction", 0) + source_seconds["extraction"]
                seconds["extraction"] = source_seconds["extraction"]
    out[label] = {
        "run_id": run_id,
        "status": run.status,
        "raw": raw,
        "cost": dict(cost),
        "seconds": seconds,
        "total_seconds": total,
        "e1_reused": e1_reused,
        "calls": LLMCall.objects.filter(run_id=run_id).count(),
    }
print("JSON>" + json.dumps(out, ensure_ascii=False))
