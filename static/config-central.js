/**
 * Painel central de configurações INDUPACK (dados via área administrativa).
 */
(function () {
    function $(id) {
        return document.getElementById(id);
    }
    function fmtBytes(n) {
        if (n == null || isNaN(n)) return "—";
        var u = ["B", "KB", "MB", "GB"];
        var i = 0;
        var v = Number(n);
        while (v >= 1024 && i < u.length - 1) {
            v /= 1024;
            i++;
        }
        return (i === 0 ? String(Math.round(v)) : v.toFixed(1)) + " " + u[i];
    }
    function fmtDT(iso) {
        if (!iso) return "—";
        var d = new Date(iso);
        return isNaN(d.getTime()) ? String(iso) : d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "medium" });
    }
    function toast(el, msg, ok) {
        if (!el) return;
        el.textContent = msg;
        el.className = "cfg-toast" + (ok ? " cfg-toast--ok" : " cfg-toast--err");
        el.hidden = false;
        clearTimeout(el._t);
        el._t = setTimeout(function () {
            el.hidden = true;
        }, 5200);
    }
    function api(method, url, body) {
        var opt = { method: method, credentials: "same-origin" };
        if (body !== undefined) {
            opt.headers = { "Content-Type": "application/json" };
            opt.body = JSON.stringify(body);
        }
        return fetch(url, opt).then(function (r) {
            return r.json().then(function (j) {
                return { okHttp: r.ok, j: j };
            });
        });
    }
    var state = null;

    function load() {
        return api("GET", "/admin/config/completo").then(function (x) {
            if (!x.okHttp || !x.j || !x.j.ok) throw new Error("load");
            state = x.j;
            render();
        });
    }

    function render() {
        if (!state) return;
        var p = state.painel || {};
        var s = state.settings || {};
        $("v-ver").textContent = p.versao || "—";
        $("v-db").textContent = p.banco_conectado ? "Conectado" : "Indisponível";
        $("v-db").className = "cfg-kv__v" + (p.banco_conectado ? " cfg-ok" : " cfg-bad");
        $("v-srv").textContent = p.servidor_online ? "Online" : "—";
        $("v-hora").textContent = fmtDT(p.servidor_iso);
        $("v-maq-c").textContent = String(p.maquinas_cadastradas != null ? p.maquinas_cadastradas : "—");
        $("v-maq-a").textContent = String(p.maquinas_ativas != null ? p.maquinas_ativas : "—");
        $("v-user").textContent = String(p.usuarios != null ? p.usuarios : "—");
        $("v-tab").textContent = String(p.tablets_com_codigo != null ? p.tablets_com_codigo : "—");

        var b = (p.backup || {});
        $("bk-ult").textContent = fmtDT(b.ultimo_iso);
        $("bk-qtd").textContent =
            String(b.count_total != null ? b.count_total : 0) +
            " (" +
            (b.count_db || 0) +
            " cópias de dados · " +
            (b.count_zip || 0) +
            " pacotes completos)";
        $("bk-tam").textContent = fmtBytes(b.total_bytes);
        $("bk-st").textContent = "Operacional";

        var pr = s.producao || {};
        $("f-parada-max").value = pr.parada_max_minutos != null ? pr.parada_max_minutos : "";
        $("f-meta-glob").value = pr.meta_padrao_global != null ? pr.meta_padrao_global : "";
        $("f-ef").value = pr.eficiencia_metodo || "padrao";
        $("f-prog").value = pr.progresso_modo || "linear";
        $("f-prod-mod").value = pr.producao_total_modo || "substituicao";
        $("f-reset-os").checked = !!pr.reset_os_automatico;

        var vis = s.visual || {};
        $("f-empresa").value = vis.nome_empresa || "";
        $("f-cor").value = vis.cor_principal || "#1a4a62";
        $("f-fs").checked = !!vis.fullscreen_padrao;
        $("f-title").value = vis.titulo_navegador || "";
        $("f-logo-url").textContent = vis.logo_url || "(nenhum)";

        var seg = s.seguranca || {};
        $("f-sess").value = seg.sessao_max_minutos != null ? seg.sessao_max_minutos : "";
        $("f-lo").value = seg.logout_auto_minutos != null ? seg.logout_auto_minutos : "";
        $("f-multi").checked = !!seg.multiplos_logins;
        $("f-adm-av").checked = !!seg.admin_padrao_aviso;

        renderMaquinas(state.maquinas || []);
        renderOps(state.operadores || []);
        renderParadas(state.paradas || []);
    }

    function renderMaquinas(rows) {
        var tb = $("tbl-maq");
        if (!tb) return;
        tb.innerHTML = rows
            .map(function (m) {
                return (
                    "<tr data-id='" +
                    m.id +
                    "'><td>" +
                    m.id +
                    "</td><td><input class='cfg-inp cfg-inp--sm' data-f='nome' value='" +
                    esc(m.nome) +
                    "'></td><td><input class='cfg-inp cfg-inp--sm' data-f='setor' value='" +
                    esc(m.setor) +
                    "'></td><td><input class='cfg-inp cfg-inp--sm' type='number' data-f='meta' value='" +
                    esc(String(m.meta)) +
                    "'></td><td><input type='checkbox' data-f='ativo' " +
                    (m.ativo ? "checked" : "") +
                    "></td><td><button type='button' class='cfg-mini' data-act='save-maq'>Guardar</button></td></tr>"
                );
            })
            .join("");
    }
    function esc(s) {
        return String(s || "")
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;");
    }
    function renderOps(rows) {
        var tb = $("tbl-op");
        if (!tb) return;
        tb.innerHTML = rows
            .map(function (o) {
                return (
                    "<tr data-id='" +
                    o.id +
                    "'><td><input class='cfg-inp cfg-inp--sm' data-f='nome' value='" +
                    esc(o.nome) +
                    "'></td><td><input class='cfg-inp cfg-inp--sm' data-f='turno' value='" +
                    esc(o.turno_padrao) +
                    "'></td><td><select class='cfg-inp cfg-inp--sm' data-f='nivel'>" +
                    optNivel(o.nivel_acesso) +
                    "</select></td><td><input type='checkbox' data-f='ativo' " +
                    (o.ativo ? "checked" : "") +
                    "></td><td><button type='button' class='cfg-mini' data-act='save-op'>Guardar</button> <button type='button' class='cfg-mini cfg-mini--danger' data-act='del-op'>Remover</button></td></tr>"
                );
            })
            .join("");
    }
    function optNivel(cur) {
        var labels = { operador: "Operador", supervisor: "Supervisor", manutencao: "Manutenção", admin: "Administrador" };
        var opts = ["operador", "supervisor", "manutencao", "admin"];
        return opts
            .map(function (v) {
                return "<option value='" + v + "'" + (v === cur ? " selected" : "") + ">" + (labels[v] || v) + "</option>";
            })
            .join("");
    }
    function renderParadas(rows) {
        var tb = $("tbl-par");
        if (!tb) return;
        tb.innerHTML = rows
            .map(function (r) {
                return (
                    "<tr data-id='" +
                    r.id +
                    "'><td><strong>" +
                    esc(r.codigo) +
                    "</strong></td><td><input class='cfg-inp cfg-inp--sm' data-f='rotulo' value='" +
                    esc(r.rotulo) +
                    "'></td><td><input class='cfg-inp cfg-inp--sm' data-f='cat' value='" +
                    esc(r.categoria) +
                    "'></td><td><input type='checkbox' data-f='ativo' " +
                    (r.ativo ? "checked" : "") +
                    "></td><td><input class='cfg-inp cfg-inp--sm' type='number' data-f='ordem' value='" +
                    esc(String(r.ordem)) +
                    "'></td><td><button type='button' class='cfg-mini' data-act='save-par'>Guardar</button> <button type='button' class='cfg-mini cfg-mini--danger' data-act='del-par'>Remover</button></td></tr>"
                );
            })
            .join("");
    }

    function saveProducao(ev) {
        ev.preventDefault();
        var body = {
            producao: {
                parada_max_minutos: parseInt($("f-parada-max").value, 10) || 480,
                meta_padrao_global: parseInt($("f-meta-glob").value, 10) || 1000,
                eficiencia_metodo: $("f-ef").value,
                progresso_modo: $("f-prog").value,
                producao_total_modo: $("f-prod-mod").value,
                reset_os_automatico: $("f-reset-os").checked,
            },
        };
        api("PUT", "/admin/config/settings", body).then(function (x) {
            toast($("cfg-toast"), x.okHttp && x.j.ok ? "Parâmetros de produção guardados." : "Não foi possível guardar.", x.okHttp && x.j.ok);
            if (x.okHttp && x.j.ok) load();
        });
    }
    function saveVisual(ev) {
        ev.preventDefault();
        var body = {
            visual: {
                nome_empresa: $("f-empresa").value.trim(),
                cor_principal: $("f-cor").value.trim() || "#1a4a62",
                fullscreen_padrao: $("f-fs").checked,
                titulo_navegador: $("f-title").value.trim(),
            },
        };
        api("PUT", "/admin/config/settings", body).then(function (x) {
            toast($("cfg-toast"), x.okHttp && x.j.ok ? "Identidade visual guardada." : "Não foi possível guardar.", x.okHttp && x.j.ok);
            if (x.okHttp && x.j.ok) {
                setTimeout(function () {
                    window.location.reload();
                }, 650);
            }
        });
    }
    function saveSeg(ev) {
        ev.preventDefault();
        var body = {
            seguranca: {
                sessao_max_minutos: Math.max(30, parseInt($("f-sess").value, 10) || 10080),
                logout_auto_minutos: Math.max(0, parseInt($("f-lo").value, 10) || 0),
                multiplos_logins: $("f-multi").checked,
                admin_padrao_aviso: $("f-adm-av").checked,
            },
        };
        api("PUT", "/admin/config/settings", body).then(function (x) {
            toast(
                $("cfg-toast"),
                x.okHttp && x.j.ok
                    ? "Parâmetros de segurança guardados. Para aplicar o novo tempo de sessão a todos os utilizadores, reinicie o Indupack."
                    : "Não foi possível guardar.",
                x.okHttp && x.j.ok
            );
            if (x.okHttp && x.j.ok) load();
        });
    }

    function postBackup(url, label) {
        api("POST", url).then(function (x) {
            toast($("cfg-toast"), x.okHttp && x.j.ok ? label + " concluído." : "Não foi possível concluir a cópia de segurança.", x.okHttp && x.j.ok);
            load();
        });
    }

    document.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-act]");
        if (!btn) return;
        var tr = btn.closest("tr");
        var act = btn.getAttribute("data-act");
        if (act === "save-maq" && tr) {
            var id = parseInt(tr.getAttribute("data-id"), 10);
            var nome = tr.querySelector("[data-f=nome]").value;
            var setor = tr.querySelector("[data-f=setor]").value;
            var meta = parseInt(tr.querySelector("[data-f=meta]").value, 10);
            var ativo = tr.querySelector("[data-f=ativo]").checked;
            api("PUT", "/admin/config/maquinas/" + id, { nome: nome, setor: setor, meta: meta, ativo: ativo }).then(function (x) {
                toast($("cfg-toast"), x.okHttp && x.j.ok ? "Equipamento atualizado." : "Não foi possível guardar.", x.okHttp && x.j.ok);
                load();
            });
        }
        if (act === "save-op" && tr) {
            var oid = parseInt(tr.getAttribute("data-id"), 10);
            api("PUT", "/admin/config/operadores/" + oid, {
                nome: tr.querySelector("[data-f=nome]").value,
                turno_padrao: tr.querySelector("[data-f=turno]").value,
                nivel_acesso: tr.querySelector("[data-f=nivel]").value,
                ativo: tr.querySelector("[data-f=ativo]").checked,
            }).then(function (x) {
                toast($("cfg-toast"), x.okHttp && x.j.ok ? "Operador atualizado." : "Não foi possível guardar.", x.okHttp && x.j.ok);
                load();
            });
        }
        if (act === "del-op" && tr) {
            var oid2 = parseInt(tr.getAttribute("data-id"), 10);
            if (!confirm("Remover este operador da lista?")) return;
            api("DELETE", "/admin/config/operadores/" + oid2).then(function (x) {
                toast($("cfg-toast"), x.okHttp && x.j.ok ? "Registo removido." : "Não foi possível remover.", x.okHttp && x.j.ok);
                load();
            });
        }
        if (act === "save-par" && tr) {
            var sid = parseInt(tr.getAttribute("data-id"), 10);
            api("PUT", "/admin/config/paradas/" + sid, {
                rotulo: tr.querySelector("[data-f=rotulo]").value,
                categoria: tr.querySelector("[data-f=cat]").value,
                ativo: tr.querySelector("[data-f=ativo]").checked,
                ordem: parseInt(tr.querySelector("[data-f=ordem]").value, 10),
            }).then(function (x) {
                toast($("cfg-toast"), x.okHttp && x.j.ok ? "Motivo de parada atualizado." : "Não foi possível guardar.", x.okHttp && x.j.ok);
                load();
            });
        }
        if (act === "del-par" && tr) {
            var sid2 = parseInt(tr.getAttribute("data-id"), 10);
            if (!confirm("Remover este motivo da lista?")) return;
            api("DELETE", "/admin/config/paradas/" + sid2).then(function (x) {
                toast($("cfg-toast"), x.okHttp && x.j.ok ? "Registo removido." : "Não foi possível remover.", x.okHttp && x.j.ok);
                load();
            });
        }
    });

    document.addEventListener("submit", function (e) {
        var f = e.target;
        if (f.id === "form-nova-maq") {
            e.preventDefault();
            api("POST", "/admin/config/maquinas", {
                nome: $("nm-maq").value,
                setor: $("st-maq").value,
                meta_padrao: parseInt($("mt-maq").value, 10) || 1000,
            }).then(function (x) {
                toast($("cfg-toast"), x.okHttp && x.j.ok ? "Equipamento registado." : (x.j && x.j.erro) || "Não foi possível guardar.", x.okHttp && x.j.ok);
                $("form-nova-maq").reset();
                load();
            });
        }
        if (f.id === "form-novo-op") {
            e.preventDefault();
            api("POST", "/admin/config/operadores", {
                nome: $("op-nome").value,
                turno_padrao: $("op-turno").value,
                nivel_acesso: $("op-nivel").value,
                ativo: true,
            }).then(function (x) {
                toast($("cfg-toast"), x.okHttp && x.j.ok ? "Operador registado." : "Não foi possível guardar.", x.okHttp && x.j.ok);
                f.reset();
                load();
            });
        }
        if (f.id === "form-novo-par") {
            e.preventDefault();
            api("POST", "/admin/config/paradas", {
                codigo: $("par-cod").value,
                rotulo: $("par-rot").value,
                categoria: $("par-cat").value || "geral",
                ativo: true,
            }).then(function (x) {
                toast($("cfg-toast"), x.okHttp && x.j.ok ? "Motivo de parada registado." : "Não foi possível guardar.", x.okHttp && x.j.ok);
                f.reset();
                load();
            });
        }
    });

    document.addEventListener("DOMContentLoaded", function () {
        var fpr = $("form-producao");
        if (fpr) fpr.addEventListener("submit", saveProducao);
        var fvi = $("form-visual");
        if (fvi) fvi.addEventListener("submit", saveVisual);
        var fsg = $("form-seg");
        if (fsg) fsg.addEventListener("submit", saveSeg);
        var b1 = $("btn-bk-db");
        var b2 = $("btn-bk-full");
        if (b1) b1.addEventListener("click", function () {
            postBackup("/backup/database", "Cópia da base de dados");
        });
        if (b2) b2.addEventListener("click", function () {
            postBackup("/backup/full", "Cópia completa (pacote)");
        });
        var logo = $("form-logo");
        if (logo) {
            logo.addEventListener("submit", function (ev) {
                ev.preventDefault();
                var inp = $("file-logo");
                if (!inp || !inp.files || !inp.files[0]) return;
                var fd = new FormData();
                fd.append("file", inp.files[0]);
                fetch("/admin/config/logo", { method: "POST", body: fd, credentials: "same-origin" }).then(function (r) {
                    return r.json();
                }).then(function (j) {
                    toast($("cfg-toast"), j.ok ? "Logótipo enviado com sucesso." : "Não foi possível enviar o ficheiro.", !!j.ok);
                    if (j.ok) {
                        setTimeout(function () {
                            window.location.reload();
                        }, 650);
                    }
                });
            });
        }
        load().catch(function () {
            toast($("cfg-toast"), "Não foi possível carregar as configurações. Confirme que tem sessão de administrador.", false);
        });
    });
})();
