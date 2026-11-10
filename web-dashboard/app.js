/* Internet's Dream dashboard — hash-routed SPA.
   Live mode talks to `dreamcore serve` (default http://127.0.0.1:8765);
   demo mode uses window.DEMO so the site works fully on GitHub Pages. */

(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const view = $("#view");

  const state = {
    apiBase: localStorage.getItem("dream.apiBase") || "http://127.0.0.1:8765",
    live: false,
    theme: localStorage.getItem("dream.theme") || "light",
  };

  // ---------- theme ----------
  function applyTheme() {
    document.documentElement.dataset.theme = state.theme;
    localStorage.setItem("dream.theme", state.theme);
  }
  $("#theme-toggle").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    applyTheme();
  });
  applyTheme();

  // ---------- api ----------
  async function api(path, opts = {}) {
    const r = await fetch(state.apiBase + path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  }

  async function detectLive() {
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 1500);
      const r = await fetch(state.apiBase + "/health", { signal: ctl.signal });
      clearTimeout(t);
      state.live = r.ok;
    } catch {
      state.live = false;
    }
    const badge = $("#mode-badge");
    badge.textContent = state.live ? "live · dreamcore" : "demo mode";
    badge.classList.toggle("live", state.live);
  }

  // ---------- helpers ----------
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtTs = (ts) => {
    if (!ts) return "";
    const d = new Date(typeof ts === "number" && ts < 1e12 ? ts * 1000 : ts);
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
      " · " + d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  };
  const initials = (s) => (s || "?").split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const avatarColor = (s) => {
    let h = 0; for (const c of s || "") h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return `hsl(${h % 360} 45% 45%)`;
  };

  function memCard(m) {
    const ts = m.ts ? fmtTs(m.ts) : "";
    return `<div class="mem">
      <div class="avatar" style="background:${avatarColor(m.sender || m.title)}22;color:${avatarColor(m.sender || m.title)}">${esc(initials(m.sender || m.title))}</div>
      <div style="min-width:0">
        <div class="meta">${esc(m.title)} · ${esc(m.sender || "unknown")} · ${ts} <span class="source-chip">${esc(m.source)}</span></div>
        <div class="title"></div>
        <div class="text">${esc(m.text || m.snippet || "")}</div>
      </div>
    </div>`;
  }

  function demoSearch(q, limit = 20) {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    return window.DEMO.memories
      .map((m) => {
        const hay = `${m.title} ${m.sender} ${m.chat} ${m.text}`.toLowerCase();
        const score = terms.reduce((s, t) => s + (hay.includes(t) ? 1 : 0), 0);
        return { m, score };
      })
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
      .map((x) => ({ ...x.m, score: x.score / terms.length }));
  }

  // ---------- views ----------
  function renderDashboard() {
    view.innerHTML = `
      <h1>Dashboard</h1>
      <p class="sub">Your digital life, indexed locally. Everything below never leaves this device unless you configure an LLM provider.</p>
      <div class="grid cols-4" id="stat-grid"></div>
      <div class="grid cols-2" style="margin-top:24px">
        <div class="card"><h3>Recent memories</h3><div id="recent"></div></div>
        <div class="card"><h3>Memory graph</h3>
          <p class="sub" style="margin:0">Chats and people connected by shared memories.</p>
          <a class="btn tonal" href="#/graph">Open graph</a>
        </div>
      </div>`;
    loadStats();
    loadRecent();
  }

  async function loadStats() {
    const grid = $("#stat-grid");
    try {
      const s = state.live ? await api("/stats") : {
        total: window.DEMO.stats.total,
        by_source: Object.fromEntries(Object.entries(window.DEMO.stats.bySource).map(([k, v]) => [k, v])),
      };
      const sources = Object.entries(s.by_source || {});
      grid.innerHTML = `
        <div class="card"><h3>Memories</h3><div class="stat">${s.total.toLocaleString()}</div>
        <div class="stat-sub">encrypted at rest · AES-256-GCM</div></div>
        ${sources.slice(0, 3).map(([k, v]) => `
          <div class="card"><h3>${esc(k)}</h3><div class="stat">${v.toLocaleString()}</div>
          <div class="stat-sub">indexed documents</div></div>`).join("")}`;
    } catch {
      grid.innerHTML = `<div class="card"><h3>Offline</h3><p class="sub">Start <code>dream serve</code> to go live.</p></div>`;
    }
  }

  async function loadRecent() {
    const el = $("#recent");
    if (state.live) {
      const hits = await api("/search?q=" + encodeURIComponent("the"));
      el.innerHTML = hits.slice(0, 5).map(memCard).join("") || "<p class='sub'>No memories yet — ingest a chat export.</p>";
    } else {
      el.innerHTML = window.DEMO.memories.slice(0, 5).map(memCard).join("");
    }
  }

  function renderSearch() {
    view.innerHTML = `
      <h1>Search memories</h1>
      <p class="sub">Hybrid keyword + semantic search across everything you've indexed.</p>
      <div class="ask-box">
        <input id="q" type="search" placeholder="e.g. restaurant recommendation last month…" autofocus>
        <button class="btn" id="go">Search</button>
      </div>
      <div id="results"></div>`;
    const run = async () => {
      const q = $("#q").value.trim();
      if (!q) return;
      const out = $("#results");
      out.innerHTML = `<p class="sub">Searching…</p>`;
      try {
        const hits = state.live
          ? await api("/search?q=" + encodeURIComponent(q))
          : demoSearch(q);
        out.innerHTML = hits.length
          ? hits.map((h) => memCard(state.live ? { ...h, text: h.snippet } : h)).join("")
          : `<div class="card"><p class="sub">No memories matched. Try different words, or ingest more sources.</p></div>`;
      } catch (e) {
        out.innerHTML = `<div class="card"><p class="sub">Search failed: ${esc(e.message)}. Is <code>dream serve</code> running?</p></div>`;
      }
    };
    $("#go").addEventListener("click", run);
    $("#q").addEventListener("keydown", (e) => e.key === "Enter" && run());
  }

  function renderAsk() {
    view.innerHTML = `
      <h1>Ask your second brain</h1>
      <p class="sub">Answers are grounded in your indexed memories and cite their sources.</p>
      <div class="ask-box">
        <input id="question" type="text" placeholder="What was that restaurant my friend recommended?" autofocus>
        <button class="btn" id="ask-go">Ask</button>
      </div>
      <div id="answer"></div>`;
    const run = async () => {
      const q = $("#question").value.trim();
      if (!q) return;
      const out = $("#answer");
      out.innerHTML = `<div class="answer">Thinking…</div>`;
      if (state.live) {
        try {
          const r = await api("/ask", { method: "POST", body: JSON.stringify({ question: q }) });
          out.innerHTML = `<div class="answer">${esc(r.answer)}</div>
            <div class="sources"><h3>Sources</h3>${(r.sources || []).map((h) => memCard({ ...h, text: h.snippet })).join("")}</div>`;
        } catch (e) {
          out.innerHTML = `<div class="answer">Ask failed: ${esc(e.message)}</div>`;
        }
      } else {
        // demo answer composed from matching memories — no fake LLM claims
        const hits = demoSearch(q, 3);
        if (!hits.length) {
          out.innerHTML = `<div class="answer">I don't have anything indexed about that yet. In live mode, the LLM gateway answers from your memories with citations.</div>`;
        } else {
          const bullets = hits.map((h) =>
            `• ${h.sender || "?"} in ${h.chat || h.title}: "${(h.text || "").slice(0, 140)}…"`).join("\n");
          out.innerHTML = `<div class="answer">Demo mode — no LLM configured. The closest memories I found:\n\n${esc(bullets)}\n\nConnect <code>dream serve</code> and set an API key in Settings to get real generated answers.</div>
            <div class="sources"><h3>Sources</h3>${hits.map(memCard).join("")}</div>`;
        }
      }
    };
    $("#ask-go").addEventListener("click", run);
    $("#question").addEventListener("keydown", (e) => e.key === "Enter" && run());
  }

  function renderGraph() {
    view.innerHTML = `
      <h1>Memory graph</h1>
      <p class="sub">Chats (outer ring) connected to people (inner) by shared memories.</p>
      <canvas id="graph-canvas"></canvas>
      <div class="legend">
        <span><i style="background:var(--md-sys-color-primary)"></i>chat / channel</span>
        <span><i style="background:var(--md-sys-color-tertiary-container);border:1px solid var(--md-sys-color-outline)"></i>person</span>
      </div>`;
    drawGraph();
  }

  function drawGraph() {
    const canvas = $("#graph-canvas");
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth, H = canvas.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.scale(dpr, dpr);

    const data = state.live ? null : window.DEMO.graph;
    const nodes = [], edges = [];
    if (state.live) {
      api("/graph").then((g) => { animate(g.nodes, g.edges); }).catch(() => animate([], []));
    } else {
      animate(data.nodes, data.edges);
    }

    function animate(nodeData, edgeData) {
      if (!nodeData.length) {
        ctx.fillStyle = getComputedStyle(document.documentElement)
          .getPropertyValue("--md-sys-color-on-surface-variant");
        ctx.font = "14px sans-serif"; ctx.fillText("No graph data — ingest memories first.", 24, 40);
        return;
      }
      const cx = W / 2, cy = H / 2;
      const chats = nodeData.filter((n) => n.group === 1);
      const people = nodeData.filter((n) => n.group === 2);
      nodeData.forEach((n, i) => {
        const isChat = n.group === 1;
        const list = isChat ? chats : people;
        const idx = list.indexOf(n);
        const radius = isChat ? Math.min(W, H) * 0.36 : Math.min(W, H) * 0.2;
        const count = list.length;
        const ang = (idx / Math.max(count, 1)) * Math.PI * 2 - Math.PI / 2;
        nodes.push({ ...n, x: cx + Math.cos(ang) * radius * (isChat ? 1 : 0.62),
                     y: cy + Math.sin(ang) * radius * (isChat ? 1 : 0.62), vx: 0, vy: 0 });
      });
      edges.push(...edgeData);
      const primary = getComputedStyle(document.documentElement).getPropertyValue("--md-sys-color-primary").trim();
      const tertiary = getComputedStyle(document.documentElement).getPropertyValue("--md-sys-color-tertiary-container").trim();
      const onSurf = getComputedStyle(document.documentElement).getPropertyValue("--md-sys-color-on-surface").trim();
      const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));

      let t = 0;
      (function frame() {
        t += 0.008;
        ctx.clearRect(0, 0, W, H);
        // gentle drift
        nodes.forEach((n) => {
          n.x += Math.cos(t + n.y * 0.01) * 0.15;
          n.y += Math.sin(t * 1.3 + n.x * 0.01) * 0.15;
        });
        ctx.strokeStyle = primary; ctx.globalAlpha = 0.25; ctx.lineWidth = 1;
        edges.forEach((e) => {
          const a = byId[e.source], b = byId[e.target];
          if (!a || !b) return;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        });
        ctx.globalAlpha = 1;
        nodes.forEach((n) => {
          const r = n.group === 1 ? 7 : 5;
          ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
          ctx.fillStyle = n.group === 1 ? primary : tertiary;
          ctx.fill();
          ctx.strokeStyle = onSurf; ctx.globalAlpha = 0.4; ctx.stroke(); ctx.globalAlpha = 1;
          ctx.fillStyle = onSurf; ctx.font = "11px sans-serif"; ctx.textAlign = "center";
          ctx.fillText(n.id.length > 16 ? n.id.slice(0, 15) + "…" : n.id, n.x, n.y - r - 5);
        });
        requestAnimationFrame(frame);
      })();
    }
  }

  function renderSettings() {
    const apiBase = state.apiBase;
    view.innerHTML = `
      <h1>Settings</h1>
      <p class="sub">Connection and privacy controls. Keys are stored only in this browser's localStorage — never sent anywhere except your configured endpoints.</p>
      <div class="settings-grid">
        <div class="card">
          <h3>dreamcore API</h3>
          <div class="field"><label>API base URL</label>
            <input id="api-base" value="${esc(apiBase)}" placeholder="http://127.0.0.1:8765"></div>
          <button class="btn tonal" id="save-api">Save & reconnect</button>
          <span id="conn-status" class="stat-sub" style="margin-left:12px"></span>
        </div>
        <div class="card">
          <h3>LLM provider</h3>
          <p class="sub" style="margin-top:0">Ask-mode generation is configured on the <code>dreamcore</code> backend, not here:</p>
          <pre class="answer" style="font-size:13px">dream config --provider openai-compatible \\
  --base-url https://api.openai.com/v1 \\
  --api-key sk-... --model gpt-4o-mini

# or Anthropic:
dream config --provider anthropic --model claude-sonnet-4-5

# or local Ollama:
dream config --provider openai-compatible \\
  --base-url http://localhost:11434/v1 --model llama3.1</pre>
        </div>
        <div class="card">
          <h3>Privacy</h3>
          <p class="sub" style="margin-top:0">• All memories are AES-256-GCM encrypted at rest.<br>
          • Search index stores metadata only (sender, chat, date).<br>
          • Zero telemetry. The dashboard makes requests only to your API base URL.<br>
          • Demo mode uses a bundled sample dataset — no data leaves your browser.</p>
        </div>
      </div>`;
    $("#save-api").addEventListener("click", async () => {
      state.apiBase = $("#api-base").value.trim().replace(/\/$/, "") || "http://127.0.0.1:8765";
      localStorage.setItem("dream.apiBase", state.apiBase);
      const st = $("#conn-status");
      st.textContent = "checking…";
      await detectLive();
      st.textContent = state.live ? "connected ✓" : "unreachable — demo mode";
      route();
    });
  }

  // ---------- router ----------
  const routes = { dashboard: renderDashboard, search: renderSearch, ask: renderAsk, graph: renderGraph, settings: renderSettings };
  function route() {
    const name = (location.hash.replace("#/", "") || "dashboard").split("?")[0];
    document.querySelectorAll(".rail-item").forEach((a) =>
      a.classList.toggle("active", a.dataset.route === name));
    (routes[name] || renderDashboard)();
    view.focus();
  }
  window.addEventListener("hashchange", route);

  detectLive().then(route);
})();
