(() => {
  if (window.top !== window || document.getElementById("dgu-ai-extension-host")) return;

  const host = document.createElement("div");
  host.id = "dgu-ai-extension-host";
  const shadow = host.attachShadow({ mode: "closed" });
  const style = document.createElement("style");
  style.textContent = `
    :host { all: initial; }
    .fab { position: fixed; right: 24px; bottom: 24px; z-index: 2147483647; width: 58px; height: 58px; border: 0; border-radius: 50%; background: #1428a0; color: white; font: 700 22px Arial; cursor: pointer; box-shadow: 0 8px 24px #0004; }
    .panel { display: none; position: fixed; right: 24px; bottom: 92px; z-index: 2147483647; width: 450px; height: 680px; border: 0; border-radius: 24px; background: white; box-shadow: 0 18px 55px #0005; overflow: hidden; }
    .panel.open { display: block; }
    @media (max-width: 560px) { .panel { right: 10px; bottom: 80px; width: calc(100vw - 20px); height: calc(100vh - 100px); } .fab { right: 14px; bottom: 14px; } }
  `;
  const button = document.createElement("button");
  button.className = "fab"; button.type = "button"; button.title = "동국대 AI Assistant"; button.textContent = "✦";
  const panel = document.createElement("iframe");
  panel.className = "panel"; panel.title = "동국대 AI Assistant"; panel.src = chrome.runtime.getURL("panel.html");
  button.addEventListener("click", () => panel.classList.toggle("open"));
  function openRegisteredMenu(label) {
    const title = label.split(" > ").filter(Boolean).pop();
    if (!title) return false;
    const normalize = (value) => value.replace(/\s+/g, "").toLowerCase();
    const target = normalize(title);
    const candidates = [...document.querySelectorAll("button,a,[role=row],[role=treeitem],[role=button],li,[aria-label],[title]")]
      .filter((element) => element instanceof HTMLElement && element.offsetParent && element !== host)
      .filter((element) => [element.textContent, element.getAttribute("aria-label"), element.getAttribute("title")]
        .some((value) => normalize(value || "") === target));
    const clickable = candidates.find((element) => element.matches("[role=row],[role=treeitem],button,a,[role=button],li")) || candidates[0];
    if (clickable) { clickable.scrollIntoView({ block: "center" }); clickable.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true })); }
    return Boolean(clickable);
  }
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "DGU_NDRIMS_ACTION") return;
    sendResponse({ opened: openRegisteredMenu(String(message.label || "")) });
  });
  shadow.append(style, button, panel); document.documentElement.appendChild(host);
})();
