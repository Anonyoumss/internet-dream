// Internet's Dream extension — background service worker.
// Saves page/selection metadata to `dreamcore serve` (default :8765).
// All data stays local; the only network call is to your own backend.

const DEFAULT_API = "http://127.0.0.1:8765";

async function getApiBase() {
  const { apiBase } = await chrome.storage.sync.get("apiBase");
  return (apiBase || DEFAULT_API).replace(/\/$/, "");
}

async function postMemory(doc) {
  const base = await getApiBase();
  const r = await fetch(`${base}/ingest-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(doc),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

// Save current page (title + url + optional selection) — used by popup
// and the right-click context menu.
async function savePage(opts = {}) {
  const tab = await getActiveTab();
  if (!tab?.id || !tab.url || tab.url.startsWith("chrome")) {
    throw new Error("can't save browser-internal pages");
  }
  let selection = "";
  if (opts.includeSelection !== false) {
    try {
      const [res] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => window.getSelection()?.toString() || "",
      });
      selection = res?.result || "";
    } catch { /* cross-origin / restricted page — skip selection */ }
  }
  const text = [
    `URL: ${tab.url}`,
    `Title: ${tab.title || ""}`,
    selection ? `Selected text:\n${selection}` : "",
    opts.note ? `Note: ${opts.note}` : "",
  ].filter(Boolean).join("\n");
  return postMemory({
    source: "browser-extension",
    kind: "page",
    title: `🌐 ${tab.title || tab.url}`.slice(0, 200),
    text,
    sender: "you",
    chat: "browser",
    ts: Date.now() / 1000,
  });
}

// Context menus
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "dream-save-page", title: "Save page to Internet's Dream",
    contexts: ["page"],
  });
  chrome.contextMenus.create({
    id: "dream-save-selection", title: "Save selection to Internet's Dream",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  try {
    if (info.menuItemId === "dream-save-page") {
      await savePage({ includeSelection: false });
    } else if (info.menuItemId === "dream-save-selection") {
      const base = await getApiBase();
      const r = await fetch(`${base}/ingest-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: "browser-extension", kind: "selection",
          title: `📝 selection from ${tab.title || tab.url}`.slice(0, 200),
          text: `URL: ${tab.url}\nTitle: ${tab.title || ""}\n\n${info.selectionText}`,
          sender: "you", chat: "browser", ts: Date.now() / 1000,
        }),
      });
      if (!r.ok) throw new Error(`${r.status}`);
    }
  } catch (e) {
    console.error("dream save failed:", e);
  }
});

// Messages from popup
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    try {
      if (msg.type === "save-page") sendResponse(await savePage(msg));
      else if (msg.type === "get-api") {
        sendResponse({ apiBase: await getApiBase() });
      } else if (msg.type === "set-api") {
        await chrome.storage.sync.set({ apiBase: msg.apiBase });
        sendResponse({ ok: true });
      } else if (msg.type === "ping") {
        const base = await getApiBase();
        const r = await fetch(`${base}/health`, { signal: AbortSignal.timeout(2000) });
        sendResponse({ online: r.ok });
      } else {
        sendResponse({ error: "unknown message" });
      }
    } catch (e) {
      sendResponse({ error: String(e) });
    }
  })();
  return true; // async response
});
