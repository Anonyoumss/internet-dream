const $ = (s) => document.querySelector(s);
const msg = (text, ok = true) => {
  const el = $("#msg");
  el.textContent = text;
  el.className = ok ? "ok" : "err";
};

function send(msgObj) {
  return new Promise((resolve) => chrome.runtime.sendMessage(msgObj, resolve));
}

async function refreshStatus() {
  const res = await send({ type: "ping" });
  const el = $("#status");
  if (res?.online) { el.textContent = "● dreamcore connected"; el.classList.remove("off"); }
  else { el.textContent = "○ offline — run `dream serve`"; el.classList.add("off"); }
  const cfg = await send({ type: "get-api" });
  $("#api-base").value = cfg?.apiBase || "";
}

$("#save-page").onclick = async () => {
  const res = await send({ type: "save-page", includeSelection: false });
  msg(res?.error ? `failed: ${res.error}` : "page saved ✓", !res?.error);
};

$("#save-page-note").onclick = async () => {
  const note = prompt("Note to attach:");
  if (note === null) return;
  const res = await send({ type: "save-page", includeSelection: false, note });
  msg(res?.error ? `failed: ${res.error}` : "page saved ✓", !res?.error);
};

$("#save-selection").onclick = async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  const res = await send({ type: "save-page", includeSelection: true });
  msg(res?.error ? `failed: ${res.error}` : "page + selection saved ✓", !res?.error);
};

$("#save-api").onclick = async () => {
  const res = await send({ type: "set-api", apiBase: $("#api-base").value.trim() });
  msg(res?.ok ? "saved" : "failed", res?.ok);
  refreshStatus();
};

$("#search-q").addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  const q = e.target.value.trim();
  if (!q) return;
  const cfg = await send({ type: "get-api" });
  const base = (cfg?.apiBase || "http://127.0.0.1:8765").replace(/\/$/, "");
  try {
    const r = await fetch(`${base}/search?q=${encodeURIComponent(q)}&limit=5`);
    const hits = await r.json();
    $("#results").innerHTML = hits.length
      ? hits.map((h) => `<div style="margin-bottom:8px"><b>${h.title}</b><br>
          <span style="opacity:.7">${h.sender || ""} · ${(h.snippet || "").slice(0, 120)}</span></div>`).join("")
      : "<i>no results</i>";
  } catch {
    $("#results").innerHTML = "<i>backend offline</i>";
  }
});

refreshStatus();
