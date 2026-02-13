const API = "http://localhost:8000";

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

export async function planModel({ prompt, useOllama }) {
  const res = await fetch(`${API}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, units: "mm", use_ollama: !!useOllama })
  });
  return handle(res);
}

export async function generateModel({ prompt, modelType, params }) {
  const res = await fetch(`${API}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, model_type: modelType, params })
  });
  return handle(res);
}
