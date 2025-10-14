import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";
import api from "../api";

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "我们先从哪里开始呢？" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim()) return;
    const newMsgs = [...messages, { role: "user", content: input }];
    setMessages(newMsgs);
    setInput("");
    setLoading(true);

    try {
      const res = await api.chat(input);
      let replyText = "";

      if (res.error) replyText = `⚠️ 错误: ${res.error}`;
      else if (res.content) replyText = res.content;
      else replyText = JSON.stringify(res, null, 2);

      // 模拟打字机流式输出
      let i = 0;
      const streamMsg = { role: "assistant", content: "" };
      setMessages([...newMsgs, streamMsg]);

      const interval = setInterval(() => {
        if (i < replyText.length) {
          streamMsg.content += replyText[i++];
          setMessages([...newMsgs, { ...streamMsg }]);
        } else {
          clearInterval(interval);
          setLoading(false);
        }
      }, 15);
    } catch (err) {
      setMessages([...newMsgs, { role: "assistant", content: `⚠️ 网络错误: ${err.message}` }]);
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-box">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className={m.role === "user" ? "user-msg" : "ai-msg"}>
              <ReactMarkdown
                children={m.content}
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              />
            </div>
          </div>
        ))}
        <div ref={chatEndRef}></div>
      </div>

      <div className="input-area">
        <div className="input-box">
          <button className="add-btn">＋</button>
          <input
            placeholder="询问任何问题"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button className="mic-btn">🎤</button>
          <button className="send-btn" onClick={send} disabled={loading}>
            {loading ? "..." : "↑"}
          </button>
        </div>
        <div className="hint">Signify AI 可能会生成不准确的内容，请核实结果。</div>
      </div>
    </div>
  );
}
