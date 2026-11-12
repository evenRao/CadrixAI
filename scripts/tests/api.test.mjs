import assert from "node:assert/strict";
import test from "node:test";
import { getCapabilities, generateModel, planModel } from "../../frontend/src/api.js";

test("API requests use the deployed page origin instead of a developer's localhost", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => ({ ok: true, json: async () => ({ supported: [] }) }));
  await getCapabilities();
  assert.equal(fetch.mock.calls[0].arguments[0], "/v2/capabilities");
});

test("generation sends edited parameters, including false and zero values", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => ({ ok: true, json: async () => ({ success: true }) }));
  const parameters = { length_mm: 140, rounded_edges: false, corner_radius_mm: 0 };
  await generateModel({ prompt: "Parts tray", modelType: "parts_tray", parameters });
  const [url, request] = fetch.mock.calls[0].arguments;
  assert.equal(url, "/v2/generate");
  assert.deepEqual(JSON.parse(request.body), { prompt: "Parts tray", model_type: "parts_tray", parameters, use_llm: false });
});

test("HTTP failures reach the caller with the backend error", async (t) => {
  t.mock.method(globalThis, "fetch", async () => ({ ok: false, text: async () => "Backend unavailable" }));
  await assert.rejects(planModel({ prompt: "Tray" }), /Backend unavailable/);
});
