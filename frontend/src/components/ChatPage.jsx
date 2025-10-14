import React, { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import "../style.css";

export default function ChatPage() {
  const [messages, setMessages] = useState([
    { role: "ai", content: "你好 👋 我是 Access Agent，可以帮你查询项目、12NC 或参数。" },
  ]);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);

  // 📨 发送消息
  const sendMessage = async () => {
    const question = userInput.trim();
    if (!question) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setUserInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:5000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question }),
      });
      const data = await res.json();

      const formatted = formatAiReply(data);
      setMessages((prev) => [...prev, formatted]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "⚠️ 网络错误，请检查后端是否在运行。" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // 🧠 美化 AI 回复
  const formatAiReply = (data) => {
    if (!data) return { role: "ai", content: "⚠️ 未返回任何结果。" };

    // 【情况 1】后端返回错误
    if (data.error) {
      return {
        role: "ai",
        content: `⚠️ <b>系统提示：</b>${data.error}`,
      };
    }

    // 【情况 2】项目 + 12NC 汇总
    if (data.summary && data.details) {
      let html = `<b>📊 查询结果如下：</b><br><br>`;
      data.summary.forEach((s) => {
        const code = s.Project_Code;
        const count = s["12NC数量"];
        const related = data.details
          .filter((d) => d.Project_Code === code)
          .map((d) => d["12NC"]);
        const preview = related.slice(0, 6).join("，");
        const more = related.length > 6 ? "…" : "";
        html += `🧩 <b>${code}</b> 含有 <b>${count}</b> 个 12NC，例如：${preview}${more}<br>`;
      });
      html += `<br>✅ 共 ${data.summary.length} 个项目。`;
      return { role: "ai", content: html };
    }

    // 【情况 3】普通字符串
    if (typeof data === "string") {
      return { role: "ai", content: data };
    }

    // 【情况 4】对象或数组，自动转成自然语言
    try {
      const pretty = JSON.stringify(data, null, 2)
        .replace(/^{|}$/g, "")
        .replace(/["{}]/g, "")
        .replace(/,/g, "<br>")
        .replace(/\n/g, "<br>");
      return { role: "ai", content: `🧠 <b>系统返回：</b><br>${pretty}` };
    } catch {
      return { role: "ai", content: JSON.stringify(data) };
    }
  };

  // ⌨️ 回车发送
  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  return (
    <div className="chat-page">
      <div className="chat-window">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role}`}>
            <div
              className="message-bubble"
              dangerouslySetInnerHTML={{ __html: msg.content }}
            ></div>
            {msg.chartData && (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={msg.chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="x" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="y"
                      stroke="#0078d7"
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        ))}

        {/* 打字动画 */}
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

      {/* 输入框 */}
      <div className="chat-input">
        <input
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="请输入你的问题，例如：查找 P0048614 的 12NC..."
        />
        <button onClick={sendMessage} disabled={loading}>
          {loading ? "思考中..." : "发送"}
        </button>
      </div>
    </div>
  );
}
