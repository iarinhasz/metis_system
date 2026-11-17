"""Monta o HTML da comparação IA × revisores humanos (PeerRead) e imprime em PDF com o Chrome.

Uso, na pasta da comparação: python3 scripts/render.py dados metis_vs_humanos.pdf
(dados/ tem articles.json, collected.json, analysis.json e report_<label>.json). Precisa do
PeerRead em dataset_project/raw/ e do google-chrome para imprimir o PDF."""

import html
import json
import statistics
import subprocess
import sys
from pathlib import Path

DIR = Path(sys.argv[1]).resolve()
OUT_PDF = Path(sys.argv[2]).resolve()
OUT_HTML = DIR / "comparacao.html"
# dataset_project/resultados/<esta pasta>/scripts/render.py → dataset_project/raw/...
PEERREAD = Path(__file__).resolve().parents[3] / "raw" / "PeerRead-master" / "data"

CRITERIA = [
    ("originality", "Originalidade", "ORIGINALITY"),
    ("soundness", "Solidez", "SOUNDNESS_CORRECTNESS"),
    ("substance", "Substância", "SUBSTANCE"),
    ("clarity", "Clareza", "CLARITY"),
    ("meaningful_comparison", "Comparação com outros trabalhos", "MEANINGFUL_COMPARISON"),
    ("impact", "Impacto", "IMPACT"),
    ("replicability", "Reprodutibilidade", None),
]
STAGES = [
    ("extraction", "E1 extração"),
    ("profiling", "E2 perfil"),
    ("integrity", "E3 integridade"),
    ("evaluation", "E4 avaliação"),
    ("consolidation", "E5 relatório"),
]
REC_LABEL = {
    "accept": "aceitar",
    "minor": "aceitar com pequenos ajustes",
    "major": "não aceitar como está (muitos ajustes)",
    "reject": "rejeitar",
    None: "—",
}
def band(score):
    """A recomendação pela média da IA, com os limites do Metis."""
    if score is None:
        return None
    return "accept" if score >= 4 else "minor" if score >= 3 else "major" if score >= 2 else "reject"


def would_accept(score):
    return {"accept": "sim", "minor": "sim", "major": "não", "reject": "não"}.get(band(score), "—")

e = html.escape


def num(value, digits=1):
    return "—" if value is None else f"{float(value):.{digits}f}".replace(".", ",")


def minutes(seconds):
    if seconds is None:
        return "—"
    seconds = int(round(seconds))
    return f"{seconds // 60} min {seconds % 60:02d} s" if seconds >= 60 else f"{seconds} s"


def diff_cell(ai, human):
    if ai is None or human is None:
        return "<td>—</td>"
    diff = ai - human
    css = "neg" if diff <= -0.75 else "pos" if diff >= 0.75 else ""
    return f"<td class='{css}'>{'+' if diff > 0 else ''}{num(diff)}</td>"


def human_reviews(venue, split, pid):
    data = json.loads((PEERREAD / venue / split / "reviews" / f"{pid}.json").read_text())
    seen, reviews = set(), []
    for review in data["reviews"]:
        if review.get("IS_META_REVIEW") or review.get("is_meta_review"):
            continue
        if review.get("RECOMMENDATION") in (None, ""):
            continue
        text = " ".join((review.get("comments") or "").split())
        key = (text[:200], review.get("RECOMMENDATION"))
        if key in seen:
            continue  # o PeerRead do ICLR repete cada revisão
        seen.add(key)
        reviews.append(review | {"comments": text})
    return data, reviews


def to_five(venue, value):
    """Recomendação humana na escala 1–5 (o ICLR usa 1–10)."""
    if value is None:
        return None
    return (value - 1) / 9 * 4 + 1 if venue.startswith("iclr") else value


def numbers(art, collected):
    """Média humana e média da IA, geral e por critério, na escala 1–5."""
    meta, reviews = human_reviews(art["venue"], art["split"], art["pid"])
    recs = [float(r["RECOMMENDATION"]) for r in reviews]
    human_general = to_five(art["venue"], statistics.mean(recs)) if recs else None
    raw = collected["raw"]
    per_criterion = []
    for key, label, human_key in CRITERIA:
        ai = [s["grades"][key] for s in raw.values() if key in s["grades"]]
        human = [float(r[human_key]) for r in reviews if human_key and r.get(human_key)]
        per_criterion.append(
            (
                label,
                statistics.mean(ai) if ai else None,
                statistics.mean(human) if human else None,
                len(human),
            )
        )
    ai_all = [g for s in raw.values() for g in s["grades"].values()]
    ai_general = statistics.mean(ai_all) if ai_all else None
    return meta, reviews, human_general, ai_general, per_criterion


def decision_text(meta):
    accepted = meta.get("accepted")
    return "aceito" if accepted is True else "recusado" if accepted is False else "não informada"


def article_section(art, report, collected, analysis):
    meta, reviews, human_general, ai_general, per_criterion = numbers(art, collected)
    rows = "".join(
        f"<tr><td>{label}</td><td>{num(human)}{f' <small>({n} rev.)</small>' if n else ''}</td>"
        f"<td>{num(ai)}</td>{diff_cell(ai, human)}</tr>"
        for label, ai, human, n in per_criterion
    )
    stage_cells = "".join(
        f"<td>{minutes(collected['seconds'].get(key))}<br>"
        f"<small>US$ {num(collected['cost'].get(key, 0), 3)}</small></td>"
        for key, _ in STAGES
    )
    human_items = "".join(
        f"<div class='review'><div class='rhead'>Revisor {i} · recomendação {e(str(r['RECOMMENDATION']))}"
        f" ({art['human_scale']})</div>"
        f"<p>{e(r['comments'][:800])}{'…' if len(r['comments']) > 800 else ''}</p></div>"
        for i, r in enumerate(reviews, start=1)
    )
    weaknesses = "".join(f"<li>{e(i['text'])}</li>" for i in report["weaknesses"]) or "<li>—</li>"
    strengths = "".join(f"<li>{e(i['text'])}</li>" for i in report["strengths"]) or "<li>—</li>"
    missing_note = (
        "No ICLR 2017, só algumas revisões dão nota por critério (quantas, entre parênteses)."
        if art["venue"].startswith("iclr")
        else "O ACL 2017 não avalia reprodutibilidade."
    )
    return f"""
<section class="article">
  <h2>{e(art['label'])} — {e(meta['title'])}</h2>
  <p class="sub">{e(art['venue_label'])} · decisão real: <b>{decision_text(meta)}</b></p>
  <table class="big">
    <tr><th></th><th>Humanos</th><th>IA (Metis)</th><th>Diferença (IA − humanos)</th></tr>
    <tr><td><b>Nota geral (1–5)</b></td><td><b>{num(human_general)}</b></td><td><b>{num(ai_general)}</b></td>
        {diff_cell(ai_general, human_general)}</tr>
    <tr><td>Aceitaria?</td><td>{('sim' if meta.get('accepted') else 'não') if meta.get('accepted') is not None else '—'} <small>(decisão real)</small></td>
        <td>{would_accept(ai_general)} <small>({REC_LABEL[band(ai_general)]})</small></td><td></td></tr>
  </table>
  <h3>Por critério (média, de 1 a 5)</h3>
  <table class="grid">
    <tr><th>Critério</th><th>Média humana</th><th>Média da IA</th><th>Diferença</th></tr>
    {rows}
  </table>
  <p class="note">{missing_note} A média da IA é a dos três avaliadores (A, B e C).</p>
  <h3>Tempo e custo</h3>
  <table class="grid">
    <tr><th>Total</th>{''.join(f'<th>{name}</th>' for _, name in STAGES)}</tr>
    <tr><td><b>{minutes(collected['total_seconds'])}</b><br><b>US$ {num(sum(collected['cost'].values()), 2)}</b></td>{stage_cells}</tr>
  </table>
  <div class="analysis"><h3>O que a comparação mostra</h3>{analysis.get(art['label'], '<p>—</p>')}</div>
  <div class="cols">
    <div><h3>O que a IA criticou</h3><ul>{weaknesses}</ul>
         <h3>O que a IA elogiou</h3><ul>{strengths}</ul></div>
    <div><h3>O que os revisores humanos disseram (trechos)</h3>{human_items}</div>
  </div>
</section>"""


def main():
    articles = json.loads((DIR / "articles.json").read_text())
    collected = json.loads((DIR / "collected.json").read_text())
    analysis = json.loads((DIR / "analysis.json").read_text())
    summary_rows, sections = [], []
    totals = {"seconds": 0.0, "cost": 0.0}
    means: list[tuple[float, float]] = []
    for art in articles:
        report = json.loads((DIR / f"report_{art['label']}.json").read_text())
        data = collected[art["label"]]
        meta, _, human_general, ai_general, _ = numbers(art, data)
        means.append((human_general, ai_general))
        cost = sum(data["cost"].values())
        totals["seconds"] += data["total_seconds"] or 0
        totals["cost"] += cost
        summary_rows.append(
            f"<tr><td>{e(art['label'])}<br><small>{e(art['venue_label'])}</small></td>"
            f"<td>{e(meta['title'][:52])}{'…' if len(meta['title']) > 52 else ''}</td>"
            f"<td>{decision_text(meta)}</td><td><b>{num(human_general)}</b></td>"
            f"<td><b>{num(ai_general)}</b></td>{diff_cell(ai_general, human_general)}"
            f"<td>{would_accept(ai_general)}</td>"
            f"<td>{minutes(data['total_seconds'])}</td><td>US$ {num(cost, 2)}</td></tr>"
        )
        sections.append(article_section(art, report, data, analysis))
    doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Metis × revisores humanos</title>
<style>
@page {{ size: A4; margin: 16mm 14mm; }}
body {{ font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 9.5pt; color: #1d1d1f; line-height: 1.4; }}
h1 {{ font-size: 20pt; margin: 0 0 4px; }} h2 {{ font-size: 13pt; margin: 0 0 2px; color: #b3122e; }}
h3 {{ font-size: 10.5pt; margin: 12px 0 4px; }} .sub {{ color: #555; margin: 0 0 8px; }}
table {{ border-collapse: collapse; width: 100%; margin: 4px 0; }}
th, td {{ border: 1px solid #d0d0d6; padding: 4px 6px; text-align: left; vertical-align: top; }}
th {{ background: #f3f3f6; font-weight: 600; }}
.big td, .big th {{ font-size: 11pt; padding: 6px 8px; }}
.grid td:nth-child(n+2), .big td:nth-child(n+2), .summary td:nth-child(n+4) {{ text-align: center; }}
.neg {{ background: #fde8ea; }} .pos {{ background: #e6f4ea; }}
.note {{ color: #555; font-size: 8.5pt; }} small {{ color: #666; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }} ul {{ margin: 0; padding-left: 16px; }}
li {{ margin-bottom: 3px; }} .review {{ border-left: 3px solid #d0d0d6; padding-left: 8px; margin-bottom: 6px; }}
.rhead {{ font-weight: 600; font-size: 8.5pt; color: #444; }} .review p {{ margin: 2px 0; font-size: 8.5pt; }}
.analysis {{ background: #f7f7fa; border: 1px solid #e3e3e8; padding: 6px 10px; margin-top: 10px; }}
.article {{ page-break-before: always; }} .summary td, .summary th {{ font-size: 8.5pt; }}
</style></head><body>
<h1>Metis × revisores humanos</h1>
<p class="sub">A nota que o Metis deu a artigos reais, comparada com a dos revisores humanos (PeerRead) · 17/11/2026</p>
<h3>Como ler</h3>
<p>Tudo está na mesma escala, <b>de 1 (ruim) a 5 (ótimo)</b>.</p>
<ul>
<li><b>Média humana:</b> a média das recomendações dos revisores do artigo. O ICLR usa uma escala de 1 a 10,
convertida para 1 a 5.</li>
<li><b>Média da IA:</b> a média das notas que os três avaliadores do Metis deram aos critérios.</li>
<li><b>Diferença:</b> IA menos humanos. Negativa (vermelho) = a IA foi mais dura; positiva (verde) = mais generosa.</li>
<li><b>A IA aceitaria?</b> Vem da média da IA: a partir de 3, ele recomenda <i>aceitar</i> (≥ 4) ou
<i>aceitar com pequenos ajustes</i> (3 a 3,9); abaixo de 3, <i>não aceitar como está</i> (2 a 2,9, o artigo precisa
de muitos ajustes e de nova avaliação) ou <i>rejeitar</i> (abaixo de 2). Esses limites ainda não foram calibrados. (O relatório oficial
do Metis usa só as notas cuja citação foi conferida no texto, por isso a recomendação dele pode sair diferente.)</li>
</ul>
<h3>Resumo</h3>
<table class="summary"><tr><th>Artigo</th><th>Título</th><th>Decisão real</th><th>Média humana</th>
<th>Média da IA</th><th>Diferença</th><th>A IA aceitaria?</th><th>Tempo</th><th>Custo</th></tr>
{''.join(summary_rows)}
<tr><td colspan="3"><b>Média dos {len(articles)} artigos</b></td><td><b>{num(statistics.mean(h for h, _ in means))}</b></td>
<td><b>{num(statistics.mean(a for _, a in means))}</b></td>{diff_cell(statistics.mean(a for _, a in means), statistics.mean(h for h, _ in means))}<td colspan="3"></td></tr>
<tr><td colspan="7"><b>Total</b></td><td><b>{minutes(totals['seconds'])}</b></td>
<td><b>US$ {num(totals['cost'], 2)}</b></td></tr></table>
<p class="note">Tempo: de processamento, somando os estágios. Custo: soma das chamadas aos modelos registradas pelo sistema.</p>
<div class="analysis"><h3>Conclusão</h3>{analysis.get('_geral', '')}</div>
<h3>Limitações</h3>
<ul>
<li><b>A extração (E1) corrompe fórmulas matemáticas, e isso contamina a avaliação.</b> Letras gregas e expoentes
se perdem: no PDF está <code>q(c|D; φ)</code> e <code>±2^n1</code>; a extração entregou <code>q(c|D; $)</code> e
<code>±21</code>. Os avaliadores reclamaram de "notação corrompida" em 8 dos 9 artigos (100 vezes no total), um
defeito que não é dos artigos; os mais punidos (358, 355 e 457) são os de muita matemática. A conferência do E1
contra o PDF ignora fórmulas de propósito (só mede a prosa), por isso o problema passou. Próximo passo: extrair as
fórmulas como LaTeX ou conferi-las também.</li>
<li><b>Amostra pequena:</b> são só {len(articles)} artigos; mostram tendências, não medem com precisão.</li>
<li><b>As notas não são exatamente comparáveis:</b> a média humana vem da recomendação dos revisores, e a da IA, das
notas por critério. Os próprios revisores também discordam entre si.</li>
<li><b>Faixas de recomendação não calibradas:</b> os limites de 2, 3 e 4 foram definidos sem medição.</li>
</ul>
{''.join(sections)}
</body></html>"""
    OUT_HTML.write_text(doc)
    subprocess.run(
        [
            "google-chrome",
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={OUT_PDF}",
            OUT_HTML.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    print(OUT_PDF)


main()
