"""Refatora painel KPI mobile no tablet.html."""
import re
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "templates" / "tablet.html"
text = path.read_text(encoding="utf-8")

text = re.sub(
    r'\n\s*<motion class="mob-cell mob-cell--fardos">.*?</motion>\n',
    "\n",
    text,
    count=1,
    flags=re.S,
)
text = re.sub(
    r'\n\s*<div class="mob-cell mob-cell--fardos">.*?</div>\n',
    "\n",
    text,
    count=1,
    flags=re.S,
)

old_ops = re.search(
    r'<section class="mob-ops" id="mob-ops-grid".*?</section>\s+<section class="mob-card mob-apont"',
    text,
    re.S,
)
if not old_ops:
    raise SystemExit("mob-ops block not found")

new_ops = """<section class="mob-ops mes-kpi-panel" id="mob-ops-grid" aria-label="Indicadores operacionais" data-machine-st="stop">
                    <div class="mes-kpi-grid" role="group" aria-label="KPIs de produção">
                        <div class="mes-kpi-card mes-kpi-card--cliente">
                            <span class="mes-kpi-card__label">Cliente</span>
                            <span class="mes-kpi-card__value" id="mob-kpi-cliente" data-tablet-id="f-cliente">—</span>
                        </div>
                        <div class="mes-kpi-card mes-kpi-card--prod">
                            <span class="mes-kpi-card__label">Produzido</span>
                            <span class="mes-kpi-card__value" id="mob-kpi-produzido" data-tablet-id="hmi-op-produzido">0</span>
                        </div>
                        <div class="mes-kpi-card mes-kpi-card--fardos">
                            <span class="mes-kpi-card__label">Fardos</span>
                            <span class="mes-kpi-card__value" id="mob-f-fardos-kpi" data-tablet-id="f-fardos">—</span>
                        </div>
                        <div class="mes-kpi-card mes-kpi-card--faltam">
                            <span class="mes-kpi-card__label">Faltam</span>
                            <span class="mes-kpi-card__value" id="mob-kpi-faltam" data-tablet-id="hmi-op-faltam">0</span>
                        </motion>
                        <div class="mes-kpi-card mes-kpi-card--ef">
                            <span class="mes-kpi-card__label">Eficiência</span>
                            <span class="mes-kpi-card__value" id="mob-kpi-ef" data-tablet-id="hmi-op-ef">0%</span>
                        </div>
                        <div class="mes-kpi-card mes-kpi-card--parado">
                            <span class="mes-kpi-card__label">Tempo parado</span>
                            <span class="mes-kpi-card__value mes-kpi-card__value--mono" id="mob-kpi-tempo-parado" data-tablet-id="hmi-kpi-tempo-parado">00:00:00</span>
                        </div>
                        <div class="mes-kpi-card mes-kpi-card--motivo">
                            <span class="mes-kpi-card__label">Motivo</span>
                            <span class="mes-kpi-card__value mes-kpi-card__value--motivo" id="mob-kpi-motivo" data-tablet-id="hmi-kpi-motivo">—</span>
                        </div>
                    </div>
                    <footer class="mes-kpi-foot">
                        <span class="mes-kpi-foot__op" data-tablet-id="hmi-op-combo">—</span>
                        <span class="mes-kpi-foot__dia">Prod. dia <strong data-tablet-id="hmi-producao-dia">0</strong></span>
                    </footer>
                </section>

                <section class="mob-card mob-apont" """

new_ops = new_ops.replace("</motion>", "</div>").replace(
    '<div class="mes-kpi-card mes-kpi-card--faltam">',
    '<div class="mes-kpi-card mes-kpi-card--faltam">',
)

text = text[: old_ops.start()] + new_ops + text[old_ops.end() :]

css_old_start = "/* Painel operacional central — mini KPIs */"
css_old_end = ".ref-body--mobile-op .mob-card.mob-mes,"
if css_old_start not in text:
    raise SystemExit("CSS start not found")
i0 = text.index(css_old_start)
i1 = text.index(css_old_end)

new_css = """/* Painel operacional central — KPIs MES compactos */
.ref-body--mobile-op .mob-ops.mes-kpi-panel {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin: 0;
    padding: 5px 6px;
    background: linear-gradient(165deg, rgba(12, 20, 32, 0.96) 0%, rgba(8, 14, 24, 0.99) 100%);
    border: 1px solid rgba(94, 176, 214, 0.22);
    border-radius: var(--r-sm);
    box-shadow:
        0 0 0 1px rgba(94, 176, 214, 0.08) inset,
        0 6px 22px rgba(0, 0, 0, 0.4),
        0 0 20px rgba(34, 197, 94, 0.05);
}

.ref-body--mobile-op .mob-ops[data-machine-st="run"] {
    border-color: rgba(34, 197, 94, 0.35);
    box-shadow:
        0 0 0 1px rgba(34, 197, 94, 0.14) inset,
        0 6px 22px rgba(0, 0, 0, 0.4),
        0 0 28px rgba(34, 197, 94, 0.12);
}

.ref-body--mobile-op .mob-ops[data-machine-st="stop"] {
    border-color: rgba(245, 158, 11, 0.28);
    box-shadow:
        0 0 0 1px rgba(245, 158, 11, 0.1) inset,
        0 6px 22px rgba(0, 0, 0, 0.4),
        0 0 22px rgba(245, 158, 11, 0.08);
}

.ref-body--mobile-op .mob-ops[data-machine-st="maint"] {
    border-color: rgba(148, 163, 184, 0.35);
    box-shadow:
        0 0 0 1px rgba(148, 163, 184, 0.12) inset,
        0 6px 22px rgba(0, 0, 0, 0.4);
}

.ref-body--mobile-op .mes-kpi-grid {
    flex: 1 1 auto;
    min-height: 0;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    grid-auto-rows: minmax(50px, auto);
    gap: 5px;
    align-content: start;
}

.ref-body--mobile-op .mes-kpi-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: stretch;
    gap: 3px;
    min-width: 0;
    min-height: 50px;
    padding: 5px 7px;
    box-sizing: border-box;
    border-radius: 6px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.05) 0%, rgba(0, 0, 0, 0.32) 100%);
    box-shadow: 0 0 14px rgba(94, 176, 214, 0.05) inset;
    pointer-events: none;
    user-select: none;
}

.ref-body--mobile-op .mes-kpi-card--cliente {
    grid-column: span 2;
}

.ref-body--mobile-op .mes-kpi-card--motivo {
    grid-column: span 2;
}

.ref-body--mobile-op .mes-kpi-card__label {
    flex-shrink: 0;
    font-size: clamp(0.48rem, 1.65vw, 0.56rem);
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(148, 163, 184, 0.9);
    line-height: 1.1;
}

.ref-body--mobile-op .mes-kpi-card__value {
    flex: 0 0 auto;
    font-size: clamp(0.74rem, 2.65vw, 1rem);
    font-weight: 900;
    font-variant-numeric: tabular-nums;
    color: #f1f5f9;
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.ref-body--mobile-op .mes-kpi-card--cliente .mes-kpi-card__value {
    color: #cbd5e1;
    font-size: clamp(0.76rem, 2.7vw, 1.02rem);
}

.ref-body--mobile-op .mes-kpi-card--prod .mes-kpi-card__value {
    color: var(--mes-blue-mid);
}

.ref-body--mobile-op .mes-kpi-card--fardos .mes-kpi-card__value {
    color: #e2e8f0;
}

.ref-body--mobile-op .mes-kpi-card--faltam .mes-kpi-card__value {
    color: var(--mes-orange);
}

.ref-body--mobile-op .mes-kpi-card--ef .mes-kpi-card__value {
    color: #7dd3fc;
}

.ref-body--mobile-op .mes-kpi-card--parado .mes-kpi-card__value {
    color: #94a3b8;
    letter-spacing: 0.03em;
}

.ref-body--mobile-op .mes-kpi-card__value--motivo {
    color: var(--mes-amber);
    font-weight: 800;
    font-size: clamp(0.68rem, 2.4vw, 0.88rem);
}

.ref-body--mobile-op .mes-kpi-card__value--mono {
    font-variant-numeric: tabular-nums;
}

.ref-body--mobile-op .mes-kpi-foot {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 4px 6px 2px;
    border-top: 1px solid rgba(148, 163, 184, 0.16);
    font-size: clamp(0.48rem, 1.6vw, 0.54rem);
    font-weight: 700;
    color: var(--mes-muted);
}

.ref-body--mobile-op .mes-kpi-foot__op {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
    flex: 1 1 auto;
}

.ref-body--mobile-op .mes-kpi-foot__dia strong {
    color: var(--mes-blue-mid);
    font-weight: 900;
    font-variant-numeric: tabular-nums;
}

.ref-body--iphone-12pm .mes-kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-auto-rows: minmax(46px, auto);
    gap: 4px;
}

.ref-body--iphone-12pm .mes-kpi-card {
    min-height: 46px;
    padding: 4px 6px;
}

.ref-body--iphone-12pm .mes-kpi-card--cliente {
    grid-column: 1 / -1;
}

.ref-body--iphone-12pm .mes-kpi-card--motivo {
    grid-column: 2 / -1;
}

.ref-body--iphone-12pm .mes-kpi-card__label {
    font-size: 0.46rem;
}

.ref-body--iphone-12pm .mes-kpi-card__value {
    font-size: clamp(0.66rem, 2.3vw, 0.86rem);
}

"""

text = text[:i0] + new_css + text[i1:]

text = re.sub(
    r"\.ref-body--mobile-op \.mob-order-grid \{\s*grid-template-columns: repeat\(2,[^}]+\}\s*",
    ".ref-body--mobile-op .mob-order-grid {\n    grid-template-columns: repeat(3, minmax(0, 1fr));\n}\n\n",
    text,
    count=1,
)

path.write_text(text, encoding="utf-8")
print("OK", path)
