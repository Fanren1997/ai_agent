import React, { useState } from "react";
import api from "../api";
import DataTable from "./DataTable";

export default function QueryInterface() {
  const [schema, setSchema] = useState(
    "CREATE TABLE users (id INT, name VARCHAR(50), created_at DATETIME);"
  );
  const [question, setQuestion] = useState("查询所有用户姓名");
  const [sql, setSql] = useState("");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const res = await api.nl2sql(schema, question);
      setSql(res.sql);
      const exec = await api.query(res.sql);
      setRows(exec.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="query-box">
      <h3>🧮 自然语言 → SQL 查询</h3>
      <textarea
        rows={5}
        value={schema}
        onChange={(e) => setSchema(e.target.value)}
      />
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="输入问题，例如：查最近注册的10个用户"
      />
      <button onClick={run} disabled={loading}>
        {loading ? "执行中..." : "生成并执行"}
      </button>
      {sql && <pre className="sql-block">{sql}</pre>}
      <DataTable data={rows} />
    </div>
  );
}
