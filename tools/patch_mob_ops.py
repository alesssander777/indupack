# -*- coding: utf-8 -*-
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "templates" / "tablet.html"
text = P.read_text(encoding="utf-8")

OLD = '''                <section class="mob-card mob-mes" aria-label="Operação">
                    <div class="mob-mes-grid">
                        <div class="mob-cell mob-cell--status">
                            <span class="mob-cell__k">Status</span>
                            <span class="mob-cell__v mob-cell__v--status">
                                <span class="hmi-dot" data-tablet-id="hmi-mid-dot"></span>
                                <span data-tablet-id="hmi-mid-status-txt">PARADA</span>
                            </span>
                        </div>
                        <div class="mob-cell">
                            <span class="mob-cell__k">Operador / turno</span>
                            <span class="mob-cell__v" data-tablet-id="hmi-op-combo">—</span>
                        </div>
                        <div class="mob-cell">
                            <span class="mob-cell__k">Tempo parado</span>
                            <span class="mob-cell__v mob-cell__mono" data-tablet-id="hmi-op-tempo-parado">00:00:00</span>
                        </div>
                        <div class="mob-cell mob-cell--motivo">
                            <span class="mob-cell__k">Motivo</span>
                            <span class="mob-cell__v mob-cell__v--motivo" data-tablet-id="hmi-motivo-parada">—</span>
                        </div>
                    </div>
                </section>

                <section class="mob-card mob-apont" aria-label="Apontamento">'''


NEW = '''                <section class="mob-ops" id="mob-ops-grid" aria-label="Painel operacional" data-machine-st="stop">
                    <div class="mob-ops-grid">
                        <article class="mob-mini mob-mini--status">
                            <span class="mob-mini__glyph mob-mini__glyph--pulse" aria-hidden="true"></span>
                            <span class="mob-mini__label">Status</span>
                            <span class="mob-mini__value mob-mini__value--status">
                                <span class="hmi-dot" data-tablet-id="hmi-mid-dot"></span>
                                <span data-tablet-id="hmi-mid-status-txt">PARADA</span>
                            </span>
                        </article>
                        <article class="mob-mini mob-mini--prod">
                            <span class="mob-mini__glyph" aria-hidden="true">▣</span>
                            <span class="mob-mini__label">Produzido</span>
                            <span class="mob-mini__value" data-tablet-id="hmi-op-produzido">0</span>
                        </article>
                        <article class="mob-mini mob-mini--fardos">
                            <span class="mob-mini__glyph" aria-hidden="true">≡</span>
                            <span class="mob-mini__label">Fardos</span>
                            <span class="mob-mini__value" data-tablet-id="f-fardos">—</span>
                        </article>
                        <article class="mob-mini mob-mini--faltam">
                            <span class="mob-mini__glyph" aria-hidden="true">⏳</span>
                            <span class="mob-mini__label">Faltam</span>
                            <span class="mob-mini__value" data-tablet-id="hmi-op-faltam">0</span>
                        </article>
                        <article class="mob-mini mob-mini--ef">
                            <span class="mob-mini__glyph" aria-hidden="true">⚡</span>
                            <span class="mob-mini__label">Eficiência</span>
                            <span class="mob-mini__value" data-tablet-id="hmi-op-ef">0%</span>
                        </article>
                        <article class="mob-mini mob-mini--parado">
                            <span class="mob-mini__glyph" aria-hidden="true">⏱</span>
                            <span class="mob-mini__label">Tempo parado</span>
                            <span class="mob-mini__value mob-mini__mono" data-tablet-id="hmi-kpi-tempo-parado">00:00:00</span>
                        </article>
                        <article class="mob-mini mob-mini--motivo">
                            <span class="mob-mini__glyph" aria-hidden="true">🛠</span>
                            <span class="mob-mini__label">Motivo atual</span>
                            <span class="mob-mini__value mob-mini__value--motivo" data-tablet-id="hmi-kpi-motivo">—</span>
                        </article>
                    </div>
                    <div class="mob-ops-sub">
                        <span class="mob-ops-sub__op" data-tablet-id="hmi-op-combo">—</span>
                        <span class="mob-ops-sub__dia">Prod. dia <strong data-tablet-id="hmi-producao-dia">0</strong></span>
                    </div>
                </section>

                <section class="mob-card mob-apont" aria-label="Apontamento">'''

if OLD not in text:
    raise SystemExit("mes block not found")
text = text.replace(OLD, NEW, 1)

OLD_KPI = '''                <section class="mob-card mob-kpi" aria-label="Indicadores">
                    <div class="mob-kpi-grid">
                        <div class="mob-kpi-item">
                            <span class="mob-kpi-k">Eficiência</span>
                            <span class="mob-kpi-v" data-tablet-id="hmi-op-ef">0%</span>
                        </div>
                        <div class="mob-kpi-item">
                            <span class="mob-kpi-k">OEE</span>
                            <span class="mob-kpi-v" data-tablet-id="hmi-op-oee">0%</span>
                        </div>
                        <div class="mob-kpi-item">
                            <span class="mob-kpi-k">Produzido</span>
                            <span class="mob-kpi-v" data-tablet-id="hmi-op-produzido">0</span>
                        </div>
                        <div class="mob-kpi-item mob-kpi-item--warn">
                            <span class="mob-kpi-k">Faltam</span>
                            <span class="mob-kpi-v" data-tablet-id="hmi-op-faltam">0</span>
                        </div>
                        <div class="mob-kpi-item">
                            <span class="mob-kpi-k">T. parado</span>
                            <span class="mob-kpi-v mob-cell__mono" data-tablet-id="hmi-kpi-tempo-parado">00:00:00</span>
                        </div>
                        <div class="mob-kpi-item">
                            <span class="mob-kpi-k">Motivo</span>
                            <span class="mob-kpi-v mob-kpi-v--sm" data-tablet-id="hmi-kpi-motivo">—</span>
                        </div>
                    </div>
                    <div class="mob-kpi-dia">
                        <span class="mob-kpi-dia__k">Produção do dia (máquina)</span>
                        <span class="mob-kpi-dia__v" data-tablet-id="hmi-producao-dia">0</span>
                    </div>
                </section>

                '''

if OLD_KPI not in text:
    raise SystemExit("kpi block not found")
text = text.replace(OLD_KPI, "", 1)

text = text.replace(
    '''                <span class="mob-stash" hidden aria-hidden="true">
                    <span data-tablet-id="f-cliente"></span>
                    <span data-tablet-id="f-fardos"></span>
                    <span data-tablet-id="f-obs"></span>
                    <span data-tablet-id="hmi-op-operador"></span>
                    <span data-tablet-id="hmi-op-turno"></span>
                </span>''',
    '''                <span class="mob-stash" hidden aria-hidden="true">
                    <span data-tablet-id="f-cliente"></span>
                    <span data-tablet-id="f-obs"></span>
                    <span data-tablet-id="hmi-op-operador"></span>
                    <span data-tablet-id="hmi-op-turno"></span>
                    <span data-tablet-id="hmi-op-oee"></span>
                    <span data-tablet-id="hmi-op-tempo-parado"></span>
                    <span data-tablet-id="hmi-motivo-parada"></span>
                </span>''',
    1,
)

text = text.replace(
    '                <div class="mob-cmds" aria-label="Comandos">\n                <div class="mob-cmds" aria-label="Comandos">',
    '                <div class="mob-cmds" aria-label="Comandos">',
    1,
)

CSS_MARKER = ".ref-body--mobile-op .mob-kpi-grid {"
CSS_OPS = r'''
/* Painel operacional central — mini KPIs */
.ref-body--mobile-op .mob-ops {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
    margin: 0;
    padding: 3px;
    background: linear-gradient(165deg, rgba(12, 20, 32, 0.95) 0%, rgba(8, 14, 24, 0.98) 100%);
    border: 1px solid var(--mes-line-strong);
    border-radius: var(--r-sm);
    box-shadow:
        0 0 0 1px rgba(94, 176, 214, 0.06) inset,
        0 8px 28px rgba(0, 0, 0, 0.35),
        0 0 24px rgba(34, 197, 94, 0.04);
}

.ref-body--mobile-op .mob-ops[data-machine-st="run"] {
    box-shadow:
        0 0 0 1px rgba(34, 197, 94, 0.12) inset,
        0 8px 28px rgba(0, 0, 0, 0.35),
        0 0 32px rgba(34, 197, 94, 0.14);
}

.ref-body--mobile-op .mob-ops[data-machine-st="stop"] {
    box-shadow:
        0 0 0 1px rgba(245, 158, 11, 0.1) inset,
        0 8px 28px rgba(0, 0, 0, 0.35),
        0 0 28px rgba(245, 158, 11, 0.08);
}

.ref-body--mobile-op .mob-ops-grid {
    flex: 1 1 auto;
    min-height: 0;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    grid-template-rows: minmax(0, 1fr) minmax(0, 1fr) auto;
    gap: 4px;
}

.ref-body--mobile-op .mob-mini {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 2px;
    min-width: 0;
    min-height: 0;
    padding: 5px 6px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.04) 0%, rgba(0, 0, 0, 0.28) 100%);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 6px;
    box-shadow: 0 1px 0 rgba(255, 255, 255, 0.05) inset;
    overflow: hidden;
}

.ref-body--mobile-op .mob-mini--status {
    grid-column: 1 / 3;
    grid-row: 1 / 3;
    padding: 6px 8px;
    border-color: rgba(94, 176, 214, 0.35);
    background: linear-gradient(145deg, rgba(94, 176, 214, 0.12) 0%, rgba(0, 0, 0, 0.35) 100%);
}

.ref-body--mobile-op .mob-ops[data-machine-st="run"] .mob-mini--status {
    border-color: rgba(34, 197, 94, 0.45);
    box-shadow: 0 0 18px rgba(34, 197, 94, 0.2) inset;
}

.ref-body--mobile-op .mob-ops[data-machine-st="stop"] .mob-mini--status {
    border-color: rgba(245, 158, 11, 0.4);
    box-shadow: 0 0 16px rgba(245, 158, 11, 0.12) inset;
}

.ref-body--mobile-op .mob-mini--prod { grid-column: 3; grid-row: 1; }
.ref-body--mobile-op .mob-mini--fardos { grid-column: 4; grid-row: 1; }
.ref-body--mobile-op .mob-mini--faltam { grid-column: 3; grid-row: 2; }
.ref-body--mobile-op .mob-mini--ef { grid-column: 4; grid-row: 2; }
.ref-body--mobile-op .mob-mini--parado { grid-column: 1 / 3; grid-row: 3; }
.ref-body--mobile-op .mob-mini--motivo { grid-column: 3 / 5; grid-row: 3; }

.ref-body--mobile-op .mob-mini__glyph {
    font-size: 0.62rem;
    line-height: 1;
    opacity: 0.85;
}

.ref-body--mobile-op .mob-mini__glyph--pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--mes-amber);
    box-shadow: 0 0 8px var(--mes-amber);
}

.ref-body--mobile-op .mob-ops[data-machine-st="run"] .mob-mini__glyph--pulse {
    background: var(--mes-green);
    box-shadow: 0 0 10px var(--mes-green);
    animation: mob-pulse 1.6s ease-in-out infinite;
}

.ref-body--mobile-op .mob-mini__label {
    font-size: 0.44rem;
    font-weight: 800;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--mes-muted);
    line-height: 1.1;
}

.ref-body--mobile-op .mob-mini__value {
    font-size: clamp(0.72rem, 2.8vw, 0.95rem);
    font-weight: 900;
    font-variant-numeric: tabular-nums;
    color: var(--mes-ink);
    line-height: 1.1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.ref-body--mobile-op .mob-mini--status .mob-mini__value {
    font-size: clamp(0.85rem, 3.5vw, 1.15rem);
    white-space: normal;
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}

.ref-body--mobile-op .mob-mini--prod .mob-mini__value {
    color: var(--mes-blue-mid);
    font-size: clamp(0.78rem, 3vw, 1.05rem);
}

.ref-body--mobile-op .mob-mini--faltam .mob-mini__value {
    color: var(--mes-orange);
}

.ref-body--mobile-op .mob-mini--ef .mob-mini__value {
    color: #7dd3fc;
}

.ref-body--mobile-op .mob-mini__value--motivo {
    font-size: clamp(0.58rem, 2.2vw, 0.72rem);
    font-weight: 700;
    color: var(--mes-amber);
}

.ref-body--mobile-op .mob-mini__mono {
    font-variant-numeric: tabular-nums;
}

.ref-body--mobile-op .mob-ops-sub {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 3px 5px;
    border-top: 1px solid rgba(148, 163, 184, 0.15);
    font-size: 0.5rem;
    font-weight: 700;
    color: var(--mes-muted);
}

.ref-body--mobile-op .mob-ops-sub__op {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
    flex: 1 1 auto;
}

.ref-body--mobile-op .mob-ops-sub__dia strong {
    color: var(--mes-blue-mid);
    font-weight: 900;
    font-variant-numeric: tabular-nums;
}

@keyframes mob-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.55; transform: scale(0.92); }
}

.ref-body--iphone-12pm .mob-ops-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    grid-template-rows: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) auto;
}

.ref-body--iphone-12pm .mob-mini--status {
    grid-column: 1 / 2;
    grid-row: 1 / 3;
}

.ref-body--iphone-12pm .mob-mini--prod { grid-column: 2; grid-row: 1; }
.ref-body--iphone-12pm .mob-mini--fardos { grid-column: 3; grid-row: 1; }
.ref-body--iphone-12pm .mob-mini--faltam { grid-column: 2; grid-row: 2; }
.ref-body--iphone-12pm .mob-mini--ef { grid-column: 3; grid-row: 2; }
.ref-body--iphone-12pm .mob-mini--parado { grid-column: 1 / 3; grid-row: 3; }
.ref-body--iphone-12pm .mob-mini--motivo { grid-column: 3; grid-row: 3; }

.ref-body--mobile-op .mob-card.mob-mes,
.ref-body--mobile-op .mob-card.mob-kpi {
    display: none !important;
}

'''

if "/* Painel operacional central — mini KPIs */" not in text:
    if CSS_MARKER not in text:
        raise SystemExit("CSS marker not found")
    text = text.replace(CSS_MARKER, CSS_OPS + CSS_MARKER, 1)

JS_OLD = '''                if (mdot) {
                    mdot.className = "hmi-dot " + (stu === "RODANDO" ? "is-run" : (stu === "MANUTENÇÃO" || stu === "MANUTENCAO") ? "is-warn" : "is-stop");
                }

                document.getElementById("ft-prod-time").textContent = tempoProducaoDisplay();'''

JS_NEW = '''                if (mdot) {
                    mdot.className = "hmi-dot " + (stu === "RODANDO" ? "is-run" : (stu === "MANUTENÇÃO" || stu === "MANUTENCAO") ? "is-warn" : "is-stop");
                }

                var opsPanel = document.getElementById("mob-ops-grid");
                if (opsPanel) {
                    var opsSt = stu === "RODANDO" ? "run" : (stu === "MANUTENÇÃO" || stu === "MANUTENCAO") ? "maint" : "stop";
                    opsPanel.setAttribute("data-machine-st", opsSt);
                }

                document.getElementById("ft-prod-time").textContent = tempoProducaoDisplay();'''

if JS_OLD in text:
    text = text.replace(JS_OLD, JS_NEW, 1)

P.write_text(text, encoding="utf-8")
print("mob-ops patch OK")
