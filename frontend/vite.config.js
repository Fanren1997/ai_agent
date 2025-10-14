import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000", // 后端 Flask 服务地址
        changeOrigin: true,
      },
    },
  },
});
