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

function startBrowserSpeech(setPrompt, setError) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    setError("SpeechRecognition not supported. Use Chrome.");
    return;
  }
  const rec = new SR();
  rec.lang = "en-US";
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  rec.onresult = (e) => {
    const text = e?.results?.[0]?.[0]?.transcript || "";
    if (text) setPrompt(text);
  };
  rec.onerror = (e) => setError("Speech error: " + (e?.error || "unknown"));
  rec.start();
}

function degToRad(d) {
  return (Number(d) || 0) * (Math.PI / 180);
}

export default function App() {
  const mountRef = useRef(null);
  const rendererRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const groupRef = useRef(null);
  const controlsRef = useRef(null);
  const rafRef = useRef(null);
  const modelRef = useRef(null);

  const [caps, setCaps] = useState(null);

  const [prompt, setPrompt] = useState("box with lid 120x80x60 mm");
  const [useOllama, setUseOllama] = useState(false);

  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  // UI controls: rotation + scale
  const [rotDeg, setRotDeg] = useState({ x: 0, y: 0, z: 0 });
  // scale multiplier (1.0 = normal)
  const [scaleMul, setScaleMul] = useState(1);

  useEffect(() => {
    getCapabilities().then(setCaps).catch(() => {});
  }, []);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    sceneRef.current = scene;
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

    // OrbitControls: drag rotate, pan, zoom
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.enableRotate = true;

    // Keep sensible camera behavior
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
      controls.update(); // needed for damping
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

  function clearPreview() {
    const group = groupRef.current;
    if (!group) return;
    while (group.children.length) group.remove(group.children[0]);
    modelRef.current = null;
  }

  function applyManualTransforms() {
    const model = modelRef.current;
    if (!model) return;
    model.rotation.set(degToRad(rotDeg.x), degToRad(rotDeg.y), degToRad(rotDeg.z));
    const s = Number(scaleMul) || 1;
    model.scale.setScalar(model.userData.__baseScale * s);
  }

  // Preview fix + add OrbitControls target
  function loadPreview(glbUrl) {
    const loader = new GLTFLoader();
    loader.load(
      glbUrl,
      (gltf) => {
        clearPreview();

        const model = gltf.scene;
        modelRef.current = model;
        groupRef.current.add(model);

        // bounds before transforms
        const box = new THREE.Box3().setFromObject(model);
        const size = new THREE.Vector3();
        box.getSize(size);
        const center = new THREE.Vector3();
        box.getCenter(center);

        // center at origin
        model.position.sub(center);

        // base scale so model fits view nicely
        const maxDim = Math.max(size.x, size.y, size.z);
        const target = 1.2;
        const baseScale = maxDim > 0 ? target / maxDim : 1;

        model.userData.__baseScale = baseScale;
        model.scale.setScalar(baseScale);

        // recompute bounds after scaling
        const box2 = new THREE.Box3().setFromObject(model);
        const size2 = new THREE.Vector3();
        box2.getSize(size2);
        const maxDim2 = Math.max(size2.x, size2.y, size2.z);

        // camera config to avoid clipping
        const cam = cameraRef.current;
        cam.near = Math.max(0.001, maxDim2 / 100);
        cam.far = Math.max(50, maxDim2 * 120);

        cam.position.set(maxDim2 * 2.6, maxDim2 * 1.8, maxDim2 * 2.6);
        cam.lookAt(0, 0, 0);
        cam.updateProjectionMatrix();

        // controls target at origin
        const controls = controlsRef.current;
        if (controls) {
          controls.target.set(0, 0, 0);
          controls.update();
        }

        // apply user transforms
        applyManualTransforms();
      },
      undefined,
      (e) => {
        console.error(e);
        setError("Preview load failed. Open the browser console for details.");
      }
    );
  }

  useEffect(() => {
    // whenever rotation or scale changes, apply to current model
    applyManualTransforms();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rotDeg.x, rotDeg.y, rotDeg.z, scaleMul]);

  function resetView() {
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

  async function onPlan() {
    setError("");
    setLoading(true);
    setPlan(null);
    setResult(null);
    clearPreview();
    try {
      const p = await planModel({ prompt, useOllama });
      setPlan(p);
    } catch (e) {
      setError(e.message || "Plan failed");
    } finally {
      setLoading(false);
    }
  }

  async function onGenerate() {
    setError("");
    setLoading(true);
    setResult(null);
    clearPreview();
    try {
      const p = await planModel({ prompt, useOllama });
      setPlan(p);

      if (p.questions && p.questions.length > 0) {
        setLoading(false);
        return;
      }

      const gen = await generateModel({
        prompt,
        modelType: p.model_type,
        params: p.params
      });
      setResult(gen);
      loadPreview(gen.preview_glb_url);
    } catch (e) {
      setError(e.message || "Generate failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "440px 1fr", height: "100vh" }}>
      <div style={{ padding: 16, borderRight: "1px solid #ddd", overflowY: "auto" }}>
        <h2 style={{ marginTop: 0 }}>{caps?.app_name || "FormForge"}</h2>
        <div style={{ fontSize: 13, color: "#555", marginBottom: 10 }}>
          {caps?.tagline || "Text and voice to printable functional 3D parts"}
        </div>
        <div style={{ marginTop: 20, fontSize: 12, color: "#888" }}>
          CadrixAI © 2026 Bhavyadeep Rao
        </div>


        <label style={{ display: "block", marginBottom: 8 }}>
          Prompt
          <textarea
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            style={{ width: "100%", marginTop: 6 }}
          />
        </label>

        <button
          onClick={() => startBrowserSpeech(setPrompt, setError)}
          disabled={loading}
          style={{ width: "100%", padding: "10px 12px" }}
        >
          Speak prompt
        </button>

        <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10 }}>
          <input type="checkbox" checked={useOllama} onChange={(e) => setUseOllama(e.target.checked)} />
          Use Ollama planner (optional)
        </label>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 12 }}>
          <button onClick={onPlan} disabled={loading} style={{ padding: "10px 12px" }}>
            {loading ? "Working..." : "Plan"}
          </button>
          <button onClick={onGenerate} disabled={loading} style={{ padding: "10px 12px" }}>
            {loading ? "Working..." : "Generate"}
          </button>
        </div>

        {/* View + transform controls */}
        <div style={{ marginTop: 12, padding: 12, border: "1px solid #ddd", borderRadius: 12, background: "#fafafa" }}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>View controls</div>

          <button onClick={resetView} style={{ width: "100%", padding: "10px 12px" }}>
            Reset view
          </button>

          <div style={{ marginTop: 10, fontSize: 12, color: "#555" }}>
            Drag: rotate | Right-drag / two-finger drag: pan | Scroll / pinch: zoom
          </div>

          <div style={{ fontWeight: 800, marginTop: 12 }}>Manual rotation (degrees)</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginTop: 6 }}>
            <label>
              X
              <input
                type="number"
                value={rotDeg.x}
                onChange={(e) => setRotDeg({ ...rotDeg, x: e.target.value })}
                style={{ width: "100%" }}
              />
            </label>
            <label>
              Y
              <input
                type="number"
                value={rotDeg.y}
                onChange={(e) => setRotDeg({ ...rotDeg, y: e.target.value })}
                style={{ width: "100%" }}
              />
            </label>
            <label>
              Z
              <input
                type="number"
                value={rotDeg.z}
                onChange={(e) => setRotDeg({ ...rotDeg, z: e.target.value })}
                style={{ width: "100%" }}
              />
            </label>
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

        {error && (
          <div style={{ marginTop: 12, color: "crimson", whiteSpace: "pre-wrap" }}>
            {error}
          </div>
        )}

        {plan && (
          <div style={{ marginTop: 12, lineHeight: 1.5 }}>
            <div><b>Template:</b> {plan.model_type}</div>

            {plan.assumptions?.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <b>Assumptions</b>
                <ul style={{ marginTop: 6 }}>
                  {plan.assumptions.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              </div>
            )}

            {plan.questions?.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <b>Questions</b>
                <ul style={{ marginTop: 6 }}>
                  {plan.questions.map((q, i) => <li key={i}>{q}</li>)}
                </ul>
                <div style={{ fontSize: 12, color: "#555" }}>
                  Answer by editing the prompt (include dimensions), then Plan again.
                </div>
              </div>
            )}

            <details style={{ marginTop: 8 }}>
              <summary style={{ cursor: "pointer" }}><b>Params</b></summary>
              <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(plan.params, null, 2)}</pre>
            </details>
          </div>
        )}

        {result && (
          <div style={{ marginTop: 12, lineHeight: 1.5 }}>
            <div><b>Generated:</b> {result.model_type}</div>
            <div><b>File ID:</b> {result.file_id}</div>
            <div style={{ marginTop: 10 }}>
              <a href={result.stl_download_url} target="_blank" rel="noreferrer">
                Download STL
              </a>
            </div>
          </div>
        )}

        {caps && (
          <div style={{
            marginTop: 16,
            padding: 14,
            border: "1px solid #ddd",
            borderRadius: 12,
            background: "#fafafa"
          }}>
            <div style={{ fontWeight: 800, marginBottom: 8 }}>Supported objects</div>
            <ul style={{ paddingLeft: 18, margin: 0 }}>
              {caps.supported.map((s) => (
                <li key={s.model_type} style={{ marginBottom: 10 }}>
                  <div style={{ fontWeight: 700 }}>{s.title}</div>
                  <div style={{ fontSize: 12, color: "#666" }}>{s.description}</div>
                  <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
                    Examples: {s.examples.join(" | ")}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div ref={mountRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
