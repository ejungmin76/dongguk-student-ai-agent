"use client";

import { FormEvent, useEffect, useState } from "react";

type Detail = { label: string; url?: string; action?: { actionId: string; path: string } };
type Message = { role: "user" | "assistant"; text: string; details?: Detail[] };

export default function ChatWidget({ autoOpen = false, extensionMode = false }: { autoOpen?: boolean; extensionMode?: boolean }) {
  const [open, setOpen] = useState(autoOpen); const [text, setText] = useState("");
  const [messages, setMessages] = useState<Message[]>([]); const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(""); const [error, setError] = useState(""); const [menuStatus, setMenuStatus] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  useEffect(() => {
    const receive = (event: MessageEvent) => {
      if (event.data?.type === "DGU_NDRIMS_ACTION_RESULT") setMenuStatus(event.data.reason || (event.data.opened ? "nDRIMS 메뉴를 열었습니다." : "현재 화면에서 메뉴를 찾지 못했습니다."));
    };
    window.addEventListener("message", receive); return () => window.removeEventListener("message", receive);
  }, []);

  async function submit(event?: FormEvent, suggested?: string) {
    event?.preventDefault(); const question = (suggested ?? text).trim(); if (!question || busy) return;
    setText(""); setError(""); setBusy(true); setStatus("답변을 준비하고 있어요…");
    setMessages(current => [...current, {role:"user", text:question}, {role:"assistant", text:""}]);
    try {
      let headers: Record<string,string> = {"Content-Type":"application/json"};
      if (extensionMode) {
        const key = "dgu-extension-session";
        const extensionSession = localStorage.getItem(key) ?? crypto.randomUUID();
        localStorage.setItem(key, extensionSession); headers["X-DGU-Extension-Session"] = extensionSession;
      } else {
        const csrfResponse = await fetch("/api/csrf/", {cache:"no-store", credentials:"include"});
        if (!csrfResponse.ok) throw new Error(await readableError(csrfResponse, "Django API에 연결할 수 없습니다."));
        const csrf = await csrfResponse.json(); headers["X-CSRFToken"] = csrf.csrf_token;
      }
      const response = await fetch(extensionMode ? "/api/chat/stream/extension/" : "/api/chat/stream/", {method:"POST", credentials:"include", headers, body:JSON.stringify({message:question, session_id:sessionId})});
      if (!response.ok || !response.body) throw new Error(await readableError(response, "요청을 처리하지 못했습니다."));
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      while (true) { const {value, done} = await reader.read(); if (done) break; buffer += decoder.decode(value, {stream:true}); const end = buffer.lastIndexOf("\n\n"); if (end < 0) continue; const blocks = buffer.slice(0,end).split("\n\n"); buffer = buffer.slice(end+2); blocks.forEach(block => handleEvent(block)); }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "연결이 끊겼습니다."); }
    finally { setBusy(false); setStatus(""); }
  }
  async function readableError(response: Response, fallback: string) {
    const body = await response.text();
    try { return JSON.parse(body).error?.message ?? fallback; }
    catch { return fallback; }
  }
  function handleEvent(block: string) {
    const item: Record<string,string> = {}; block.split("\n").forEach(line => { const index=line.indexOf(":"); if(index>0) item[line.slice(0,index)] = line.slice(index+1).trim(); }); const data = item.data ? JSON.parse(item.data) : {};
    if (item.event === "session") setSessionId(data.session_id);
    if (item.event === "progress") setStatus("답변을 준비하고 있어요…");
    if (item.event === "answer") setMessages(current => current.map((message,index) => index===current.length-1 ? {...message,text:data.text} : message));
    if (item.event === "source" || item.event === "action") {
      const action = item.event === "action" && data.action_type === "navigate_ndrims_menu"
        ? { actionId: data.action_id, path: data.label } : undefined;
      setMessages(current => current.map((message,index) => index===current.length-1 ? {...message,details:[...(message.details ?? []), {label:`${item.event === "source" ? "출처" : "서비스"}: ${data.title ?? data.label}`, url:item.event === "action" ? data.url : undefined, action}]} : message));
    }
    if (item.event === "complete" && data.limitations?.length) setMessages(current => current.map((message,index) => index===current.length-1 ? {...message,details:[...(message.details ?? []), ...data.limitations.map((label:string) => ({label}))]} : message));
    if (item.event === "error") setError(data.message ?? "답변을 준비하지 못했습니다.");
  }
  const openNdrimsAction = (action: { actionId: string; path: string }) => { setMenuStatus("nDRIMS 메뉴를 여는 중…"); window.parent.postMessage({ type: "DGU_NDRIMS_ACTION", action_id: action.actionId, label: action.path }, "*"); };
  return <><button className="chat-fab" onClick={() => setOpen(true)} aria-label="AI Assistant 열기">✦</button>{open && <div className="widget"><header><div className="agent-mark">D</div><div><strong>동국대 AI Assistant</strong><small>공식 정보 기반 안내</small></div><button onClick={() => setOpen(false)} aria-label="닫기">×</button></header><div className="conversation">{messages.length===0 && <div className="welcome"><h2>무엇을 도와드릴까요?</h2><p>학사 안내와 nDRIMS 메뉴를 빠르게 찾아드릴게요.</p><button onClick={() => submit(undefined,"최대 수강학점이 몇 학점이야?")}>최대 수강학점</button><button onClick={() => submit(undefined,"기숙사 신청 메뉴를 찾아줘")}>기숙사 신청</button></div>}{messages.map((message,index) => <article className={`message ${message.role}`} key={index}><p>{message.text || (busy ? "답변을 작성하고 있어요…" : "")}</p>{message.details?.map((detail,i)=><small key={i}>{detail.action ? <button className="ndrims-action" onClick={() => openNdrimsAction(detail.action!)}>바로가기 열기 · {detail.action.path}</button> : detail.url ? <a href={detail.url} target="_blank" rel="noreferrer">{detail.label}</a> : detail.label}</small>)}</article>)}</div>{status && <div className="stream-status">● {status}</div>}{error && <div className="widget-error">{error}<button onClick={() => submit(undefined, messages.filter(m=>m.role==="user").at(-1)?.text)}>다시 시도</button></div>}<form onSubmit={submit}><textarea value={text} onChange={e=>setText(e.target.value)} placeholder="질문을 입력하세요" maxLength={2000} rows={1}/><button disabled={!text.trim() || busy} aria-label="보내기">↑</button></form><footer>AI 답변은 공식 출처를 확인해 주세요.</footer></div>}</>;
}
