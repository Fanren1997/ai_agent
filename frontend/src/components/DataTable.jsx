import React from "react";

export default function DataTable({ data }) {
  if (!data?.length) return <p>暂无数据</p>;
  const headers = Object.keys(data[0]);
  return (
    <div className="table-box">
      <table>
        <thead>
          <tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i}>
              {headers.map((h) => <td key={h}>{String(row[h] ?? "")}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
