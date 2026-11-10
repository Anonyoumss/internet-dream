// Content script — exposes page text snippets for richer saves.
// Injected only on demand via scripting.executeScript in this design;
// kept as a file so it can also be declared in the manifest later.

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "get-page-text") {
    const text = document.body?.innerText?.slice(0, 8000) || "";
    sendResponse({ text, title: document.title, url: location.href });
  }
  return true;
});
