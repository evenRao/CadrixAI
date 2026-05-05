/*
CadrixAI
Author: Bhavyadeep Rao
Project: Capstone – Natural Language to Parametric 3D Modeling
Year – 2026

Designed and developed by Bhavyadeep Rao.
All core architecture, planning logic, and CAD generation implemented independently.
*/

import React, { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { getCapabilities, planModel, generateModel } from "./api.js";

function getSpeechRecognitionCtor() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function describeSpeechError(errorCode) {
  switch (errorCode) {
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone access is blocked. Allow microphone access for this site, then try again.";
    case "audio-capture":
      return "No microphone was found, or another app is using it.";
    case "no-speech":
      return "No speech was detected. Try speaking a little closer to the microphone.";
    case "network":
      return "The browser speech service could not be reached. Try again in a moment.";
    default:
      return `Speech error: ${errorCode || "unknown"}`;
  }
}

async function ensureMicrophoneAccess() {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  stream.getTracks().forEach((track) => track.stop());
}

function startBrowserSpeech({ onText, onError, onStart, onEnd, onStatus }) {
  const SR = getSpeechRecognitionCtor();
  if (!SR) {
    onError("SpeechRecognition not supported. Use Chrome or another Chromium browser.");
    return null;
  }
  const rec = new SR();
  rec.lang = "en-US";
  rec.interimResults = true;
  rec.continuous = false;
  rec.maxAlternatives = 1;
  rec.onstart = () => {
    onStart?.();
    onStatus?.("Listening... say your build request.");
  };
  rec.onresult = (e) => {
    const result = e?.results?.[e.results.length - 1];
    const text = result?.[0]?.transcript?.trim() || "";
    if (!text) return;
    if (result?.isFinal) {
      onText(text);
      onStatus?.("Captured speech prompt. You can plan or generate now.");
      return;
    }
    onStatus?.(`Listening: ${text}`);
  };
  rec.onerror = (e) => onError(describeSpeechError(e?.error));
  rec.onend = () => onEnd?.();
  rec.start();
  return rec;
}

function degToRad(d) {
  return (Number(d) || 0) * (Math.PI / 180);
}

function parseInputValue(definition, rawValue) {
  if (definition.type === "boolean") return !!rawValue;
  if (definition.type === "integer") {
    const next = parseInt(rawValue, 10);
    return Number.isNaN(next) ? rawValue : next;
  }
  if (definition.type === "number") {
    const next = parseFloat(rawValue);
    return Number.isNaN(next) ? rawValue : next;
  }
  return rawValue;
}

function formatModelType(modelType) {
  return modelType?.replaceAll("_", " ") || "Unknown";
}

export default function App() {
  const mountRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const groupRef = useRef(null);
  const controlsRef = useRef(null);
  const rafRef = useRef(null);
  const modelRef = useRef(null);
  const speechRef = useRef(null);

  const [caps, setCaps] = useState(null);
  const [prompt, setPrompt] = useState("Make a phone stand for a 75mm wide phone with a 20 degree angle and cable hole.");
  const [useLlm, setUseLlm] = useState(false);

  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState(null);
  const [result, setResult] = useState(null);
  const [editableParams, setEditableParams] = useState({});
  const [plannedPrompt, setPlannedPrompt] = useState("");
  const [error, setError] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speechStatus, setSpeechStatus] = useState("");

  const [rotDeg, setRotDeg] = useState({ x: 0, y: 0, z: 0 });
  const [scaleMul, setScaleMul] = useState(1);
  const speechSupported = useMemo(() => !!getSpeechRecognitionCtor(), []);

  useEffect(() => {
    getCapabilities().then(setCaps).catch(() => {});
  }, []);

  const groupedCapabilities = useMemo(() => {
    if (!caps?.supported) return [];
    const groups = new Map();
    caps.supported.forEach((item) => {
      const current = groups.get(item.category) || [];
      current.push(item);
      groups.set(item.category, current);
    });
    return Array.from(groups.entries());
  }, [caps]);

  const examplePrompts = useMemo(() => {
    if (!caps?.supported) return [];
    return caps.supported
      .filter((item) => item.implemented)
      .flatMap((item) => item.examples.map((example) => ({ modelType: item.model_type, example })))
      .slice(0, 8);
  }, [caps]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf6f6f6);

    const camera = new THREE.PerspectiveCamera(60, 1, 0.001, 5000);
    camera.position.set(2, 1.5, 2);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    rendererRef.current = renderer;
    mount.appendChild(renderer.domElement);

    const group = new THREE.Group();
    groupRef.current = group;
    scene.add(group);

    scene.add(new THREE.AmbientLight(0xffffff, 1.0));
    const dir = new THREE.DirectionalLight(0xffffff, 1.0);
    dir.position.set(2, 3, 4);
    scene.add(dir);

    const grid = new THREE.GridHelper(4, 40);
    scene.add(grid);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.enableRotate = true;
    controls.minDistance = 0.2;
    controls.maxDistance = 50;
    controlsRef.current = controls;

    const resize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
    };

    const animate = () => {
      rafRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };

    window.addEventListener("resize", resize);
    resize();
    animate();

    return () => {
      window.removeEventListener("resize", resize);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      controls.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  useEffect(() => {
    return () => {
      if (!speechRef.current) return;
      speechRef.current.onend = null;
      speechRef.current.stop();
      speechRef.current = null;
    };
  }, []);

  function clearPreview() {
    const group = groupRef.current;
    if (!group) return;
    while (group.children.length) group.remove(group.children[0]);
    modelRef.current = null;
  }

  function fitCameraToObject(object) {
    const cam = cameraRef.current;
    const controls = controlsRef.current;
    if (!cam || !controls || !object) return;

    object.updateWorldMatrix(true, true);
    const box = new THREE.Box3().setFromObject(object);
    const size = new THREE.Vector3();
    box.getSize(size);
    const center = new THREE.Vector3();
    box.getCenter(center);
    const maxDim = Math.max(size.x, size.y, size.z) || 1;

    cam.near = Math.max(0.001, maxDim / 100);
    cam.far = Math.max(50, maxDim * 120);
    cam.position.set(center.x + maxDim * 2.6, center.y + maxDim * 1.8, center.z + maxDim * 2.6);
    cam.lookAt(center);
    cam.updateProjectionMatrix();

    controls.target.copy(center);
    controls.update();
  }

  function applyManualTransforms() {
    const preview = modelRef.current;
    if (!preview) return;
    preview.rotation.set(degToRad(rotDeg.x), degToRad(rotDeg.y), degToRad(rotDeg.z));
    const s = Number(scaleMul) || 1;
    preview.scale.setScalar(preview.userData.__baseScale * s);
    preview.updateWorldMatrix(true, true);
  }

  function loadPreview(glbUrl) {
    const loader = new GLTFLoader();
    loader.load(
      glbUrl,
      (gltf) => {
        clearPreview();

        const model = gltf.scene;
        model.rotation.x = -Math.PI / 2;

        const preview = new THREE.Group();
        preview.add(model);
        groupRef.current.add(preview);
        modelRef.current = preview;

        model.updateWorldMatrix(true, true);
        const box = new THREE.Box3().setFromObject(model);
        const center = new THREE.Vector3();
        box.getCenter(center);

        model.position.set(-center.x, -box.min.y, -center.z);
        preview.updateWorldMatrix(true, true);

        const box2 = new THREE.Box3().setFromObject(preview);
        const size2 = new THREE.Vector3();
        box2.getSize(size2);
        const maxDim = Math.max(size2.x, size2.y, size2.z);
        preview.userData.__baseScale = maxDim > 0 ? 1.2 / maxDim : 1;

        applyManualTransforms();
        fitCameraToObject(preview);
      },
      undefined,
      (e) => {
        console.error(e);
        setError("Preview load failed. Open the browser console for details.");
      }
    );
  }

  useEffect(() => {
    applyManualTransforms();
    if (modelRef.current) fitCameraToObject(modelRef.current);
  }, [rotDeg.x, rotDeg.y, rotDeg.z, scaleMul]);

  function resetView() {
    if (modelRef.current) {
      fitCameraToObject(modelRef.current);
      return;
    }
    const cam = cameraRef.current;
    const controls = controlsRef.current;
    if (!cam || !controls) return;
    cam.position.set(2, 1.5, 2);
    cam.near = 0.001;
    cam.far = 2000;
    cam.lookAt(0, 0, 0);
    cam.updateProjectionMatrix();
    controls.target.set(0, 0, 0);
    controls.update();
  }

  async function onSpeakPrompt() {
    setError("");
    if (speechRef.current) {
      speechRef.current.stop();
      setSpeechStatus("Speech input stopped.");
      return;
    }

    setSpeechStatus("Requesting microphone access...");
    try {
      await ensureMicrophoneAccess();
    } catch (e) {
      setError(describeSpeechError(e?.name === "NotAllowedError" ? "not-allowed" : e?.name));
      setSpeechStatus("Microphone permission is required for speech input.");
      return;
    }

    const recognition = startBrowserSpeech({
      onText: (text) => {
        setPrompt(text);
        setError("");
      },
      onError: (message) => {
        setError(message);
        setSpeechStatus("Speech input could not start. Check microphone access and browser support.");
      },
      onStart: () => {
        setIsListening(true);
      },
      onEnd: () => {
        speechRef.current = null;
        setIsListening(false);
      },
      onStatus: (message) => {
        setSpeechStatus(message);
      },
    });

    if (recognition) {
      speechRef.current = recognition;
    }
  }

  function seedEditableParams(planResult) {
    const next = {};
    (planResult.parameter_definitions || []).forEach((definition) => {
      next[definition.key] = planResult.parameters?.[definition.key] ?? definition.default ?? "";
    });
    setEditableParams(next);
    setPlannedPrompt(prompt);
  }

  async function runPlan(forceRefresh = false) {
    if (!forceRefresh && plan && plannedPrompt === prompt) {
      return plan;
    }

    const nextPlan = await planModel({ prompt, useLlm });
    setPlan(nextPlan);
    seedEditableParams(nextPlan);
    return nextPlan;
  }

  async function onPlan() {
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const nextPlan = await runPlan(true);
      if (!nextPlan.success && nextPlan.errors?.length) {
        setError(nextPlan.errors.join("\n"));
      }
    } catch (e) {
      setError(e.message || "Plan failed");
    } finally {
      setLoading(false);
    }
  }

  async function onGenerate() {
    setError("");
    setLoading(true);
    clearPreview();
    try {
      const nextPlan = await runPlan(plannedPrompt !== prompt);
      if (!nextPlan.success) {
        setError(nextPlan.errors?.join("\n") || "Fix the validation errors before generating.");
        setResult(null);
        return;
      }
      if (!nextPlan.implemented) {
        setError(nextPlan.todo || `${nextPlan.title || formatModelType(nextPlan.model_type)} is scaffolded but not implemented yet.`);
        setResult(null);
        return;
      }

      const nextResult = await generateModel({
        prompt,
        modelType: nextPlan.model_type,
        parameters: editableParams,
        useLlm,
      });
      setResult(nextResult);
      if (!nextResult.success) {
        setError(nextResult.errors?.join("\n") || "Generate failed");
        return;
      }
      if (nextResult.files?.glb) {
        loadPreview(nextResult.files.glb);
      }
    } catch (e) {
      setError(e.message || "Generate failed");
    } finally {
      setLoading(false);
    }
  }

  function renderMessages(title, items, tone) {
    if (!items?.length) return null;
    return (
      <div
        style={{
          marginTop: 10,
          padding: 10,
          borderRadius: 12,
          border: `1px solid ${tone === "error" ? "#e4b3b3" : "#dfd3aa"}`,
          background: tone === "error" ? "#fff4f4" : "#fff9ea",
        }}
      >
        <div style={{ fontWeight: 800, marginBottom: 6 }}>{title}</div>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {items.map((item, index) => (
            <li key={`${title}-${index}`} style={{ marginBottom: 4 }}>{item}</li>
          ))}
        </ul>
      </div>
    );
  }

  const activeSummary = result?.success ? result : plan;
  const activeWarnings = result?.warnings || plan?.warnings || [];
  const activeErrors = result?.errors || plan?.errors || [];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "460px minmax(0, 1fr)",
        width: "100vw",
        height: "100vh",
        overflow: "hidden",
        overscrollBehavior: "none",
        background: "#fff"
      }}
    >
      <div
        style={{
          padding: 16,
          borderRight: "1px solid #ddd",
          overflowY: "auto",
          overflowX: "hidden",
          height: "100vh",
          position: "sticky",
          top: 0,
          alignSelf: "start",
          overscrollBehavior: "contain",
          background: "#fff",
          zIndex: 2
        }}
      >
        <h2 style={{ marginTop: 0, marginBottom: 6 }}>{caps?.app_name || "CadrixAI V2"}</h2>
        <div style={{ fontSize: 13, color: "#555", marginBottom: 10 }}>
          {caps?.tagline || "AI-assisted parametric CAD for printable functional parts"}
        </div>
        <div style={{ marginBottom: 16, fontSize: 12, color: "#888" }}>
          CadrixAI © 2026 Bhavyadeep Rao
        </div>

        <div style={{ padding: 14, border: "1px solid #ddd", borderRadius: 12, background: "#fafafa" }}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>Prompt</div>
          <textarea
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            style={{ width: "100%", marginTop: 6 }}
          />

          <div style={{ fontWeight: 800, marginTop: 12, marginBottom: 6 }}>Prompt examples</div>
          <div style={{ display: "grid", gap: 6 }}>
            {examplePrompts.map((item, index) => (
              <button
                key={`${item.modelType}-${index}`}
                type="button"
                onClick={() => setPrompt(item.example)}
                style={{ textAlign: "left", padding: "8px 10px", fontSize: 12 }}
              >
                {item.example}
              </button>
            ))}
          </div>

          <button
            onClick={onSpeakPrompt}
            disabled={loading || (!speechSupported && !isListening)}
            style={{ width: "100%", padding: "10px 12px", marginTop: 12 }}
          >
            {isListening ? "Stop listening" : "Speak prompt"}
          </button>

          <div style={{ marginTop: 8, fontSize: 12, color: "#555" }}>
            {speechSupported
              ? speechStatus || "Uses your browser microphone and fills the same V2 prompt box."
              : "Speech input needs a Chromium browser with microphone access."}
          </div>

          <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10 }}>
            <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
            Use local Ollama parser (optional)
          </label>

          <div style={{ marginTop: 6, fontSize: 12, color: "#666" }}>
            Falls back to the built-in rule-based parser if Ollama is unavailable.
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 12 }}>
            <button onClick={onPlan} disabled={loading} style={{ padding: "10px 12px" }}>
              {loading ? "Working..." : "Plan"}
            </button>
            <button onClick={onGenerate} disabled={loading} style={{ padding: "10px 12px" }}>
              {loading ? "Working..." : "Generate"}
            </button>
          </div>
        </div>

        <div style={{ marginTop: 12, padding: 14, border: "1px solid #ddd", borderRadius: 12, background: "#fafafa" }}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>V2 Supported Builds</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {(caps?.highlighted_builds || []).map((build) => (
              <div key={build} style={{ padding: "6px 10px", borderRadius: 999, background: "#fff", border: "1px solid #ddd", fontSize: 12 }}>
                {build}
              </div>
            ))}
          </div>
        </div>

        {activeSummary && (
          <div style={{ marginTop: 12, padding: 14, border: "1px solid #ddd", borderRadius: 12, background: "#fafafa" }}>
            <div style={{ fontWeight: 800, marginBottom: 8 }}>Design summary</div>
            <div><b>Model:</b> {activeSummary.title || formatModelType(activeSummary.model_type)}</div>
            {activeSummary.category && <div><b>Category:</b> {activeSummary.category}</div>}
            {"implemented" in activeSummary && (
              <div><b>Status:</b> {activeSummary.implemented ? "Available now" : "Registry stub / coming next"}</div>
            )}

            {activeSummary.metadata?.printability_score !== undefined && (
              <div style={{ marginTop: 8 }}>
                <b>Printability score:</b> {activeSummary.metadata.printability_score}/100
              </div>
            )}

            {activeSummary.metadata?.estimated_dimensions_mm && Object.keys(activeSummary.metadata.estimated_dimensions_mm).length > 0 && (
              <div style={{ marginTop: 8 }}>
                <b>Estimated dimensions (mm):</b>{" "}
                {Object.entries(activeSummary.metadata.estimated_dimensions_mm).map(([key, value]) => `${key.toUpperCase()}: ${value}`).join(" | ")}
              </div>
            )}

            {activeSummary.intent && (
              <details style={{ marginTop: 10 }}>
                <summary style={{ cursor: "pointer" }}><b>Structured intent</b></summary>
                <pre style={{ whiteSpace: "pre-wrap", marginTop: 8 }}>{JSON.stringify(activeSummary.intent, null, 2)}</pre>
              </details>
            )}

            {activeSummary.parameters && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: "pointer" }}><b>Resolved parameters</b></summary>
                <pre style={{ whiteSpace: "pre-wrap", marginTop: 8 }}>{JSON.stringify(activeSummary.parameters, null, 2)}</pre>
              </details>
            )}

            {activeSummary.assumptions?.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Assumptions</div>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {activeSummary.assumptions.map((item, index) => (
                    <li key={`assumption-${index}`} style={{ marginBottom: 4 }}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            {result?.success && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Files</div>
                <div><a href={result.files.stl} target="_blank" rel="noreferrer">Download STL</a></div>
                {result.files.step && (
                  <div style={{ marginTop: 6 }}>
                    <a href={result.files.step} target="_blank" rel="noreferrer">Download Fusion STEP</a>
                  </div>
                )}
                {result.files.extra_downloads?.map((item, index) => (
                  <div key={`${item.url}-${index}`} style={{ marginTop: 6 }}>
                    <a href={item.url} target="_blank" rel="noreferrer">Download {item.label}</a>
                  </div>
                ))}
                {result.files.step && (
                  <div style={{ marginTop: 6, fontSize: 12, color: "#555" }}>
                    Fusion users should prefer STEP to preserve units during post-processing.
                  </div>
                )}
              </div>
            )}

            {activeSummary.todo && (
              <div style={{ marginTop: 10, fontSize: 12, color: "#555" }}>{activeSummary.todo}</div>
            )}
          </div>
        )}

        {renderMessages("Validation Errors", activeErrors, "error")}
        {renderMessages("Validation Warnings", activeWarnings, "warning")}

        {plan?.parameter_definitions?.length > 0 && (
          <div style={{ marginTop: 12, padding: 14, border: "1px solid #ddd", borderRadius: 12, background: "#fafafa" }}>
            <div style={{ fontWeight: 800, marginBottom: 8 }}>Advanced parameter controls</div>
            <div style={{ display: "grid", gap: 10 }}>
              {plan.parameter_definitions.map((definition) => (
                <label key={definition.key} style={{ display: "block" }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>
                    {definition.label}
                    {definition.unit ? ` (${definition.unit})` : ""}
                  </div>
                  <div style={{ fontSize: 12, color: "#666", marginBottom: 4 }}>{definition.description}</div>
                  {definition.type === "boolean" ? (
                    <input
                      type="checkbox"
                      checked={!!editableParams[definition.key]}
                      onChange={(e) => setEditableParams((current) => ({ ...current, [definition.key]: e.target.checked }))}
                    />
                  ) : (
                    <input
                      type="number"
                      step={definition.type === "integer" ? 1 : 0.1}
                      min={definition.minimum ?? undefined}
                      max={definition.maximum ?? undefined}
                      value={editableParams[definition.key] ?? ""}
                      onChange={(e) =>
                        setEditableParams((current) => ({
                          ...current,
                          [definition.key]: parseInputValue(definition, e.target.value),
                        }))
                      }
                      style={{ width: "100%" }}
                    />
                  )}
                </label>
              ))}
            </div>
          </div>
        )}

        <div style={{ marginTop: 12, padding: 14, border: "1px solid #ddd", borderRadius: 12, background: "#fafafa" }}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>View controls</div>
          <button onClick={resetView} style={{ width: "100%", padding: "10px 12px" }}>
            Reset view
          </button>
          <div style={{ marginTop: 10, fontSize: 12, color: "#555" }}>
            Drag: rotate | Right-drag / two-finger drag: pan | Scroll / pinch: zoom
          </div>

          <div style={{ fontWeight: 800, marginTop: 12 }}>Manual rotation (degrees)</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginTop: 6 }}>
            {["x", "y", "z"].map((axis) => (
              <label key={axis}>
                {axis.toUpperCase()}
                <input
                  type="number"
                  value={rotDeg[axis]}
                  onChange={(e) => setRotDeg({ ...rotDeg, [axis]: e.target.value })}
                  style={{ width: "100%" }}
                />
              </label>
            ))}
          </div>

          <div style={{ fontWeight: 800, marginTop: 12 }}>Scale</div>
          <label style={{ display: "block", marginTop: 6 }}>
            Scale multiplier (1.0 = normal)
            <input
              type="number"
              step="0.05"
              min="0.1"
              max="10"
              value={scaleMul}
              onChange={(e) => setScaleMul(e.target.value)}
              style={{ width: "100%" }}
            />
          </label>
        </div>

        {caps && (
          <div style={{ marginTop: 12, padding: 14, border: "1px solid #ddd", borderRadius: 12, background: "#fafafa" }}>
            <div style={{ fontWeight: 800, marginBottom: 8 }}>Supported model categories</div>
            {groupedCapabilities.map(([category, items]) => (
              <div key={category} style={{ marginBottom: 14 }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>{category}</div>
                <div style={{ display: "grid", gap: 8 }}>
                  {items.map((item) => (
                    <div key={item.model_type} style={{ padding: 10, borderRadius: 10, background: "#fff", border: "1px solid #e6e6e6" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                        <div style={{ fontWeight: 700 }}>{item.title}</div>
                        <div style={{ fontSize: 11, color: item.implemented ? "#1c6f43" : "#8b6a1b" }}>
                          {item.implemented ? "Ready" : "Stub"}
                        </div>
                      </div>
                      <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>{item.description}</div>
                      {item.examples?.length > 0 && (
                        <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>
                          Example: {item.examples[0]}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div style={{ marginTop: 12, color: "crimson", whiteSpace: "pre-wrap" }}>
            {error}
          </div>
        )}
      </div>

      <div
        ref={mountRef}
        style={{
          width: "100%",
          minWidth: 0,
          height: "100vh",
          minHeight: 0,
          overflow: "hidden",
          overscrollBehavior: "none",
          touchAction: "none"
        }}
      />
    </div>
  );
}
