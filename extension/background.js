chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "DGU_NDRIMS_ACTION") return;
  chrome.tabs.query({ active: true, lastFocusedWindow: true }, ([tab]) => {
    if (!tab?.id || !tab.url?.startsWith("https://ndrims.dongguk.edu/")) {
      sendResponse({ opened: false, reason: "nDRIMS 탭을 찾지 못했습니다." });
      return;
    }
    chrome.tabs.sendMessage(tab.id, message, (response) => {
      sendResponse(response ?? { opened: false, reason: "nDRIMS 화면과 연결되지 않았습니다." });
    });
  });
  return true;
});
