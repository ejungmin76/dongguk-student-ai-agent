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
  chrome.runtime.sendMessage({ type: "DGU_NDRIMS_REGISTER_TAB" });
  const normalize = (value) => value.replace(/\s+/g, "").toLowerCase();
  const findMenuRow = (title) => {
    const target = normalize(title);
    return [...document.querySelectorAll('[role="row"],[role="treeitem"]')]
      .find((element) => element instanceof HTMLElement && element.offsetParent
        && normalize(element.getAttribute("aria-label") || element.textContent || "") === target);
  };
  const activateMenuRow = (row) => {
    row.scrollIntoView({ block: "center" });
    row.focus?.();
    row.click();
  };
  async function openRegisteredMenu(label) {
    const path = label.split(">").map((part) => part.trim()).filter(Boolean);
    const title = path.at(-1);
    if (!title) return { opened: false, reason: "메뉴 경로가 비어 있습니다." };
    let row = findMenuRow(title);
    if (!row && path.length > 1) {
      const parent = findMenuRow(path[path.length - 2]);
      if (parent) {
        activateMenuRow(parent);
        await new Promise((resolve) => setTimeout(resolve, 350));
        row = findMenuRow(title);
      }
    }
    if (!row) return { opened: false, reason: `nDRIMS에서 '${title}' 메뉴를 찾지 못했습니다.` };
    activateMenuRow(row);
    return { opened: true, reason: `'${title}' 메뉴를 열었습니다.` };
  }
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "DGU_NDRIMS_ACTION") return;
    openRegisteredMenu(String(message.label || "")).then(sendResponse);
    return true;
  });
  shadow.append(style, button, panel); document.documentElement.appendChild(host);
})();
