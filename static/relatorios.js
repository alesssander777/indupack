(function () {
    "use strict";

    var state = { payload: null, charts: {}, meta: null };

    function pad(n) {
        return String(n).padStart(2, "0");
    }
    function fmtISO(d) {
        return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
    }
    function today() {
        return fmtISO(new Date());
    }
    function presetMes() {
        var d = new Date();
        var ini = new Date(d.getFullYear(), d.getMonth(), 1);
        var fim = new Date(d.getFullYear(), d.getMonth() + 1, 0);
        return { inicio: fmtISO(ini), fim: fmtISO(fim) };
    }
    function presetSemana() {
        var fim = new Date();
        var ini = new Date(fim);
        ini.setDate(ini.getDate() - 6);
        return { inicio: fmtISO(ini), fim: fmtISO(fim) };
    }

    function tickClock() {
        var now = new Date();
        var clk = document.getElementById("rel-live-clock");
        var dt = document.getElementById("rel-live-date");
        var ts = now.toLocaleTimeString("pt-BR", { hour12: false });
        if (clk) {
            clk.textContent = ts;
            try {
                clk.setAttribute("datetime", now.toISOString());
            } catch (e) {}
        }
        if (dt) {
            dt.textContent = now.toLocaleDateString("pt-BR", {
                weekday: "long",
                day: "2-digit",
                month: "long",
                year: "numeric",
            });
        }
    }

    function setConnStatus(ok, msg) {
        var el = document.getElementById("rel-conn-status");
        if (!el) return;
        var txt = el.querySelector(".rel-online-pill__txt");
        var offline = ok === false;
        var busy = ok === null;
        el.classList.toggle("is-offline", offline);
        el.classList.toggle("is-busy", busy);
        if (txt) txt.textContent = msg || (offline ? "Offline" : busy ? "Atualizando…" : "Sincronizado");
    }

    function qs() {
        var p = new URLSearchParams();
        p.set("inicio", document.getElementById("rel-inicio").value);
        p.set("fim", document.getElementById("rel-fim").value);
        var mq = document.getElementById("rel-maquina").value;
        if (mq) p.set("maquina", mq);
        var op = document.getElementById("rel-operador").value.trim();
        if (op) p.set("operador", op);
        var tu = document.getElementById("rel-turno").value.trim();
        if (tu) p.set("turno", tu);
        var pr = document.getElementById("rel-produto").value.trim();
        if (pr) p.set("produto", pr);
        var st = document.getElementById("rel-setor").value.trim();
        if (st) p.set("setor", st);
        return p.toString();
    }

    function destroyChart(key) {
        if (state.charts[key]) {
            state.charts[key].destroy();
            delete state.charts[key];
        }
    }

    function barChart(canvasId, labels, values, label, colorHex) {
        var el = document.getElementById(canvasId);
        if (!el || typeof Chart === "undefined") return;
        destroyChart(canvasId);
        if (!labels || !labels.length) {
            return;
        }
        var root = getComputedStyle(document.documentElement);
        var col = root.getPropertyValue("--ip-brand-primary").trim() || "#1a4a62";
        var gridCol = "rgba(148, 163, 184, 0.12)";
        var tickCol = "#94a3b8";
        state.charts[canvasId] = new Chart(el.getContext("2d"), {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: label,
                        data: values,
                        backgroundColor: colorHex || col,
                        borderRadius: 6,
                        borderSkipped: false,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        ticks: { color: tickCol, maxRotation: 45, minRotation: 0, font: { size: 10 } },
                        grid: { color: gridCol },
                        border: { color: gridCol },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: { color: tickCol, font: { size: 10 } },
                        grid: { color: gridCol },
                        border: { color: gridCol },
                    },
                },
            },
        });
    }

    function fillTable(tbodyId, rows, cols) {
        var tb = document.getElementById(tbodyId);
        if (!tb) return;
        tb.innerHTML = "";
        rows.forEach(function (r) {
            var tr = document.createElement("tr");
            cols.forEach(function (c) {
                var td = document.createElement("td");
                td.textContent = r[c] != null ? String(r[c]) : "—";
                tr.appendChild(td);
            });
            tb.appendChild(tr);
        });
    }

    function formatDateBR(iso) {
        if (!iso || typeof iso !== "string") return "—";
        var p = iso.split("-");
        if (p.length !== 3) return iso;
        return p[2] + "/" + p[1] + "/" + p[0];
    }
    function fmtNum(n) {
        if (n === null || n === undefined || n === "") return "—";
        try {
            return Number(n).toLocaleString("pt-BR");
        } catch (e) {
            return String(n);
        }
    }

    function renderAll() {
        var d = state.payload;
        if (!d || !d.ok) return;
        var kp = d.kpis || {};
        var fl = d.filtros || {};
        var pr = document.getElementById("rel-periodo-resumo");
        if (pr) pr.textContent = formatDateBR(fl.inicio) + " — " + formatDateBR(fl.fim);

        document.getElementById("kpi-prod").textContent = fmtNum(kp.producao_total);
        var sub = document.getElementById("kpi-prod-sub");
        if (sub) sub.textContent = "unidades registradas no período";

        document.getElementById("kpi-par").textContent = kp.tempo_parado_fmt || "—";
        document.getElementById("kpi-disp").textContent =
            kp.disponibilidade_proxy_pct != null ? kp.disponibilidade_proxy_pct + "%" : "—";
        document.getElementById("kpi-oee").textContent = kp.oee_proxy_pct != null ? kp.oee_proxy_pct + "%" : "—";

        var evInline = document.getElementById("kpi-ev-inline");
        if (evInline) evInline.textContent = String(kp.eventos_producao != null ? kp.eventos_producao : "—");

        var di = d.diario || {};
        var sem = d.semanal || {};
        var men = d.mensal || {};

        var cm = sem.comparacao_maquinas || [];
        var bestM = cm[0];
        var nm = document.getElementById("kpi-best-maq-name");
        var vm = document.getElementById("kpi-best-maq-val");
        if (nm && vm) {
            if (bestM && bestM.nome) {
                nm.textContent = bestM.nome;
                vm.textContent = fmtNum(bestM.producao) + " un.";
            } else {
                nm.textContent = "—";
                vm.textContent = "—";
            }
        }
        var po = di.por_operador || [];
        var bestO = po[0];
        var no = document.getElementById("kpi-best-op-name");
        var vo = document.getElementById("kpi-best-op-val");
        if (no && vo) {
            if (bestO && bestO.nome && bestO.nome !== "—") {
                no.textContent = bestO.nome;
                vo.textContent = fmtNum(bestO.quantidade) + " un.";
            } else {
                no.textContent = "—";
                vo.textContent = "—";
            }
        }

        fillTable(
            "tb-dia-maq",
            di.por_maquina || [],
            ["nome", "quantidade"]
        );
        fillTable(
            "tb-dia-op",
            di.por_operador || [],
            ["nome", "quantidade"]
        );
        fillTable(
            "tb-dia-turno",
            di.por_turno || [],
            ["nome", "quantidade"]
        );
        fillTable(
            "tb-dia-prod",
            di.produtos || [],
            ["nome", "quantidade"]
        );
        fillTable(
            "tb-dia-par",
            di.paradas_motivo || [],
            ["motivo", "duracao_fmt"]
        );

        fillTable(
            "tb-sem-maq",
            sem.comparacao_maquinas || [],
            ["nome", "producao", "tempo_parado_fmt", "eficiencia_est"]
        );
        fillTable("tb-sem-turno", sem.comparacao_turnos || [], ["nome", "quantidade"]);
        fillTable("tb-sem-prod", sem.produtos_top || [], ["nome", "quantidade"]);

        fillTable(
            "tb-mes-maq",
            men.ranking_maquinas || [],
            ["nome", "producao", "tempo_parado_fmt", "eficiencia_est"]
        );
        fillTable("tb-mes-op", men.ranking_operadores || [], ["nome", "quantidade"]);

        document.getElementById("mes-total").textContent = String(men.producao_total != null ? men.producao_total : "—");
        document.getElementById("mes-oee").textContent =
            men.oee_medio_proxy_pct != null ? men.oee_medio_proxy_pct + "%" : "—";
        document.getElementById("mes-perdas").textContent = String(
            men.perdas_estimadas != null ? men.perdas_estimadas : "—"
        );
        document.getElementById("mes-produt").textContent =
            men.produtividade_un_h != null ? String(men.produtividade_un_h) : "—";

        fillTable(
            "tb-det",
            d.detalhado || [],
            ["produto", "operador", "turno", "maquina", "quantidade", "horario", "tempo_producao", "tempo_parado", "observacoes"]
        );

        var labelsM = (sem.comparacao_maquinas || []).map(function (x) {
            return (x.nome || "").slice(0, 14);
        });
        var valsM = (sem.comparacao_maquinas || []).map(function (x) {
            return Number(x.producao) || 0;
        });
        barChart("chart-maq", labelsM, valsM, "Produção", "rgba(56, 189, 248, 0.85)");

        var labelsP = (sem.produtos_top || []).slice(0, 8).map(function (x) {
            return (x.nome || "—").slice(0, 18);
        });
        var valsP = (sem.produtos_top || [])
            .slice(0, 8)
            .map(function (x) {
                return Number(x.quantidade) || 0;
            });
        barChart("chart-prod", labelsP, valsP, "Qtd", "rgba(52, 211, 153, 0.82)");

        var notes = document.getElementById("rel-notes");
        if (notes) {
            notes.innerHTML = "";
            (d.notas_metodologia || []).forEach(function (t) {
                var li = document.createElement("li");
                li.textContent = t;
                notes.appendChild(li);
            });
        }
        if (d.aviso) {
            var w = document.getElementById("rel-warn");
            if (w) {
                w.textContent = d.aviso;
                w.hidden = false;
            }
        } else {
            var w2 = document.getElementById("rel-warn");
            if (w2) w2.hidden = true;
        }
    }

    function loadMeta() {
        return fetch("/api/relatorios/meta", { credentials: "same-origin" }).then(function (r) {
            if (!r.ok) throw new Error("meta");
            return r.json();
        });
    }

    function loadData() {
        document.getElementById("rel-loading").hidden = false;
        setConnStatus(null, "Atualizando…");
        return fetch("/api/relatorios/dados?" + qs(), { credentials: "same-origin" })
            .then(function (r) {
                if (r.status === 401) {
                    window.location.href = "/login";
                    return null;
                }
                if (!r.ok) throw new Error("dados");
                return r.json();
            })
            .then(function (j) {
                document.getElementById("rel-loading").hidden = true;
                state.payload = j;
                setConnStatus(true, "Sincronizado");
                renderAll();
            })
            .catch(function () {
                document.getElementById("rel-loading").hidden = true;
                setConnStatus(false, "Sem conexão");
                alert("Não foi possível carregar os relatórios.");
            });
    }

    function wireTabs() {
        var tabs = document.querySelectorAll(".rel-tabs button");
        var panels = document.querySelectorAll(".rel-panels section");
        tabs.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var id = btn.getAttribute("data-panel");
                tabs.forEach(function (b) {
                    b.setAttribute("aria-selected", b === btn ? "true" : "false");
                });
                panels.forEach(function (p) {
                    p.hidden = p.id !== "panel-" + id;
                });
            });
        });
    }

    function wireFilters() {
        document.getElementById("rel-aplicar").addEventListener("click", function () {
            loadData();
        });
        document.getElementById("rel-hoje").addEventListener("click", function () {
            var t = today();
            document.getElementById("rel-inicio").value = t;
            document.getElementById("rel-fim").value = t;
            loadData();
        });
        document.getElementById("rel-semana").addEventListener("click", function () {
            var p = presetSemana();
            document.getElementById("rel-inicio").value = p.inicio;
            document.getElementById("rel-fim").value = p.fim;
            loadData();
        });
        document.getElementById("rel-mes").addEventListener("click", function () {
            var p = presetMes();
            document.getElementById("rel-inicio").value = p.inicio;
            document.getElementById("rel-fim").value = p.fim;
            loadData();
        });
    }

    function wireExports() {
        var q = function () {
            return qs();
        };
        document.getElementById("rel-xlsx").addEventListener("click", function () {
            window.location.href = "/api/relatorios/export.xlsx?" + q();
        });
        document.getElementById("rel-pdf").addEventListener("click", function () {
            window.location.href = "/api/relatorios/export.pdf?" + q();
        });
        document.getElementById("rel-mail-btn").addEventListener("click", function () {
            var em = document.getElementById("rel-mail-to").value.trim();
            var toast = document.getElementById("rel-mail-toast");
            toast.textContent = "";
            toast.className = "rel-toast";
            if (!em || em.indexOf("@") < 0) {
                toast.textContent = "Informe um e-mail válido.";
                toast.className = "rel-toast rel-toast--err";
                return;
            }
            var body = {
                email: em,
                inicio: document.getElementById("rel-inicio").value,
                fim: document.getElementById("rel-fim").value,
                maquina: document.getElementById("rel-maquina").value || null,
                operador: document.getElementById("rel-operador").value || null,
                turno: document.getElementById("rel-turno").value || null,
                produto: document.getElementById("rel-produto").value || null,
                setor: document.getElementById("rel-setor").value || null,
            };
            document.getElementById("rel-mail-btn").disabled = true;
            fetch("/api/relatorios/email-pdf", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            })
                .then(function (r) {
                    return r.json().then(function (j) {
                        return { status: r.status, j: j };
                    });
                })
                .then(function (x) {
                    document.getElementById("rel-mail-btn").disabled = false;
                    toast.textContent = x.j.mensagem || x.j.erro || "Resposta sem mensagem.";
                    toast.className = "rel-toast " + (x.j.ok ? "rel-toast--ok" : "rel-toast--err");
                })
                .catch(function () {
                    document.getElementById("rel-mail-btn").disabled = false;
                    toast.textContent = "Falha de rede ao enviar.";
                    toast.className = "rel-toast rel-toast--err";
                });
        });
    }

    function populateMeta(meta) {
        state.meta = meta;
        var sel = document.getElementById("rel-maquina");
        sel.innerHTML = '<option value="">Todas</option>';
        (meta.maquinas || []).forEach(function (m) {
            var o = document.createElement("option");
            o.value = String(m.id);
            o.textContent = m.nome + (m.setor ? " (" + m.setor + ")" : "");
            sel.appendChild(o);
        });
        var dl = document.getElementById("rel-setor-list");
        if (dl) {
            dl.innerHTML = "";
            (meta.setores || []).forEach(function (s) {
                var opt = document.createElement("option");
                opt.value = s;
                dl.appendChild(opt);
            });
        }
    }

    function loadAgendaStub() {
        fetch("/api/relatorios/agendamento-stub", { credentials: "same-origin" })
            .then(function (r) {
                return r.json();
            })
            .then(function (j) {
                var pre = document.getElementById("rel-agenda-json");
                if (pre) pre.textContent = JSON.stringify(j.estrutura_futura || {}, null, 2);
            })
            .catch(function () {});
    }

    document.addEventListener("DOMContentLoaded", function () {
        var t = today();
        document.getElementById("rel-inicio").value = t;
        document.getElementById("rel-fim").value = t;
        wireTabs();
        wireFilters();
        wireExports();
        tickClock();
        setConnStatus(null, "Conectando…");
        setInterval(tickClock, 1000);
        loadMeta()
            .then(function (m) {
                populateMeta(m);
                return loadData();
            })
            .catch(function () {
                setConnStatus(false, "Erro de acesso");
                alert("Sem permissão ou erro ao carregar filtros.");
            });
        loadAgendaStub();
    });
})();
