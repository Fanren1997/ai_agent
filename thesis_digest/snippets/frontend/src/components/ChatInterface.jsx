import React, { useEffect, useRef, useState } from "react";
import { RefreshCcw, SendHorizontal, PlusCircle, Copy, MoreHorizontal } from "lucide-react";
import {
  sendChatMessage,
  createSession,
  listSessions,
  getSessionMessages,
  updateSessionTitle,
  deleteSession,
  API_ORIGIN,
} from "../api";

export default function ChatInterface() {
  const linkRegex = /(https?:\/\/\S+|\/api\/download\/\S+)/g;

  const renderMessageContent = (text) => {
    if (!text) return null;
    const normalizedText = text.replace(/<br\s*\/?>/gi, "\n");
    const lines = normalizedText.split("\n");

    return lines.map((line, lineIdx) => {
      const parts = [];
      let lastIndex = 0;

      line.replace(linkRegex, (match, _p1, offset) => {
        if (offset > lastIndex) {
          parts.push(line.slice(lastIndex, offset));
        }
        const isDownload = match.includes("/api/download/");
        const href = isDownload && match.startsWith("/api/") ? `${API_ORIGIN}${match}` : match;
        const linkProps = isDownload
          ? { download: true, target: "_self" }
          : { target: "_blank", rel: "noopener noreferrer" };

        parts.push(
          <a key={`link-${lineIdx}-${offset}`} href={href} {...linkProps}>
            {match}
          </a>
        );
        lastIndex = offset + match.length;
        return match;
      });

      if (lastIndex < line.length) {
        parts.push(line.slice(lastIndex));
      }

      const isLastLine = lineIdx === lines.length - 1;
      return (
        <React.Fragment key={`line-${lineIdx}`}>
          {parts.length ? parts : line}
          {!isLastLine && <br />}
        </React.Fragment>
      );
    });
  };

  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [editingTitleId, setEditingTitleId] = useState(null);
  const [titleInput, setTitleInput] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionMenuIndex, setActionMenuIndex] = useState(null);
  const chatBoxRef = useRef(null);

  // 每次有新消息时滚动到底部
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (actionMenuIndex === null) return;
    const onDocClick = () => setActionMenuIndex(null);
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, [actionMenuIndex]);

  useEffect(() => {
    initSessions();
  }, []);

  async function initSessions() {
    setLoadingSessions(true);
    try {
      const data = await listSessions();
      setSessions(data);
      if (data.length) {
        selectSession(data[0].id);
      } else {
        await handleCreateSession();
      }
    } finally {
      setLoadingSessions(false);
    }
  }

  async function selectSession(sessionId) {
    setCurrentSessionId(sessionId);
    const history = await getSessionMessages(sessionId);
    const formatted = history.map((m) => ({
      sender: m.role === "assistant" ? "ai" : "user",
      text: m.content,
    }));
    setMessages(formatted);
  }

  async function handleCreateSession() {
    const data = await createSession("新对话");
    const newSessions = [{ id: data.sessionId, title: data.title }, ...sessions];
    setSessions(newSessions);
    await selectSession(data.sessionId);
  }

  function generateTitleFromText(text) {
    const clean = text.replace(/\s+/g, " ").replace(/[。！？!?,，]/g, " ").trim();
    if (!clean) return "新对话";
    return clean.slice(0, 20);
  }

  async function handleDeleteSession(sessionId) {
    await deleteSession(sessionId);
    const filtered = sessions.filter((s) => s.id !== sessionId);
    setSessions(filtered);
    if (currentSessionId === sessionId) {
      if (filtered.length) {
        await selectSession(filtered[0].id);
      } else {
        await handleCreateSession();
      }
    }
  }

  async function handleSend(customText) {
    const text = (customText ?? input).trim();
    if (!text) return;
    if (!currentSessionId) {
      await handleCreateSession();
    }

    const userMsg = { sender: "user", text };
    setMessages((prev) => [...prev, userMsg]);

    if (!customText) {
      setInput("");
    }

    setLoading(true);
    try {
      const reply = await sendChatMessage(text, currentSessionId);
      const downloadNote = reply.downloadUrl ? `\n下载链接: ${reply.downloadUrl}` : "";
      const aiText = (reply.message ?? reply.reply ?? String(reply)) + downloadNote;
      const aiMsg = { sender: "ai", text: aiText };
      setMessages((prev) => [...prev, aiMsg]);

      // 如果是新对话且标题还是默认值，自动根据问题生成标题
      const current = sessions.find((s) => s.id === currentSessionId);
      if (current && (!current.title || current.title === "新对话")) {
        const title = generateTitleFromText(text);
        try {
          await updateSessionTitle(currentSessionId, title);
          setSessions((prev) =>
            prev.map((s) => (s.id === currentSessionId ? { ...s, title } : s))
          );
        } catch (e) {
          console.warn("更新标题失败", e);
        }
      }
    } catch (err) {
      setMessages((prev) => [...prev, { sender: "ai", text: `⚠️ 网络错误：${err.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  function regenerate() {
    if (!messages.length) return;
    const lastUser = [...messages].reverse().find((m) => m.sender === "user");
    if (lastUser) {
      handleSend(lastUser.text);
    }
  }

  return (
    <div className="chat-layout">
      <aside className="chat-sidebar">
        <div className="sidebar-title">对话</div>
        <button className="sidebar-new" onClick={handleCreateSession} disabled={loadingSessions}>
          <PlusCircle size={16} />
          <span>新聊天</span>
        </button>
        <div className="sidebar-list">
          {sessions.map((s) => (
            <button
              key={s.id}
              className={`sidebar-item ${currentSessionId === s.id ? "active" : ""}`}
              onClick={() => selectSession(s.id)}
              title={s.title}
            >
              <div className="sidebar-item-main">
                {editingTitleId === s.id ? (
                  <input
                    value={titleInput}
                    onChange={(e) => setTitleInput(e.target.value)}
                    onBlur={async () => {
                      const newTitle = titleInput.trim() || "新对话";
                      await updateSessionTitle(s.id, newTitle);
                      setSessions((prev) => prev.map((x) => (x.id === s.id ? { ...x, title: newTitle } : x)));
                      setEditingTitleId(null);
                    }}
                    onKeyDown={async (e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        const newTitle = titleInput.trim() || "新对话";
                        await updateSessionTitle(s.id, newTitle);
                        setSessions((prev) =>
                          prev.map((x) => (x.id === s.id ? { ...x, title: newTitle } : x))
                        );
                        setEditingTitleId(null);
                      }
                    }}
                    autoFocus
                  />
                ) : (
                  <span onDoubleClick={() => { setEditingTitleId(s.id); setTitleInput(s.title || ""); }}>
                    {s.title || `对话 ${s.id}`}
                  </span>
                )}
                <span
                  className="delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteSession(s.id);
                  }}
                >
                  ×
                </span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <div className="chat-page">
        <div className="chat-window" ref={chatBoxRef}>
          {messages.map((m, idx) => {
            const prevUserText = [...messages]
              .slice(0, idx)
              .reverse()
              .find((x) => x.sender === "user")?.text;

            const onCopy = async () => {
              try {
                await navigator.clipboard.writeText(m.text || "");
              } catch (err) {
                console.warn("复制失败", err);
              }
            };

            const onRetry = () => {
              if (prevUserText) {
                handleSend(prevUserText);
              }
            };

            const handleMenuToggle = (event) => {
              event.stopPropagation();
              setActionMenuIndex((prev) => (prev === idx ? null : idx));
            };

            const handleMenuCopy = async () => {
              try {
                await navigator.clipboard.writeText(m.text || "");
              } catch (err) {
                console.warn("复制失败", err);
              } finally {
                setActionMenuIndex(null);
              }
            };

            const handleMenuDelete = () => {
              setMessages((prev) => prev.filter((_, i) => i !== idx));
              setActionMenuIndex(null);
            };

            const handleMenuRetry = () => {
              if (prevUserText) {
                handleSend(prevUserText);
              }
              setActionMenuIndex(null);
            };

            return (
              <div key={idx} className={`chat-message ${m.sender}`}>
                <div className="message-bubble">{renderMessageContent(m.text)}</div>
                {m.sender === "ai" && (
                  <div className="msg-actions-row">
                    <div className="msg-actions">
                      <button type="button" title="复制" onClick={onCopy}>
                        <Copy size={14} />
                      </button>
                      <button
                        type="button"
                        title="重试"
                        onClick={onRetry}
                        disabled={!prevUserText || loading}
                      >
                        <RefreshCcw size={14} />
                      </button>
                      <div className="msg-menu-wrapper">
                        <button type="button" title="更多" onClick={handleMenuToggle}>
                          <MoreHorizontal size={16} />
                        </button>
                        {actionMenuIndex === idx && (
                          <div
                            className="msg-menu"
                            onClick={(event) => event.stopPropagation()}
                          >
                            <button type="button" onClick={handleMenuCopy}>
                              复制
                            </button>
                            <button type="button" onClick={handleMenuRetry} disabled={!prevUserText || loading}>
                              重新提问
                            </button>
                            <button type="button" onClick={handleMenuDelete}>
                              删除消息
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="chat-message ai">
              <div className="message-bubble typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
        </div>

        <div className="chat-input">
          <input
            id="chat-input"
            name="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && handleSend()}
            placeholder="请输入查询问题，例如：查 P0048614 的 12NC..."
          />
          <button type="button" onClick={() => handleSend()} disabled={loading} aria-label="发送消息" title="发送消息">
            <SendHorizontal size={18} />
          </button>
        </div>

      </div>
    </div>
  );
}
