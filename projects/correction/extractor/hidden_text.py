"""Varredura determin?stica de texto potencialmente oculto em PDFs."""

from __future__ import annotations

import re
from collections.abc import Sequence
from io import BytesIO
from typing import Any, Literal

import pdfplumber

from projects.correction.extractor.contract import HiddenTextFinding

FindingReason = Literal["color", "size", "outside_page", "under_image", "instruction"]

_INSTRUCTION_PATTERNS = (
    re.compile(
        r"\b(?:ignore|disregard|override|forget)\b.{0,50}\b(?:previous|all|above|prior)"
        r"\b.{0,30}\b(?:instruction|prompt|rule)s?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:ignorar?|desconsidere|desconsiderar|esque?a|esqueca)\b.{0,60}"
        r"\b(?:instru??es|instrucoes|prompts?|regras)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:ai|artificial intelligence|automated)\s+(?:reviewer|judge|evaluator)\b"
        r".{0,80}\b(?:accept|approve|positive|high score|recommend)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:revisor|avaliador|juiz)\s+(?:de\s+)?(?:ia|intelig?ncia artificial)\b"
        r".{0,80}\b(?:aceite|aprove|nota alta|recomende)\b",
        re.IGNORECASE,
    ),
)
_REASONS: tuple[FindingReason, ...] = (
    "color",
    "size",
    "outside_page",
    "under_image",
    "instruction",
)


def scan_hidden_text(pdf_bytes: bytes) -> tuple[HiddenTextFinding, ...]:
    """Retorna trechos com ind?cios visuais ou textuais de oculta??o em cada p?gina."""
    findings: list[HiddenTextFinding] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            characters: Sequence[dict[str, Any]] = page.chars
            background_rects: dict[tuple[float, ...], list[dict[str, Any]]] = {}
            for rectangle in page.rects:
                color = _color_components(rectangle.get("non_stroking_color"))
                if color is not None:
                    background_rects.setdefault(color, []).append(rectangle)
            lines = _group_lines(characters)
            for line in lines:
                findings.extend(_findings_for_line(page, page_number, line, background_rects))
    return tuple(findings)


def _group_lines(
    characters: Sequence[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    lines: list[list[dict[str, Any]]] = []
    for character in sorted(characters, key=lambda item: (float(item["top"]), float(item["x0"]))):
        top = float(character["top"])
        if not lines or abs(float(lines[-1][0]["top"]) - top) > 2.5:
            lines.append([character])
        else:
            lines[-1].append(character)
    return [sorted(line, key=lambda item: float(item["x0"])) for line in lines]


def _findings_for_line(
    page: pdfplumber.page.Page,
    page_number: int,
    line: Sequence[dict[str, Any]],
    background_rects: dict[tuple[float, ...], list[dict[str, Any]]],
) -> list[HiddenTextFinding]:
    text = "".join(str(character["text"]) for character in line)
    has_instruction = any(pattern.search(text) for pattern in _INSTRUCTION_PATTERNS)
    marked: list[tuple[dict[str, Any], set[FindingReason]]] = []
    for character in line:
        reasons = _character_reasons(page, character, background_rects)
        if reasons and has_instruction:
            reasons.add("instruction")
        marked.append((character, reasons))

    findings: list[HiddenTextFinding] = []
    run: list[dict[str, Any]] = []
    reasons_in_run: set[FindingReason] = set()
    for character, reasons in marked:
        if reasons:
            if run and float(character["x0"]) - float(run[-1]["x1"]) > max(
                3.0, float(character.get("size", 0))
            ):
                finding = _make_finding(page_number, run, reasons_in_run)
                if finding is not None:
                    findings.append(finding)
                run = []
                reasons_in_run = set()
            run.append(character)
            reasons_in_run.update(reasons)
        elif run:
            finding = _make_finding(page_number, run, reasons_in_run)
            if finding is not None:
                findings.append(finding)
            run = []
            reasons_in_run = set()
    if run:
        finding = _make_finding(page_number, run, reasons_in_run)
        if finding is not None:
            findings.append(finding)
    return findings


def _character_reasons(
    page: pdfplumber.page.Page,
    character: dict[str, Any],
    background_rects: dict[tuple[float, ...], list[dict[str, Any]]],
) -> set[FindingReason]:
    reasons: set[FindingReason] = set()
    color = character.get("non_stroking_color")
    if _is_white(color) or _matches_background(character, color, background_rects):
        reasons.add("color")
    if float(character.get("size", 0)) < 2:
        reasons.add("size")
    if (
        float(character["x0"]) < 0
        or float(character["x1"]) > float(page.width)
        or float(character["top"]) < 0
        or float(character["bottom"]) > float(page.height)
    ):
        reasons.add("outside_page")
    center_x = (float(character["x0"]) + float(character["x1"])) / 2
    center_y = (float(character["top"]) + float(character["bottom"])) / 2
    if any(
        float(image["x0"]) <= center_x <= float(image["x1"])
        and float(image["top"]) <= center_y <= float(image["bottom"])
        for image in page.images
    ):
        reasons.add("under_image")
    return reasons


def _is_white(color: object) -> bool:
    components = _color_components(color)
    if components is not None and len(components) == 4:
        return all(component <= 0.05 for component in components)
    return components is not None and all(component >= 0.95 for component in components)


def _matches_background(
    character: dict[str, Any],
    color: object,
    background_rects: dict[tuple[float, ...], list[dict[str, Any]]],
) -> bool:
    components = _color_components(color)
    if components is None:
        return False
    center_x = (float(character["x0"]) + float(character["x1"])) / 2
    center_y = (float(character["top"]) + float(character["bottom"])) / 2
    for rectangle in background_rects.get(components, ()):
        if float(rectangle["x0"]) <= center_x <= float(rectangle["x1"]) and float(
            rectangle["top"]
        ) <= center_y <= float(rectangle["bottom"]):
            return True
    return False


def _color_components(color: object) -> tuple[float, ...] | None:
    if isinstance(color, (int, float)):
        return (float(color),)
    if (
        isinstance(color, (tuple, list))
        and color
        and all(isinstance(component, (int, float)) for component in color)
    ):
        return tuple(float(component) for component in color)
    return None


def _make_finding(
    page_number: int, characters: Sequence[dict[str, Any]], reasons: set[FindingReason]
) -> HiddenTextFinding | None:
    text = "".join(str(character["text"]) for character in characters).strip()
    if not text:
        return None
    return HiddenTextFinding(
        page=page_number,
        text=text,
        reasons=tuple(reason for reason in _REASONS if reason in reasons),
        bbox=(
            min(float(character["x0"]) for character in characters),
            min(float(character["top"]) for character in characters),
            max(float(character["x1"]) for character in characters),
            max(float(character["bottom"]) for character in characters),
        ),
    )
