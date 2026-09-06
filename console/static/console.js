/* NexFleet Console — interactions (vanilla JS) */
(function () {
  "use strict";

  function toast(msg, type) {
    const root = document.getElementById("toast-root");
    const el = document.createElement("div");
    el.className = "toast " + (type || "");
    el.textContent = msg;
    root.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .3s"; setTimeout(() => el.remove(), 320); }, 3200);
  }

  async function api(path, method, body) {
    const res = await fetch(path, {
      method: method || "GET",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch (_) {}
    if (res.status === 401) { location.href = "/login"; throw new Error("Non connecté."); }
    if (!res.ok) throw new Error((data && data.error) || "Erreur serveur.");
    return data;
  }

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k === "html") node.innerHTML = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    }
    (children || []).forEach((c) => { if (c != null) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return node;
  }

  function openModal(title, body, onSave, saveLabel) {
    const root = el("div", { class: "modal-root" });
    const card = el("div", { class: "modal-card glass" }, [
      el("h3", { text: title }),
      body,
      el("div", { class: "modal-actions" }, [
        el("button", { class: "btn btn-ghost", text: "Annuler", onclick: () => root.remove() }),
        el("button", { class: "btn btn-primary", id: "modal-save", text: saveLabel || "Enregistrer",
          onclick: async () => { try { await onSave(); root.remove(); } catch (e) { toast(e.message, "error"); } } }),
      ]),
    ]);
    root.append(el("div", { class: "modal-backdrop", onclick: () => root.remove() }), card);
    document.body.appendChild(root);
    return card;
  }

  function inputFor(col) {
    const name = col.name;
    const typeName = String(col.type || "").toUpperCase();
    let kind = "text";
    if (typeName.includes("INT")) kind = "number";
    else if (typeName.includes("REAL") || typeName.includes("FLOAT") || typeName.includes("DOUBLE")) kind = "number";
    const isPk = col.pk && /INT|pk/i.test(name + typeName);
    const wrap = el("div");
    if (isPk) {
      wrap.appendChild(el("small", { class: "hint", html: "<code>" + name + "</code> (clé primaire, auto)" }));
      return wrap;
    }
    wrap.appendChild(el("label", { text: name + (col.notnull ? " *" : "") }));
    const input = el("input", { type: kind, name: name, placeholder: col.dflt_value != null ? "défaut : " + col.dflt_value : "" });
    wrap.appendChild(input);
    return wrap;
  }

  function fieldValue(input) {
    if (input.type === "number") return input.value === "" ? null : Number(input.value);
    return input.value;
  }

  document.addEventListener("click", async (e) => {
    const target = e.target.closest("[data-console]");
    if (!target) return;

    if (target.dataset.console === "new-row") {
      const cols = JSON.parse(target.dataset.cols);
      const body = el("div", { class: "grid-2" });
      cols.forEach((c) => body.appendChild(inputFor(c)));
      openModal("Nouvelle ligne — " + target.dataset.table, body, async () => {
        const payload = {};
        cols.forEach((c) => {
          const input = body.querySelector(`[name="${c.name}"]`);
          if (input) payload[c.name] = fieldValue(input);
        });
        await api("/api/console/tables/" + target.dataset.table, "POST", payload);
        toast("Ligne créée.", "success");
        location.reload();
      }, "Créer");
    }

    if (target.dataset.console === "edit-row") {
      const cols = JSON.parse(target.dataset.cols);
      const row = JSON.parse(target.dataset.row);
      const body = el("div", { class: "grid-2" });
      cols.forEach((c) => {
        const wrap = inputFor(c);
        const input = wrap.querySelector("input");
        if (input && row[c.name] != null) input.value = String(row[c.name]);
        body.appendChild(wrap);
      });
      openModal("Modifier la ligne " + target.dataset.table, body, async () => {
        const payload = {};
        cols.forEach((c) => {
          const input = body.querySelector(`[name="${c.name}"]`);
          if (input) payload[c.name] = fieldValue(input);
        });
        await api("/api/console/tables/" + target.dataset.table + "/" + row.id, "PUT", payload);
        toast("Ligne modifiée.", "success");
        location.reload();
      }, "Enregistrer");
    }

    if (target.dataset.console === "del-row") {
      const table = target.dataset.table;
      const id = target.dataset.id;
      if (!confirm("Supprimer la ligne id=" + id + " de la table " + table + " ?")) return;
      try {
        await api("/api/console/tables/" + table + "/" + id, "DELETE");
        toast("Ligne supprimée.", "success");
        location.reload();
      } catch (err) { toast(err.message, "error"); }
    }

    if (target.dataset.console === "new-user") {
      const body = el("div", null, [
        el("label", { text: "Nom d'utilisateur *" }), el("input", { name: "username", required: true }),
        el("label", { text: "E-mail *" }), el("input", { name: "email", type: "email", required: true }),
        el("label", { text: "Mot de passe *" }), el("input", { name: "password", type: "password", required: true, minlength: "8" }),
        el("label", { text: "Rôle" }), (() => { const s = el("select", { name: "role" }); s.appendChild(el("option", { text: "user", value: "user" })); s.appendChild(el("option", { text: "admin", value: "admin" })); return s; })(),
      ]);
      openModal("Nouvel utilisateur NexFleet", body, async () => {
        const get = (n) => body.querySelector(`[name="${n}"]`).value;
        await api("/api/console/users", "POST", { username: get("username"), email: get("email"), password: get("password"), role: get("role") });
        toast("Utilisateur créé.", "success");
        location.reload();
      }, "Créer");
    }

    if (target.dataset.console === "edit-user") {
      const u = JSON.parse(target.dataset.user);
      const body = el("div", null, [
        el("label", { text: "Rôle" }), (() => { const s = el("select", { name: "role" }); ["user", "admin"].forEach((r) => { const o = el("option", { text: r, value: r }); o.selected = u.role === r; s.appendChild(o); }); return s; })(),
        el("label", { text: "Nouveau mot de passe (laisser vide pour conserver)" }), el("input", { name: "password", type: "password" }),
      ]);
      openModal("Modifier " + u.username, body, async () => {
        const payload = { role: body.querySelector('[name="role"]').value };
        const pw = body.querySelector('[name="password"]').value;
        if (pw) payload.password = pw;
        await api("/api/console/users/" + u.id, "PUT", payload);
        toast("Utilisateur mis à jour.", "success");
        location.reload();
      }, "Enregistrer");
    }

    if (target.dataset.console === "del-user") {
      const u = JSON.parse(target.dataset.user);
      if (!confirm("Supprimer l'utilisateur « " + u.username + " » ?")) return;
      try {
        await api("/api/console/users/" + u.id, "DELETE");
        toast("Utilisateur supprimé.", "success");
        location.reload();
      } catch (err) { toast(err.message, "error"); }
    }
  });

  const frmBootstrap = document.getElementById("frm-bootstrap");
  if (frmBootstrap) {
    frmBootstrap.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const data = Object.fromEntries(new FormData(frmBootstrap));
      try {
        await api("/api/console/bootstrap", "POST", data);
        location.href = "/";
      } catch (e) {
        toast(e.message, "error");
      }
    });
  }

  const sqlRun = document.getElementById("sql-run");
  if (sqlRun) {
    const input = document.getElementById("sql-input");
    const result = document.getElementById("sql-result");
    sqlRun.addEventListener("click", async () => {
      result.innerHTML = "";
      try {
        const res = await api("/api/console/sql", "POST", { sql: input.value });
        if (res.read_only) {
          const count = el("p", { class: "sql-ok", text: res.count + " ligne(s) renvoyée(s)." });
          result.appendChild(count);
          if (res.columns && res.columns.length) {
            const wrap = el("div", { class: "sql-result-wrap" });
            const table = el("table", { class: "data" });
            const thead = el("thead", null, [el("tr", null, res.columns.map((c) => el("th", { text: c })))]);
            const tbody = el("tbody");
            res.rows.forEach((r) => tbody.appendChild(el("tr", null, r.map((v) => el("td", { text: v == null ? "NULL" : String(v) })))));
            table.append(thead, tbody);
            wrap.appendChild(table);
            result.appendChild(wrap);
          }
        } else {
          result.appendChild(el("p", { class: "sql-ok", text: "Requête exécutée : " + res.affected + " ligne(s) affectée(s)." }));
        }
      } catch (e) {
        result.appendChild(el("p", { class: "sql-err", text: "Erreur : " + e.message }));
      }
    });
    const clearBtn = document.getElementById("sql-clear");
    if (clearBtn) clearBtn.addEventListener("click", () => { input.value = ""; result.innerHTML = ""; });
  }

  const backupBtn = document.getElementById("backup-now");
  const backupList = document.getElementById("backup-list");
  if (backupBtn && backupList) {
    const fmtSize = (b) => b >= 1024 * 1024 ? (b / 1024 / 1024).toFixed(2) + " Mo" : Math.round(b / 1024) + " Ko";
    const render = async () => {
      const res = await api("/api/console/backups");
      backupList.innerHTML = "";
      if (!res.backups.length) {
        backupList.appendChild(el("tr", null, [el("td", { colspan: "4" }, [el("div", { class: "empty" }, [el("div", { class: "empty-ico", text: "💾" }), el("p", { text: "Aucune sauvegarde pour le moment." })])])]));
        return;
      }
      res.backups.forEach((b) => {
        backupList.appendChild(el("tr", null, [
          el("td", { class: "td-strong", text: b.name }),
          el("td", { class: "td-mono", text: fmtSize(b.size) }),
          el("td", { class: "td-dim", text: new Date(b.date).toLocaleString("fr-FR") }),
          el("td", { style: "text-align:right" }, [el("a", { class: "btn btn-ghost btn-sm", href: "/api/console/backups/" + b.name + "/download", text: "Télécharger" })]),
        ]));
      });
    };
    render();
    backupBtn.addEventListener("click", async () => {
      backupBtn.disabled = true;
      try {
        const res = await api("/api/console/backup", "POST");
        toast("Sauvegarde créée : " + res.file, "success");
        render();
      } catch (e) { toast(e.message, "error"); }
      finally { backupBtn.disabled = false; }
    });
  }

  const rotateBtn = document.getElementById("rotate-secret");
  if (rotateBtn) {
    rotateBtn.addEventListener("click", async () => {
      if (!confirm("Régénérer la clé JWT NexFleet ? Toutes les sessions seront expirées.")) return;
      try {
        const res = await api("/api/console/secret/rotate");
        toast(res.note || "Clé régénérée.", "success");
      } catch (e) { toast(e.message, "error"); }
    });
  }
})();
