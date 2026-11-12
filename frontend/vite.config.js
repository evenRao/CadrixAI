/*
CadrixAI
Author: Bhavyadeep Rao
Project: Capstone – Natural Language to Parametric 3D Modeling
Year – 2026

Designed and developed by Bhavyadeep Rao.
All core architecture, planning logic, and CAD generation implemented independently.
*/

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/v2": "http://127.0.0.1:8000",
      "/files": "http://127.0.0.1:8000"
    }
  }
});
