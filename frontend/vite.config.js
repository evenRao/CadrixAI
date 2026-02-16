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
  server: { port: 5173 }
});