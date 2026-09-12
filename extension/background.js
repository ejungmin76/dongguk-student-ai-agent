let ndrimsTabId = null;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "DGU_NDRIMS_REGISTER_TAB") {
    if (sender.tab?.id) ndrimsTabId = sender.tab.id;
    return;
  }
  if (message?.type !== "DGU_NDRIMS_ACTION") return;
  const sendToNdrims = (tabId) => chrome.tabs.sendMessage(tabId, message, (response) => {
    if (chrome.runtime.lastError) {
      ndrimsTabId = null;
      sendResponse({ opened: false, reason: "nDRIMS 화면과 연결이 끊겼습니다. 페이지를 새로고침해 주세요." });
      return;
    }
    sendResponse(response ?? { opened: false, reason: "nDRIMS 메뉴 응답을 받지 못했습니다." });
  });
  if (ndrimsTabId) {
    sendToNdrims(ndrimsTabId);
    return true;
  }
  chrome.tabs.query({ url: "https://ndrims.dongguk.edu/*" }, (tabs) => {
    const tab = tabs.find((item) => item.id);
    if (!tab?.id) {
      sendResponse({ opened: false, reason: "열려 있는 nDRIMS 탭을 찾지 못했습니다." });
      return;
    }
    ndrimsTabId = tab.id;
    sendToNdrims(tab.id);
  });
  return true;
});
