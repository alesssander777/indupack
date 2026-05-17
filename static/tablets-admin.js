/**
 * Painel administrativo de terminais — atualização ao vivo e ações remotas.
 */
(function () {
    "use strict";

    var grid = document.getElementById("tb-term-grid");
    if (!grid) return;

    var kpiOn = document.getElementById("tb-kpi-on");
    var kpiOff = document.getElementById("tb-kpi-off");
    var kpiSync = document.getElementById("tb-kpi-sync");
    var modal = document.getElementById("tb-modal");
    var modalTitle = document.getElementById("tb-modal-title");
    var modalBody = document.getElementById("tb-modal-body");
    var modalClose = document.getElementById("tb-modal-close");
    var pollMs = 4000;

    function esc(s) {
        var d = document.createElement("div");
        d.textContent = s == null ? "" : String(s);
        return d.innerHTML;
    }

    function statusDot(tom) {
        if (tom === "ok") return "🟢 ";
        if (tom === "warn") return "🟡 ";
        if (tom === "off") return "🔴 ";
        return "⚪ ";
    }

    function heartbeatTxt(seg) {
        if (seg == null || seg < 0) return "—";
        if (seg < 60) return "há " + seg + " s";
        if (seg < 3600) return "há " + Math.floor(seg / 60) + " min";
        return "há " + Math.floor(seg / 3600) + " h";
    }

    function renderCard(t) {
        var mid = t.maquina_id;
        var online = !!t.online;
        var cls = "tb-term" + (online ? " tb-term--online" : " tb-term--offline");
        if (t.manutencao) cls += " tb-term--maint";
        var batCls = "tb-mini__v";
        if (t.bateria_tom === "baixa") batCls += " tb-mini__v--bat-low";
        else if (t.bateria_tom === "carregando") batCls += " tb-mini__v--bat-chg";

        return (
            '<article class="' +
            cls +
            '" data-maquina-id="' +
            mid +
            '">' +
            '<div class="tb-term__topline" aria-hidden="true"></div>' +
            '<div class="tb-term__glow" aria-hidden="true"></div>' +
            '<div class="tb-term__sheen" aria-hidden="true"></div>' +
            '<header class="tb-term__head">' +
            '<div class="tb-term__head-left">' +
            '<div class="tb-term__device" aria-hidden="true">' +
            '<svg class="tb-term__device-svg" width="26" height="26" viewBox="0 0 24 24" fill="none"><rect x="4" y="2" width="16" height="20" rx="2" stroke="currentColor" stroke-width="1.75"/><path d="M9 19h6" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/></svg>' +
            "</div>" +
            '<div class="tb-term__titles">' +
            '<span class="tb-term__eyebrow">Terminal industrial</span>' +
            "<h3 class=\"tb-term__name\">" +
            esc(t.identificador) +
            "</h3>" +
            "</div>" +
            "</div>" +
            '<div class="tb-term__head-right">' +
            (online
                ? '<span class="tb-realtime"><span class="tb-realtime__dot"></span> Ao vivo</span>'
                : "") +
            '<span class="tb-badge ' +
            (online ? "tb-badge--live" : "tb-badge--down") +
            '">' +
            esc(t.terminal_conexao_label) +
            "</span>" +
            "</div>" +
            "</header>" +
            '<div class="tb-term__machine-bar">' +
            '<span class="tb-term__machine-k">Máquina vinculada</span>' +
            '<p class="tb-term__machine-v">' +
            esc(t.maquina_nome) +
            '<span class="tb-term__hash"> #' +
            mid +
            "</span></p>" +
            "</div>" +
            '<div class="tb-status-row" aria-label="Status">' +
            '<div class="tb-status tb-status--' +
            esc(t.maquina_status_tom || "neutral") +
            '">' +
            '<span class="tb-status__k">Máquina</span>' +
            '<span class="tb-status__v">' +
            statusDot(t.maquina_status_tom === "ok" ? "ok" : "neutral") +
            esc(t.maquina_status_label) +
            "</span>" +
            "</div>" +
            '<div class="tb-status tb-status--' +
            esc(t.terminal_status_tom || "off") +
            '">' +
            '<span class="tb-status__k">Terminal</span>' +
            '<span class="tb-status__v">' +
            statusDot(t.terminal_status_tom) +
            esc(t.terminal_status_label) +
            "</span>" +
            "</div>" +
            '<div class="tb-status tb-status--' +
            (t.operador && t.operador !== "—" ? "ok" : "neutral") +
            '">' +
            '<span class="tb-status__k">Operador</span>' +
            '<span class="tb-status__v">' +
            (t.operador && t.operador !== "—" ? "🟢 " : "⚪ ") +
            esc(t.operador_status_label) +
            "</span>" +
            "</div>" +
            "</div>" +
            '<div class="tb-term__dash">' +
            '<div class="tb-mini"><span class="tb-mini__k">Último heartbeat</span><span class="tb-mini__v tb-mono">' +
            esc(heartbeatTxt(t.heartbeat_seg)) +
            "</span></div>" +
            '<div class="tb-mini"><span class="tb-mini__k">Última sincronização</span><span class="tb-mini__v tb-mono">' +
            esc(t.ultimo_acesso_txt) +
            "</span></div>" +
            '<div class="tb-mini"><span class="tb-mini__k">IP</span><span class="tb-mini__v tb-mono">' +
            esc(t.ip) +
            "</span></div>" +
            '<div class="tb-mini"><span class="tb-mini__k">Bateria</span><span class="' +
            batCls +
            '">' +
            esc(t.bateria_txt) +
            "</span></div>" +
            "</div>" +
            '<p class="tb-term__act-hint">Ações do <strong>dispositivo</strong> — não alteram programação nem pedidos.</p>' +
            '<div class="tb-term__actions">' +
            '<button type="button" class="tb-act" data-action="logs" data-id="' +
            mid +
            '" data-name="' +
            esc(t.identificador) +
            '"><span>Logs</span></button>' +
            '<button type="button" class="tb-act" data-action="reiniciar" data-id="' +
            mid +
            '" data-name="' +
            esc(t.identificador) +
            '"><span>Reiniciar</span></button>' +
            '<button type="button" class="tb-act' +
            (t.kiosk ? " tb-act--on" : "") +
            '" data-action="kiosk" data-id="' +
            mid +
            '" data-active="' +
            (t.kiosk ? "1" : "0") +
            '"><span>Kiosk</span></button>' +
            '<button type="button" class="tb-act' +
            (t.manutencao ? " tb-act--on" : "") +
            '" data-action="manutencao" data-id="' +
            mid +
            '" data-active="' +
            (t.manutencao ? "1" : "0") +
            '"><span>Manutenção</span></button>' +
            "</div>" +
            "</article>"
        );
    }

    function renderAll(data) {
        var list = (data && data.terminais) || [];
        var res = (data && data.resumo) || {};
        if (kpiOn) kpiOn.textContent = String(res.online != null ? res.online : 0);
        if (kpiOff) kpiOff.textContent = String(res.offline != null ? res.offline : 0);
        if (kpiSync) kpiSync.textContent = res.ultima_sincronizacao_txt || "—";
        if (!list.length) {
            grid.innerHTML = '<p class="tb-empty">Nenhuma máquina cadastrada.</p>';
            return;
        }
        grid.innerHTML = list.map(renderCard).join("");
    }

    function poll() {
        fetch("/api/terminais", { credentials: "same-origin" })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                if (data && data.ok) renderAll(data);
            })
            .catch(function () {});
    }

    function openModal(title, html) {
        if (!modal) return;
        modalTitle.textContent = title;
        modalBody.innerHTML = html;
        modal.hidden = false;
        modal.setAttribute("aria-hidden", "false");
    }

    function closeModal() {
        if (!modal) return;
        modal.hidden = true;
        modal.setAttribute("aria-hidden", "true");
        modalBody.innerHTML = "";
    }

    function showLogs(id, name) {
        fetch("/api/terminais/" + id + "/logs", { credentials: "same-origin" })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                var rows = (data && data.logs) || [];
                var html;
                if (!rows.length) {
                    html = '<p class="tb-modal-empty">Nenhum registro operacional ainda.</p>';
                } else {
                    html =
                        '<ol class="tb-log-list">' +
                        rows
                            .map(function (row) {
                                return (
                                    "<li class=\"tb-log-item\"><span class=\"tb-log-time\">" +
                                    esc(row.ts_txt) +
                                    '</span><span class="tb-log-title">' +
                                    esc(row.titulo) +
                                    "</span>" +
                                    (row.detalhe
                                        ? '<span class="tb-log-detail">' + esc(row.detalhe) + "</span>"
                                        : "") +
                                    "</li>"
                                );
                            })
                            .join("") +
                        "</ol>";
                }
                openModal("Histórico — " + name, html);
            });
    }

    function postAction(url, confirmMsg) {
        if (confirmMsg && !window.confirm(confirmMsg)) return Promise.resolve(null);
        return fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: "{}",
        }).then(function (r) {
            return r.json();
        });
    }

    grid.addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-action]");
        if (!btn) return;
        var action = btn.getAttribute("data-action");
        var id = btn.getAttribute("data-id");
        var name = btn.getAttribute("data-name") || "Terminal";
        if (!id) return;

        if (action === "logs") {
            showLogs(id, name);
            return;
        }
        if (action === "reiniciar") {
            postAction("/api/terminais/" + id + "/reiniciar", "Deseja reiniciar o terminal?\n\nA sessão será recarregada no tablet (não reinicia o servidor).").then(
                function (resp) {
                    if (resp && resp.ok) poll();
                    else if (resp && resp.mensagem) alert(resp.mensagem);
                }
            );
            return;
        }
        if (action === "kiosk") {
            var onK = btn.getAttribute("data-active") !== "1";
            if (onK && !window.confirm("Ativar modo kiosk (tela cheia) neste terminal?")) return;
            if (!onK && !window.confirm("Desativar modo kiosk?")) return;
            fetch("/api/terminais/" + id + "/kiosk", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ativo: onK }),
            })
                .then(function (r) {
                    return r.json();
                })
                .then(function (resp) {
                    if (resp && resp.ok) poll();
                });
            return;
        }
        if (action === "manutencao") {
            var onM = btn.getAttribute("data-active") !== "1";
            if (onM && !window.confirm("Colocar terminal em manutenção?\n\nApontamentos e produção ficarão bloqueados no dispositivo.")) return;
            if (!onM && !window.confirm("Encerrar manutenção deste terminal?")) return;
            fetch("/api/terminais/" + id + "/manutencao", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ativo: onM }),
            })
                .then(function (r) {
                    return r.json();
                })
                .then(function (resp) {
                    if (resp && resp.ok) poll();
                });
        }
    });

    if (modalClose) modalClose.addEventListener("click", closeModal);
    if (modal) {
        modal.addEventListener("click", function (ev) {
            if (ev.target === modal) closeModal();
        });
    }

    poll();
    setInterval(poll, pollMs);
})();
