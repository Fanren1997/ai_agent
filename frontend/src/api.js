const api = {
  health: async () => (await fetch("/api/health")).json(),
  chat: async (message) =>
    await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: [{ role: "user", content: message }] }),
    }).then((res) => res.json()),
};
export default api;
