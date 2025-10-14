import React, { useEffect, useState } from "react";
import ChatPage from "./components/ChatPage";
import api from "./api";

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div className="left">
          <span className="logo">Signify</span>
          <span className="dropdown">▼</span>
        </div>
        <div className="right">
          已连接 <b>Access Agent</b> • 模型{" "}
          <b>{health?.details?.model || "deepseek-chat"}</b>
        </div>
      </header>

      <main className="main">
        <ChatPage />
      </main>
    </div>
  );
}
