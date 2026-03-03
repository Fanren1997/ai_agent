import React, { useEffect, useState } from "react";
import ChatInterface from "./components/ChatInterface";
import api from "./api";
import "./style.css";

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const modelName = health?.details?.llm_model || "deepseek-chat";

  return (
    <div className="app">
      <header className="header">
        <div className="left">
          <span className="logo">Signify</span>
          <span className="dropdown">Access Agent</span>
        </div>
        <div className="right">
          已连接 <b>Access Agent</b> · 模型 <b>{modelName}</b>
        </div>
      </header>

      <main className="main">
        <ChatInterface />
      </main>
    </div>
  );
}
