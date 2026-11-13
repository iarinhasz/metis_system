"""Revisões sintéticas julgadas; nunca executa provedores externos."""

from projects.correction.agents.schemas.criteria import Criterion
from projects.correction.agents.schemas.evaluation import (
    CriterionSynthesis,
    EvaluationMode,
    EvaluatorSlot,
    Evidence,
    ItemRef,
    ItemType,
    ItemVerdict,
    Observation,
    ReviewState,
    Verdict,
    VerdictSource,
)
from projects.correction.agents.schemas.section_roles import SectionRole
from projects.correction.agents.specs import Family, Role, development_spec
from projects.correction.attempts.models import Run
from projects.correction.attempts.status import RunStatus, Stage
from projects.correction.evaluation.contracts import ReviewedSlot
from projects.correction.evaluation.models import JudgeVerdict, ReviewRound
from projects.correction.extractor.article import ExtractedArticle, ExtractedSection
from projects.correction.extractor.models import Extraction
from projects.correction.metis.config import settings
from projects.correction.questions.criteria import STANDARD
from projects.correction.questions.models import Question
from projects.correction.questions.profile import QuestionSnapshot


def review(slot: EvaluatorSlot, grade: int = 4, *, unresolved: bool = False) -> ReviewedSlot:
    observation = Observation(
        id="obs-1",
        section_id="sec_2",
        role=SectionRole.METHOD,
        kind="strength",
        statement="O método define os parâmetros.",
        evidence=(Evidence(quote="Os parâmetros foram definidos.", section_id="sec_2"),),
        criteria=tuple(Criterion),
        severity="minor",
        confidence=0.9,
    )
    criteria = tuple(
        CriterionSynthesis.model_validate(
            {
                "criterion_key": key,
                "grade": grade,
                "justification": "A evidência sustenta este critério.",
                "observation_ids": [observation.id],
                "confidence": 0.9,
            }
        )
        for key in Criterion
    )
    pending = (
        (ItemRef(item_type=ItemType.CRITERION, item_key=Criterion.SOUNDNESS),) if unresolved else ()
    )
    state = ReviewState(observations=(observation,), criteria=criteria, unresolved=pending)
    verdicts = (
        ItemVerdict(item_type=ItemType.OBSERVATION, item_key=observation.id, verdict=Verdict.VALID),
    ) + tuple(
        ItemVerdict(
            item_type=ItemType.CRITERION,
            item_key=key,
            verdict=Verdict.INVALID if unresolved and key == Criterion.SOUNDNESS else Verdict.VALID,
        )
        for key in Criterion
    )
    return ReviewedSlot(
        slot=slot,
        round_number=1,
        mode=EvaluationMode.SECTIONED,
        model_spec=development_spec(Role(f"evaluator_{slot}")),
        state=state,
        verdicts=verdicts,
    )


def prepare_evaluated(run: Run) -> Run:
    base = ExtractedSection(
        id="sec_1",
        title="Resumo",
        level=1,
        parent_id=None,
        key="abstract",
        text="Um artigo científico de teste.",
        has_footnotes=False,
        coverage=None,
        fidelity=None,
    )
    article = ExtractedArticle(
        title="Artigo <script>privado</script>",
        authors=(),
        language="pt",
        model="fake",
        sections=(
            base,
            base.model_copy(
                update={
                    "id": "sec_2",
                    "title": "Método",
                    "key": None,
                    "text": "Os parâmetros foram definidos.",
                }
            ),
        ),
    )
    Run.claim_stage(run.pk, Stage.EXTRACTION, "e1")
    extraction = Extraction.store(run.attempt.sha256, "consolidation-test", article)
    Run.attach_extraction(run.pk, "e1", extraction)
    Run.complete_stage(run.pk, "e1", RunStatus.EXTRACTED)
    question = Question.create(name="Genérica de teste", method="standard", is_generic=True)
    snapshot = QuestionSnapshot(
        id=question.pk,
        version=question.version,
        name=question.name,
        method=question.method,
        is_generic=True,
        taxonomy_node_code=None,
        taxonomy_version=None,
        rubric_fields=(),
    )
    Run.claim_stage(run.pk, Stage.PROFILING, "e2")
    Run.initialize_profiling(
        run.pk,
        "e2",
        {
            "profiling": {},
            "method": "standard",
            "evaluation_config": STANDARD.model_dump(mode="json"),
            "taxonomy_version": "test-taxonomy",
            "model_specs": {
                role.value: spec.model_dump(mode="json")
                for role, spec in settings.model_specs.items()
            },
        },
    )
    for key, value in (
        ("classification", {"paper_type": "empirical"}),
        (
            "section_roles",
            [
                {"section_id": "sec_1", "roles": ["other"]},
                {"section_id": "sec_2", "roles": ["method"]},
            ],
        ),
        ("complete", True),
    ):
        Run.checkpoint_profile(run.pk, "e2", key, value, prompt_versions={})
    Run.checkpoint_profile(
        run.pk,
        "e2",
        "resolution",
        {"question": snapshot.model_dump(mode="json")},
        question_id=question.pk,
        prompt_versions={},
    )
    Run.complete_stage(run.pk, "e2", RunStatus.PROFILED)
    Run.claim_stage(run.pk, Stage.INTEGRITY, "e3")
    Run.complete_stage(run.pk, "e3", RunStatus.INTEGRITY_CHECKED)
    Run.claim_stage(run.pk, Stage.EVALUATION, "e4")
    for slot, grade in zip(EvaluatorSlot, (4, 5, 1), strict=True):
        record_review(run, review(slot, grade))
    Run.complete_stage(run.pk, "e4", RunStatus.EVALUATED)
    return Run.get_by_id(run.pk)


def record_review(run: Run, data: ReviewedSlot) -> ReviewRound:
    row = ReviewRound.store(
        run.pk,
        "e4",
        slot=data.slot,
        round_number=data.round_number,
        mode=data.mode,
        model_spec=data.model_spec,
        state=data.state,
    )
    judge = development_spec(
        Role.JUDGE_GOOGLE if data.model_spec.family == Family.GPT else Role.JUDGE_OPENAI
    )
    for verdict in data.verdicts:
        JudgeVerdict.record(
            row.pk, "e4", item=verdict, source=VerdictSource.JUDGE, judge_model=judge
        )
    return ReviewRound.finalize(row.pk, "e4")
