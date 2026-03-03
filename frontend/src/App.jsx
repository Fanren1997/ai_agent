import React, { useEffect, useMemo, useState } from "react";
import ChatInterface from "./components/ChatInterface";
import api from "./api";
import "./style.css";

export default function App() {
  const [health, setHealth] = useState(null);
  const [page, setPage] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("page") || "home";
  });

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    const onPopState = () => {
      const params = new URLSearchParams(window.location.search);
      setPage(params.get("page") || "home");
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const modelName = health?.details?.llm_model || "deepseek-chat";
  const adminUrl = useMemo(
    () =>
      import.meta.env.VITE_ADMIN_URL ||
      "http://127.0.0.1:5000/static/schema_manager.html",
    []
  );

  const navigate = (nextPage) => {
    const url = nextPage === "home" ? "/" : `/?page=${nextPage}`;
    window.history.pushState({}, "", url);
    setPage(nextPage);
  };

  if (page === "home") {
    return (
      <div className="home">
        <div className="home-bg" aria-hidden="true" />
        <header className="home-header">
          <div className="home-brand">Signify Access</div>
        </header>

        <main className="home-hero">
          <div className="home-hero-text">
            <p className="home-eyebrow">Access 智能中枢</p>
            <h1>从这里进入你的 AI 工作台</h1>
            <p className="home-subtitle">
              选择 Agent 对话或进入后台管理，开启数据协作与流程自动化。
            </p>
            <div className="home-actions">
              <button
                className="home-btn primary"
                onClick={() => navigate("agent")}
              >
                Agent 对话
              </button>
              <button
                className="home-btn ghost"
                onClick={() => window.open(adminUrl, "_blank", "noopener")}
              >
                Admin 后台
              </button>
            </div>
          </div>

          <div className="home-hero-card">
            <div className="home-card-header">
              <span>状态预览</span>
              <span className="home-status">
                {health ? "系统在线" : "连接中"}
              </span>
            </div>
            <div className="home-card-body">
              <div>
                <p className="home-card-label">模型</p>
                <p className="home-card-value">{modelName}</p>
              </div>
              <div>
                <p className="home-card-label">环境</p>
                <p className="home-card-value">本地服务 · 5000</p>
              </div>
              <div>
                <p className="home-card-label">数据源</p>
                <p className="home-card-value">Access / MySQL</p>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <div className="left">
          <button className="back-btn" onClick={() => navigate("home")}>
            返回主页
          </button>
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
