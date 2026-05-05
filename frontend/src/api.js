/*
CadrixAI
Author: Bhavyadeep Rao
Project: Capstone – Natural Language to Parametric 3D Modeling
Year – 2026

Designed and developed by Bhavyadeep Rao.
All core architecture, planning logic, and CAD generation implemented independently.
*/

const API = "http://localhost:8000/v2";

async function handle(res) {
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Request failed");
  }
  return res.json();
}

export async function getCapabilities() {
  const res = await fetch(`${API}/capabilities`);
  return handle(res);
}

export async function planModel({ prompt, useLlm = false, modelType = null }) {
  const res = await fetch(`${API}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, units: "mm", use_llm: !!useLlm, model_type: modelType })
  });
  return handle(res);
}

export async function generateModel({ prompt, modelType = null, parameters = {}, useLlm = false }) {
  const res = await fetch(`${API}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, model_type: modelType, parameters, use_llm: !!useLlm })
  });
  return handle(res);
}
