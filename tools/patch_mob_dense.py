# -*- coding: utf-8 -*-
"""Patch tablet.html mobile panel to dense MES layout."""
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "templates" / "tablet.html"
text = P.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

start = next(i for i, ln in enumerate(lines) if '<div class="mob-panel">' in ln and 'mob-panel--' not in ln)
end = next(i for i, ln in enumerate(lines) if '<div class="mob-cmds"' in ln)

NEW_BLOCK = r'''            <div class="mob-panel mob-panel--dense">
                <section class="mob-card mob-hero-wrap" aria-label="Status da máquina">
                    <div class="mob-status op-hero op-hero--stop" data-tablet-id="op-hero" aria-live="polite">
                        <span class="mob-status__ico" data-tablet-id="op-hero-icon" aria-hidden="true"></span>
                        <div class="mob-status__txt">
                            <strong class="mob-status__title" data-tablet-id="op-hero-title">PARADA</strong>
                            <span class="mob-status__sub" data-tablet-id="op-hero-sub"></span>
                        </div>
                    </div>
                </section>

                <section class="mob-card mob-order" aria-label="Pedido atual">
                    <div class="mob-order-grid">
                        <div class="mob-cell">
                            <span class="mob-cell__k">Código</span>
                            <span class="mob-cell__v" data-tablet-id="f-codigo">—</span>
                        </div>
                        <div class="mob-cell">
                            <span class="mob-cell__k">Medida</span>
                            <span class="mob-cell__v" data-tablet-id="f-medida">—</span>
                        </div>
                        <div class="mob-cell mob-cell--qty">
                            <span class="mob-cell__k">Quantidade</span>
                            <span class="mob-cell__v" data-tablet-id="f-quantidade">0</span>
                        </div>
                    </div>
                </section>

                <section class="mob-card mob-mes" aria-label="Operação">
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

                <section class="mob-card mob-apont" aria-label="Apontamento">
                    <div class="mob-apont__head">
                        <span class="mob-apont__htitle">Progresso da produção</span>
                        <span class="mob-apont__hratio" data-tablet-id="apont-progress-label">— / —</span>
                    </div>
                    <div class="mob-apont__ctrl">
                        <input type="number" data-tablet-id="apont-total" class="mob-apont__input" inputmode="numeric" min="0" step="1" placeholder="Total produzido" autocomplete="off" aria-label="Total produzido">
                        <button type="button" data-tablet-id="btn-aplicar-total" class="mob-apont__btn">LANÇAR</button>
                    </div>
                    <div class="mob-apont__prog" aria-label="Progresso">
                        <span class="mob-apont__pct" data-tablet-id="apont-progress-pct-big">—</span>
                        <div class="mob-apont__track-wrap">
                            <div class="mob-apont__track">
                                <div class="mob-apont__fill" data-tablet-id="apont-progress-fill"></div>
                                <span class="mob-apont__pct-in" data-tablet-id="apont-progress-pct">—</span>
                            </div>
                        </div>
                    </div>
                    <p class="mob-apont__hint" data-tablet-id="apont-hint" role="status" hidden></p>
                </section>

                <section class="mob-card mob-kpi" aria-label="Indicadores">
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

                <span class="mob-stash" hidden aria-hidden="true">
                    <span data-tablet-id="f-cliente"></span>
                    <span data-tablet-id="f-fardos"></span>
                    <span data-tablet-id="f-obs"></span>
                    <span data-tablet-id="hmi-op-operador"></span>
                    <span data-tablet-id="hmi-op-turno"></span>
                </span>

                <footer class="mob-foot" aria-label="Rodapé operacional">
                    <span class="mob-foot__tag">MES · Operação</span>
                    <span class="mob-foot__meta">Tempo útil <strong data-tablet-id="ft-prod-time">00:00:00</strong></span>
                </footer>

                <div class="mob-cmds" aria-label="Comandos">
'''.replace("<motion ", "<div ").replace("</motion>", "</motion>")

NEW_BLOCK = NEW_BLOCK.replace("</motion>", "</div>")

out = lines[:start] + [NEW_BLOCK] + lines[end:]
text2 = "".join(out)

# TABLET_SWAP_IDS extension
old_ids = '''                "apont-hint"
            ];'''
new_ids = '''                "apont-hint",
                "f-codigo",
                "f-medida",
                "f-quantidade",
                "f-cliente",
                "f-fardos",
                "f-obs",
                "hmi-op-combo",
                "hmi-op-operador",
                "hmi-op-turno",
                "hmi-op-ef",
                "hmi-op-oee",
                "hmi-op-produzido",
                "hmi-op-faltam",
                "hmi-op-tempo-parado",
                "hmi-kpi-tempo-parado",
                "hmi-motivo-parada",
                "hmi-kpi-motivo",
                "hmi-mid-status-txt",
                "hmi-mid-dot",
                "hmi-producao-dia",
                "apont-progress-pct",
                "ft-prod-time"
            ];'''
if old_ids not in text2:
    raise SystemExit('TABLET_SWAP_IDS anchor missing')
text2 = text2.replace(old_ids, new_ids, 1)

# CSS block before tablet-remote-maint
CSS = r'''
/* ========== Mobile operacional denso (herda linguagem do desktop) ========== */
.ref-body--mobile-op .mob-body {
    grid-template-columns: minmax(108px, 24vw) minmax(0, 1fr);
}

.ref-body--mobile-op .mob-panel--dense {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-height: 0;
    height: 100%;
    overflow: hidden;
    padding: 3px 5px max(3px, env(safe-area-inset-bottom)) 4px;
    justify-content: flex-start;
}

.ref-body--mobile-op .mob-card {
    flex-shrink: 0;
    background: linear-gradient(180deg, var(--mes-panel-raised) 0%, var(--mes-panel) 100%);
    border: 1px solid var(--mes-line-strong);
    border-radius: var(--r-sm);
    box-shadow: 0 1px 0 rgba(255, 255, 255, 0.04) inset, 0 4px 14px rgba(0, 0, 0, 0.22);
    padding: 4px 6px;
}

.ref-body--mobile-op .mob-hero-wrap {
    padding: 3px 6px;
}

.ref-body--mobile-op .mob-status {
    padding: 4px 6px;
    min-height: 0;
    max-height: none;
    border-radius: calc(var(--r-sm) - 2px);
}

.ref-body--mobile-op .mob-order-grid,
.ref-body--mobile-op .mob-mes-grid {
    display: grid;
    gap: 3px 5px;
}

.ref-body--mobile-op .mob-order-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.ref-body--mobile-op .mob-mes-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

.ref-body--mobile-op .mob-cell {
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 0;
    padding: 2px 4px;
    background: rgba(0, 0, 0, 0.22);
    border: 1px solid var(--mes-cell-border);
    border-radius: 4px;
}

.ref-body--mobile-op .mob-cell__k {
    font-size: 0.46rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--mes-muted);
    line-height: 1.1;
}

.ref-body--mobile-op .mob-cell__v {
    font-size: 0.68rem;
    font-weight: 700;
    color: var(--mes-ink);
    line-height: 1.15;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.ref-body--mobile-op .mob-cell--qty .mob-cell__v {
    font-size: 0.78rem;
    font-weight: 900;
    color: var(--mes-blue);
}

.ref-body--mobile-op .mob-cell__v--status {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.62rem;
    font-weight: 900;
}

.ref-body--mobile-op .mob-cell__v--motivo {
    font-size: 0.6rem;
    color: var(--mes-amber);
    white-space: nowrap;
}

.ref-body--mobile-op .mob-cell__mono {
    font-variant-numeric: tabular-nums;
}

.ref-body--mobile-op .mob-apont__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 6px;
    margin-bottom: 3px;
}

.ref-body--mobile-op .mob-apont__htitle {
    font-size: 0.5rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--mes-muted);
}

.ref-body--mobile-op .mob-apont__hratio {
    font-size: 0.58rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    color: var(--mes-blue-mid);
}

.ref-body--mobile-op .mob-apont__track-wrap {
    flex: 1 1 auto;
    min-width: 0;
}

.ref-body--mobile-op .mob-apont__track {
    position: relative;
    height: 16px;
}

.ref-body--mobile-op .mob-apont__pct-in {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.58rem;
    font-weight: 900;
    color: #fff;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.65);
    pointer-events: none;
}

.ref-body--mobile-op .mob-kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 3px;
}

.ref-body--mobile-op .mob-kpi-item {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding: 3px 4px;
    background: rgba(0, 0, 0, 0.25);
    border: 1px solid var(--mes-cell-border);
    border-radius: 4px;
    min-width: 0;
}

.ref-body--mobile-op .mob-kpi-k {
    font-size: 0.44rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--mes-muted);
}

.ref-body--mobile-op .mob-kpi-v {
    font-size: 0.68rem;
    font-weight: 900;
    font-variant-numeric: tabular-nums;
    color: var(--mes-ink);
    line-height: 1.1;
}

.ref-body--mobile-op .mob-kpi-item--warn .mob-kpi-v {
    color: var(--mes-orange);
}

.ref-body--mobile-op .mob-kpi-v--sm {
    font-size: 0.55rem;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.ref-body--mobile-op .mob-kpi-dia {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-top: 3px;
    padding: 3px 5px;
    background: rgba(94, 176, 214, 0.1);
    border: 1px solid rgba(94, 176, 214, 0.25);
    border-radius: 4px;
}

.ref-body--mobile-op .mob-kpi-dia__k {
    font-size: 0.48rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--mes-muted);
}

.ref-body--mobile-op .mob-kpi-dia__v {
    font-size: 0.82rem;
    font-weight: 900;
    color: var(--mes-blue-mid);
    font-variant-numeric: tabular-nums;
}

.ref-body--mobile-op .mob-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 2px 4px;
    border-top: 1px solid var(--mes-line);
    flex-shrink: 0;
}

.ref-body--mobile-op .mob-foot__tag,
.ref-body--mobile-op .mob-foot__meta {
    font-size: 0.48rem;
    font-weight: 700;
    color: var(--mes-muted);
}

.ref-body--mobile-op .mob-foot__meta strong {
    color: var(--mes-blue-mid);
    font-weight: 900;
}

.ref-body--mobile-op .mob-cmds {
    flex-shrink: 0;
    margin-top: auto;
}

.ref-body--mobile-op .mob-side__list .hmi-queue__card--mob-op {
    padding: 4px 5px !important;
}

.ref-body--mobile-op .mob-side__list .hmi-queue__mob-prod {
    font-size: 0.58rem;
    -webkit-line-clamp: 2;
}

.ref-body--mobile-op .mob-side__list .hmi-queue__mob-badge {
    font-size: 0.44rem;
    font-weight: 900;
    letter-spacing: 0.06em;
    padding: 1px 4px;
    border-radius: 3px;
    background: rgba(0, 0, 0, 0.35);
    color: var(--mes-blue);
}

.ref-body--mobile-op .hmi-queue__card--mob-op[data-mob-st="run"] .hmi-queue__mob-badge {
    color: var(--mes-green);
}

.ref-body--mobile-op .hmi-queue__card--mob-op[data-mob-st="stop"] .hmi-queue__mob-badge {
    color: var(--mes-amber);
}

.ref-body--mobile-op .mob-pedido__row--med,
.ref-body--mobile-op .mob-pedido {
    display: none !important;
}

.ref-body--iphone-12pm .mob-body {
    grid-template-columns: 112px minmax(0, 1fr);
}

.ref-body--iphone-12pm .mob-mes-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.ref-body--iphone-12pm .mob-kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.ref-body--iphone-12pm .mob-panel--dense {
    gap: 2px;
}

'''

marker = "    .tablet-remote-maint {"
if CSS.strip() not in text2 and marker in text2:
    text2 = text2.replace(marker, CSS + marker, 1)

# syncMobPanel simplify - remove redundant field updates
old_sync = '''            function syncMobPanel() {
                if (!document.body.classList.contains("ref-body--mobile-op")) return;
                var p = typeof getAtual === "function" ? getAtual() : null;
                var maq = (typeof estado !== "undefined" && estado) ? estado.maquina || {} : {};
                var prodParts = p ? parseProduto(p.produto) : { codigo: "—", medida: "—" };
                var codPed = p && String(p.cod || "").trim() ? String(p.cod).trim() : prodParts.codigo;
                var el;
                var medTxt = p ? disp(medidaComPeso(p.produto)) : "—";
                el = document.getElementById("mob-f-codigo");
                if (el) {
                    if (p) {
                        var prodLine = disp(codPed);
                        if (medTxt && medTxt !== "—") prodLine += " · " + medTxt;
                        el.textContent = prodLine;
                    } else {
                        el.textContent = "—";
                    }
                }
                el = document.getElementById("mob-f-medida");
                if (el) el.textContent = medTxt;
                el = document.getElementById("mob-f-quantidade");
                if (el) el.textContent = p ? fmtInt(toInt(p.quantidade, 0)) : "0";
                el = document.getElementById("mob-hmi-op-combo");
                if (el) el.textContent = formatOpComboText(maq, true);
            }'''

new_sync = '''            function syncMobPanel() {
                if (!document.body.classList.contains("ref-body--mobile-op")) return;
                var maq = (typeof estado !== "undefined" && estado) ? estado.maquina || {} : {};
                var comboEl = document.getElementById("hmi-op-combo");
                if (comboEl) comboEl.textContent = formatOpComboText(maq || {}, true);
            }'''

if old_sync in text2:
    text2 = text2.replace(old_sync, new_sync, 1)

# renderLista mobile richer
old_mob_render = '''                    if (mobileOp) {
                        var mobSt = "wait";
                        if (p.finalizado) mobSt = "done";
                        else if (isCurrent && isRun) mobSt = "run";
                        else if (isCurrent) mobSt = "stop";
                        row.innerHTML =
                            '<span class="hmi-queue__card hmi-queue__card--mob-op" data-mob-st="' +
                            mobSt +
                            '">' +
                            '<span class="hmi-queue__mob-head">' +
                            '<span class="hmi-queue__num">#' +
                            escHtml(osRef) +
                            "</span></span>" +
                            '<span class="hmi-queue__mob-prod">' +
                            escHtml(mobProd) +
                            "</span>" +
                            '<span class="hmi-queue__mob-qty">' +
                            escHtml(qVal) +
                            "</span></span>";
                    } else {'''

new_mob_render = '''                    if (mobileOp) {
                        var mobSt = "wait";
                        if (p.finalizado) mobSt = "done";
                        else if (isCurrent && isRun) mobSt = "run";
                        else if (isCurrent) mobSt = "stop";
                        var badgeShort = p.finalizado ? "OK" : (isCurrent && isRun ? "RUN" : (isCurrent ? "STOP" : "···"));
                        row.innerHTML =
                            '<span class="hmi-queue__card hmi-queue__card--mob-op" data-mob-st="' +
                            mobSt +
                            '">' +
                            '<span class="hmi-queue__mob-head">' +
                            '<span class="hmi-queue__num">#' + escHtml(osRef) + "</span>" +
                            '<span class="hmi-queue__mob-badge">' + escHtml(badgeShort) + "</span></span>" +
                            '<span class="hmi-queue__mob-prod">' + escHtml(mobProd) + "</span>" +
                            '<span class="hmi-queue__mob-qty">' + escHtml(qVal) + "</span></span>";
                    } else {'''

if old_mob_render in text2:
    text2 = text2.replace(old_mob_render, new_mob_render, 1)

# updateFields safe getElementById - optional guard for banner
# ft-prod-time duplicate in stash and foot - only one id after swap; remove duplicate data-tablet-id from foot strong
P.write_text(text2, encoding="utf-8")
print("patched OK", "lines", start + 1, "to", end + 1)
