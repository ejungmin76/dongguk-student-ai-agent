let ndrimsTabId = null;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "DGU_NDRIMS_REGISTER_TAB") {
    if (sender.tab?.id) ndrimsTabId = sender.tab.id;
    return;
  }
  if (message?.type !== "DGU_NDRIMS_ACTION") return;
  if (!ndrimsTabId) {
    sendResponse({ opened: false, reason: "nDRIMS 화면과 아직 연결되지 않았습니다. 페이지를 새로고침해 주세요." });
    return;
  }
  chrome.tabs.sendMessage(ndrimsTabId, message, (response) => {
    if (chrome.runtime.lastError) {
      ndrimsTabId = null;
      sendResponse({ opened: false, reason: "nDRIMS 화면과 연결이 끊겼습니다. 페이지를 새로고침해 주세요." });
      return;
    }
    sendResponse(response ?? { opened: false, reason: "nDRIMS 메뉴 응답을 받지 못했습니다." });
  });
  return true;
});
