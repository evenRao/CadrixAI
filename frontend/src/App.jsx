/* CadrixAI — Designed and developed by Bhavyadeep Rao. © 2026 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { getCapabilities, planModel, generateModel } from "./api.js";
import Icon from "./components/Icon.jsx";
import Modal from "./components/Modal.jsx";
import useModelViewport from "./useModelViewport.js";
import "./styles.css";

const STARTERS = [
  { title: "Phone stand", model_type: "phone_stand", example: "Make a phone stand for a 75mm wide phone with a 50 degree angle and cable hole." },
  { title: "Box with lid", model_type: "box_with_lid", example: "Box with lid 120x80x60 mm with 0.4mm clearance." },
  { title: "Cable clip", model_type: "cable_clip", example: "Make a cable clip for a 6mm cable." },
];
const speechConstructor = () => window.SpeechRecognition || window.webkitSpeechRecognition;
const parseValue = (definition, value) => value === "" ? "" : definition.type === "integer" ? parseInt(value, 10) : definition.type === "number" ? Number(value) : value;
const readableName = (value) => value?.replaceAll("_", " ") || "Untitled model";
const seedParameters = (plan) => Object.fromEntries((plan.parameter_definitions || []).map((definition) => [definition.key, plan.parameters?.[definition.key] ?? definition.default ?? ""]));
const inputKey = (prompt, useLlm, modelType) => JSON.stringify({ prompt, useLlm, modelType });

function ParameterField({ definition, value, onChange, disabled }) {
  const id = `parameter-${definition.key}`;
  if (definition.type === "boolean") return (
    <label className="switch-row" htmlFor={id}>
      <span>{definition.label}</span>
      <input id={id} className="switch" type="checkbox" checked={!!value} onChange={(event) => onChange(event.target.checked)} disabled={disabled} aria-describedby={`${id}-hint`} />
      <span className="sr-only" id={`${id}-hint`}>{definition.description}</span>
    </label>
  );
  return (
    <div className="parameter-field">
      <label htmlFor={id}>{definition.label}</label>
      <div className="unit-input">
        <input id={id} type={definition.type === "text" ? "text" : "number"} step={definition.type === "integer" ? 1 : "any"} min={definition.minimum ?? undefined} max={definition.maximum ?? undefined} value={value ?? ""} required onChange={(event) => onChange(parseValue(definition, event.target.value))} disabled={disabled} aria-describedby={`${id}-hint`} />
        {definition.unit && <span>{definition.unit === "deg" ? "°" : definition.unit}</span>}
      </div>
      <span className="field-hint" id={`${id}-hint`}>{definition.description}</span>
    </div>
  );
}

function Messages({ title, items, warning = false }) {
  if (!items?.length) return null;
  return <section className={`message ${warning ? "message-warning" : "message-error"}`} role={warning ? "status" : "alert"}><h3><Icon name="alert" size={16} />{title}</h3><ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul></section>;
}

export default function App() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem("cadrix-theme") === "light" ? "light" : "dark"; } catch { return "dark"; }
  });
  const [caps, setCaps] = useState(null);
  const [capsError, setCapsError] = useState("");
  const [prompt, setPrompt] = useState("");
  const [useLlm, setUseLlm] = useState(false);
  const [selectedModel, setSelectedModel] = useState(null);
  const [tab, setTab] = useState("describe");
  const [modal, setModal] = useState(null);
  const [templateQuery, setTemplateQuery] = useState("");
  const [templateCategory, setTemplateCategory] = useState("");
  const [plan, setPlan] = useState(null);
  const [plannedKey, setPlannedKey] = useState("");
  const [parameters, setParameters] = useState({});
  const [result, setResult] = useState(null);
  const [validation, setValidation] = useState(null);
  const [generatedKey, setGeneratedKey] = useState("");
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [previewLoadError, setPreviewLoadError] = useState("");
  const [listening, setListening] = useState(false);
  const [speechStatus, setSpeechStatus] = useState("");
  const [rotation, setRotation] = useState({ x: 0, y: 0, z: 0 });
  const [scale, setScale] = useState(1);
  const [showGrid, setShowGrid] = useState(true);
  const speechRef = useRef(null);
  const promptRef = useRef(null);
  const parametersForm = useRef(null);
  const exportRef = useRef(null);
  const busy = !!stage;
  const currentKey = inputKey(prompt, useLlm, selectedModel);
  const currentSnapshot = JSON.stringify({ input: currentKey, parameters });
  const planCurrent = plannedKey === currentKey;
  const modelCurrent = !!result?.success && generatedKey === currentSnapshot;
  const { mountRef, hasModel, previewError, loadPreview, fitView } = useModelViewport({ theme, showGrid, rotation, scale });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    try { localStorage.setItem("cadrix-theme", theme); } catch { /* Theme works without storage. */ }
  }, [theme]);

  async function refreshCapabilities() {
    setCapsError("");
    try { setCaps(await getCapabilities()); } catch { setCapsError("Template library is unavailable. Check that the backend is running, then retry."); }
  }
  useEffect(() => { refreshCapabilities(); }, []);
  useEffect(() => () => { if (speechRef.current) { speechRef.current.onend = null; speechRef.current.stop(); } }, []);
  useEffect(() => {
    const closeExport = (event) => {
      if (exportRef.current && (!exportRef.current.contains(event.target) || event.key === "Escape")) exportRef.current.open = false;
    };
    document.addEventListener("pointerdown", closeExport);
    document.addEventListener("keydown", closeExport);
    return () => { document.removeEventListener("pointerdown", closeExport); document.removeEventListener("keydown", closeExport); };
  }, []);

  const definitions = plan?.parameter_definitions || [];
  const primaryDefinitions = definitions.filter((item) => item.required && item.type !== "boolean");
  const featureDefinitions = definitions.filter((item) => item.type === "boolean");
  const advancedDefinitions = definitions.filter((item) => !item.required && item.type !== "boolean");
  const templates = useMemo(() => (caps?.supported || []).filter((item) => (!templateCategory || item.category === templateCategory) && `${item.title} ${item.description}`.toLowerCase().includes(templateQuery.toLowerCase())), [caps, templateQuery, templateCategory]);
  const activeValidation = validation?.key === currentSnapshot ? validation.response : modelCurrent ? result : null;
  const warnings = activeValidation?.warnings || [];
  const errors = activeValidation?.errors || [];
  const summary = modelCurrent ? result : plan || result;
  const status = busy ? stage : !summary ? "No model yet" : errors.length ? "Needs attention" : !modelCurrent ? (result ? "Changes not generated" : "Ready to generate") : warnings.length ? `${warnings.length} print ${warnings.length === 1 ? "note" : "notes"}` : "Checks passed";

  function selectTemplate(item) {
    setPrompt(item.example || item.examples?.[0] || item.title);
    setSelectedModel(item.model_type);
    setError("");
    setTab("describe");
    setModal(null);
    requestAnimationFrame(() => promptRef.current?.focus());
  }

  async function preparePlan() {
    if (plan && planCurrent) return { nextPlan: plan, nextParameters: parameters };
    setStage("Understanding your design…");
    const nextPlan = await planModel({ prompt: prompt.trim(), useLlm, modelType: selectedModel });
    const nextParameters = seedParameters(nextPlan);
    setPlan(nextPlan);
    setPlannedKey(currentKey);
    setParameters(nextParameters);
    setValidation({ response: nextPlan, key: JSON.stringify({ input: currentKey, parameters: nextParameters }) });
    return { nextPlan, nextParameters };
  }

  async function reviewDimensions() {
    if (!prompt.trim() || busy) return;
    setError("");
    try {
      const { nextPlan } = await preparePlan();
      if (nextPlan.parameter_definitions?.length) setTab("adjust");
      if (!nextPlan.model_type && !nextPlan.errors?.length) setError("Describe a supported part or choose a template.");
    } catch (event) { setError(event.message || "Couldn't review this design. Try again."); }
    finally { setStage(""); }
  }

  async function generate(event) {
    event?.preventDefault();
    if (!prompt.trim() || busy) return;
    if (tab === "adjust" && !parametersForm.current?.reportValidity()) return;
    setError("");
    try {
      const { nextPlan, nextParameters } = await preparePlan();
      if (!nextPlan.model_type || !nextPlan.implemented) {
        setError(nextPlan.todo || (nextPlan.errors?.length ? "" : "This model isn't available yet. Choose a supported template."));
        return;
      }
      if (!nextPlan.success && !planCurrent) {
        if (nextPlan.parameter_definitions?.length) setTab("adjust");
        return;
      }
      setStage("Building your model…");
      const nextResult = await generateModel({ prompt: prompt.trim(), modelType: nextPlan.model_type, parameters: nextParameters, useLlm });
      setValidation({ response: nextResult, key: JSON.stringify({ input: currentKey, parameters: nextParameters }) });
      if (!nextResult.success) { if (nextPlan.parameter_definitions?.length) setTab("adjust"); return; }
      setResult(nextResult);
      setGeneratedKey(JSON.stringify({ input: currentKey, parameters: nextParameters }));
      setTab("adjust");
      setPreviewLoadError("");
      if (nextResult.files?.glb) {
        setStage("Loading preview…");
        try { await loadPreview(nextResult.files.glb); } catch { setPreviewLoadError("The model is ready to export, but its 3D preview couldn't load."); }
      }
    } catch (event) { setError(event.message || "Couldn't generate this model. Try again."); }
    finally { setStage(""); }
  }

  async function speak() {
    if (speechRef.current) { speechRef.current.stop(); return; }
    const SpeechRecognition = speechConstructor();
    if (!SpeechRecognition) { setSpeechStatus("Voice input needs a browser with speech recognition, such as Chrome or Edge."); return; }
    try {
      setSpeechStatus("Requesting microphone access…");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = true;
      recognition.onstart = () => { setListening(true); setSpeechStatus("Listening… describe your part."); };
      recognition.onresult = (event) => {
        const item = event.results[event.results.length - 1];
        if (item.isFinal) { setPrompt(item[0].transcript); setSelectedModel(null); setSpeechStatus("Prompt captured. Review it before creating your model."); }
        else setSpeechStatus(`Listening: ${item[0].transcript}`);
      };
      recognition.onerror = (event) => setSpeechStatus(event.error === "not-allowed" ? "Microphone access is blocked. Allow it in your browser settings." : `Voice input stopped: ${event.error}. You can type your prompt instead.`);
      recognition.onend = () => { speechRef.current = null; setListening(false); };
      speechRef.current = recognition;
      recognition.start();
    } catch { speechRef.current = null; setSpeechStatus("Microphone unavailable. Check browser permissions or type your prompt."); }
  }

  const renderParameter = (definition) => <ParameterField key={definition.key} definition={definition} value={parameters[definition.key]} disabled={busy || !planCurrent} onChange={(value) => setParameters((current) => ({ ...current, [definition.key]: value }))} />;
  const toggleTheme = () => setTheme((current) => current === "dark" ? "light" : "dark");

  return (
    <div className="workspace" data-theme={theme}>
      <a className="skip-link" href="#workspace-content">Skip to workspace</a>
      <header className="topbar">
        <a className="brand" href="#" aria-label="CadrixAI workspace" onClick={(event) => event.preventDefault()}><span className="brand-mark"><Icon name="cube" size={22} /></span><span>Cadrix<span className="brand-ai">AI</span></span></a>
        <div className="document-title"><span>{summary?.title || readableName(summary?.model_type)}</span>{result && !modelCurrent && <span className="unsaved-dot" title="Changes not generated" />}</div>
        <div className="topbar-actions">
          <button className="icon-button theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}><Icon name={theme === "dark" ? "sun" : "moon"} /></button>
          <button className="icon-button" onClick={() => setModal("settings")} aria-label="Settings" title="Settings"><Icon name="settings" /></button>
          {modelCurrent && result?.files ? (
            <details className="export-menu" ref={exportRef}>
              <summary className="button button-primary"><Icon name="download" size={16} /><span>Export</span><Icon name="chevron" size={15} /></summary>
              <div className="dropdown"><div className="dropdown-label">Download model</div>{result.files.stl && <a href={result.files.stl} download target="_blank" rel="noreferrer"><span>STL</span><small>For 3D printing</small></a>}{result.files.step && <a href={result.files.step} download target="_blank" rel="noreferrer"><span>STEP</span><small>For CAD editing</small></a>}{result.files.glb && <a href={result.files.glb} download target="_blank" rel="noreferrer"><span>GLB</span><small>3D preview format</small></a>}{result.files.extra_downloads?.map((item) => <a key={item.url} href={item.url} download target="_blank" rel="noreferrer">{item.label}</a>)}</div>
            </details>
          ) : <button className="button button-primary export-disabled" disabled title={result ? "Update your model before exporting" : "Create a model to export"}><Icon name="download" size={16} />Export<Icon name="chevron" size={15} /></button>}
        </div>
      </header>

      <main id="workspace-content" className="workspace-body">
        <aside className="inspector" aria-label="Design controls">
          <div className="inspector-tabs" role="tablist" aria-label="Design workflow">
            {["describe", "adjust"].map((item) => <button type="button" key={item} id={`${item}-tab`} role="tab" aria-selected={tab === item} aria-controls={`${item}-panel`} tabIndex={tab === item ? 0 : -1} onKeyDown={(event) => { if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) { event.preventDefault(); const next = event.key === "Home" ? "describe" : event.key === "End" ? "adjust" : tab === "describe" ? "adjust" : "describe"; setTab(next); document.getElementById(`${next}-tab`).focus(); } }} onClick={() => setTab(item)}><Icon name={item === "describe" ? "sparkle" : "tune"} size={16} />{item === "describe" ? "Describe" : "Adjust"}</button>)}
          </div>
          <div id="describe-panel" className="inspector-panel" role="tabpanel" aria-labelledby="describe-tab" hidden={tab !== "describe"}>
            <form id="describe-form" onSubmit={generate} className="describe-form">
              <div className="section-heading"><span className="eyebrow">FROM IDEA TO OBJECT</span><h1>What would you<br />like to make?</h1><p>Describe a functional part. We’ll handle the geometry.</p></div>
              <label htmlFor="design-prompt" className="sr-only">Describe your part</label>
              <div className={`prompt-composer ${listening ? "is-listening" : ""}`}><textarea ref={promptRef} id="design-prompt" rows={6} maxLength={800} value={prompt} onChange={(event) => { setPrompt(event.target.value); setSelectedModel(null); }} placeholder="A phone stand with a charging cable slot, sized for my phone…" disabled={busy || listening} required /><div className="composer-bottom"><span>Dimensions in mm</span><button type="button" className={`icon-button ${listening ? "listening-button" : ""}`} onClick={speak} disabled={busy} aria-pressed={listening} aria-label={listening ? "Stop listening" : "Speak your prompt"} title={listening ? "Stop listening" : "Speak your prompt"}><Icon name="mic" size={17} /></button></div></div>
              {speechStatus && <p className="helper-text" role="status">{speechStatus}</p>}
              <section className="starter-section"><div className="section-label">Need a starting point?</div><div className="starter-list">{STARTERS.map((item) => <button className="starter-button" type="button" key={item.model_type} onClick={() => selectTemplate(item)} disabled={busy}><Icon name="cube" size={16} /><span>{item.title}</span><Icon name="arrow" size={14} /></button>)}</div><button type="button" className="text-button browse-button" onClick={() => setModal("templates")} disabled={busy}>Browse all templates<Icon name="arrow" size={14} /></button></section>
            </form>
          </div>
          <div id="adjust-panel" className="inspector-panel" role="tabpanel" aria-labelledby="adjust-tab" hidden={tab !== "adjust"}>
            {definitions.length ? <form id="adjust-form" ref={parametersForm} onSubmit={generate}>
              <details className="disclosure prompt-disclosure"><summary>Your prompt</summary><p>{prompt}</p><button type="button" className="text-button" onClick={() => setTab("describe")}>Edit description<Icon name="arrow" size={14} /></button></details>
              {!planCurrent && <p className="message message-warning">Your description or parser changed. Review it again to load matching dimensions.<button type="button" className="text-button" onClick={() => setTab("describe")}>Back to Describe</button></p>}
              {primaryDefinitions.length > 0 && <section className="parameter-section"><h2>Dimensions</h2>{primaryDefinitions.map(renderParameter)}</section>}
              {featureDefinitions.length > 0 && <section className="parameter-section"><h2>Features</h2>{featureDefinitions.map(renderParameter)}</section>}
              {advancedDefinitions.length > 0 && <details className="disclosure advanced-parameters"><summary>Advanced<span>{advancedDefinitions.length}</span></summary><div className="advanced-fields">{advancedDefinitions.map(renderParameter)}</div></details>}
              {plan.assumptions?.length > 0 && <details className="disclosure"><summary>Design assumptions</summary><ul className="detail-list">{plan.assumptions.map((item, index) => <li key={index}>{item}</li>)}</ul></details>}
            </form> : <div className="adjust-empty"><Icon name="tune" size={28} /><h2>A little detail goes a long way.</h2><p>Describe a part first, then fine-tune its dimensions and features here.</p><button className="button button-secondary" onClick={() => { setTab("describe"); requestAnimationFrame(() => promptRef.current?.focus()); }}>Describe a part<Icon name="arrow" size={15} /></button></div>}
          </div>
          <div className="inspector-footer">
            {error && <Messages title="Couldn't complete this request" items={[error]} />}
            <Messages title="Check your design" items={errors} />
            {tab === "describe" ? <><button className="button button-primary button-block" form="describe-form" type="submit" disabled={busy || listening || !prompt.trim()}>{busy ? <span className="spinner" /> : <Icon name="sparkle" size={17} />}{busy ? "Creating…" : "Create model"}{!busy && <Icon name="arrow" size={16} />}</button><button className="text-button review-button" onClick={reviewDimensions} disabled={busy || listening || !prompt.trim()}>Review dimensions first</button></> : definitions.length > 0 && <><button className="button button-primary button-block" type="submit" form="adjust-form" disabled={busy || !planCurrent}>{busy ? <span className="spinner" /> : <Icon name="cube" size={17} />}{busy ? "Updating…" : result ? "Update model" : "Generate model"}</button><p className="footer-note">{modelCurrent ? "Your model is up to date" : result ? "Apply changes to refresh the model" : "Generate to preview your design"}</p></>}
          </div>
        </aside>

        <section className="canvas-area" aria-label="Model preview" aria-busy={busy}>
          <div className="canvas-topline"><span className="canvas-label"><span className={`status-dot ${hasModel ? "is-ready" : ""}`} />{hasModel ? "3D preview" : "Your workspace"}</span><span className="canvas-units">mm</span></div>
          <div ref={mountRef} className="model-viewport" />
          {!hasModel && !busy && <div className="canvas-empty"><div className="empty-model"><Icon name="cube" size={78} /></div><h2>Your next idea, in 3D.</h2><p>Describe it. Refine it. Make it yours.</p><span className="empty-caption">Start with a prompt or pick a template</span></div>}
          {busy && <div className="canvas-progress" role="status"><span className="spinner" /><span>{stage}</span></div>}
          {(previewLoadError || previewError) && <div className="preview-notice" role="alert">{previewLoadError || previewError}</div>}
          {hasModel && !modelCurrent && !busy && <div className="stale-notice">Showing the last generated model</div>}
          <div className="canvas-bottomline"><p className="gesture-hint">Drag to orbit<span>·</span>Scroll to zoom</p><div className="view-toolbar"><button className="icon-button" onClick={() => fitView()} title="Reset view" aria-label="Reset view"><Icon name="home" /></button><button className="icon-button" onClick={() => fitView("front")} title="Front view" aria-label="Front view"><Icon name="cube" /></button><button className="icon-button" onClick={() => fitView("top")} title="Top view" aria-label="Top view"><Icon name="layers" /></button><span className="toolbar-divider" /><button className="icon-button" onClick={() => setShowGrid((current) => !current)} aria-label="Show grid" aria-pressed={showGrid} title="Toggle grid"><Icon name="grid" /></button><button className="icon-button" onClick={() => fitView()} title="Fit model" aria-label="Fit model"><Icon name="fit" /></button><button className="icon-button" onClick={() => setModal("view")} title="More view controls" aria-label="More view controls"><Icon name="tune" /></button></div></div>
        </section>
      </main>

      <footer className="statusbar"><button className="print-status" onClick={() => setModal("printability")}><Icon name={errors.length || warnings.length ? "alert" : modelCurrent ? "check" : "layers"} size={15} /><span>Printability</span><span className="status-separator" /><span className="status-text" aria-live="polite">{status}</span><Icon name="chevron" size={13} /></button><span className="statusbar-right">Built for making<span className="status-separator" />All dimensions in mm</span></footer>

      {modal === "settings" && <Modal title="Settings" onClose={() => setModal(null)}><section className="settings-section"><h3>Appearance</h3><p>Choose the theme that feels right for your workspace.</p><div className="theme-options">{["dark", "light"].map((item) => <button key={item} className={`theme-option ${theme === item ? "is-selected" : ""}`} aria-pressed={theme === item} onClick={() => setTheme(item)}><Icon name={item === "dark" ? "moon" : "sun"} /><span>{item === "dark" ? "Dark" : "Light"}</span>{theme === item && <Icon name="check" size={15} />}</button>)}</div><p className="helper-text">Dark by default. Your preference is saved on this device.</p></section><section className="settings-section"><h3>Design parser</h3><label className="switch-row"><span>Use local Ollama</span><input className="switch" type="checkbox" checked={useLlm} onChange={(event) => setUseLlm(event.target.checked)} disabled={busy} /></label><p className="helper-text">Uses your local model when available, with a fallback to the built-in parser.</p></section><div className="settings-credit">CadrixAI © 2026 Bhavyadeep Rao</div></Modal>}
      {modal === "templates" && <Modal title="Start from a template" wide onClose={() => setModal(null)}><div className="template-filters"><label className="sr-only" htmlFor="template-search">Search templates</label><input id="template-search" type="search" placeholder="Find a part…" value={templateQuery} onChange={(event) => setTemplateQuery(event.target.value)} /><label className="sr-only" htmlFor="template-category">Template category</label><select id="template-category" value={templateCategory} onChange={(event) => setTemplateCategory(event.target.value)}><option value="">All categories</option>{(caps?.categories || []).map((item) => <option key={item}>{item}</option>)}</select></div>{capsError ? <div className="empty-library"><p>{capsError}</p><button className="button button-secondary" onClick={refreshCapabilities}>Retry</button></div> : !caps ? <p className="helper-text" role="status">Loading templates…</p> : templates.length ? <div className="template-grid">{templates.map((item) => <button key={item.model_type} className="template-card" disabled={!item.implemented || busy} onClick={() => selectTemplate(item)}><span className="template-icon"><Icon name="cube" size={23} /></span><span className="template-card-title">{item.title}</span><span className="template-category">{item.category}{!item.implemented && " · Coming soon"}</span><span className="template-description">{item.description}</span><span className="template-use">Use template<Icon name="arrow" size={14} /></span></button>)}</div> : <p className="helper-text">No templates match. Try another search or category.</p>}</Modal>}
      {modal === "printability" && <Modal title="Printability & design details" onClose={() => setModal(null)}>{!summary ? <p className="helper-text">Generate a model to see its dimensions, printability checks, and any recommended adjustments.</p> : <><div className="print-summary"><Icon name={errors.length || warnings.length ? "alert" : modelCurrent ? "check" : "cube"} size={24} /><div><h3>{modelCurrent ? status : "Generate your changes to update checks"}</h3><p>{summary.title || readableName(summary.model_type)}</p></div>{modelCurrent && result.metadata?.printability_score !== undefined && <span className="score">{result.metadata.printability_score}<small>/100</small></span>}</div><Messages title="Validation errors" items={errors} /><Messages title="Print notes" items={warnings} warning />{modelCurrent && result.metadata?.estimated_dimensions_mm && <section className="settings-section"><h3>Estimated dimensions</h3><dl className="dimension-summary">{Object.entries(result.metadata.estimated_dimensions_mm).map(([key, value]) => <div key={key}><dt>{key.toUpperCase()}</dt><dd>{value} mm</dd></div>)}</dl></section>}{summary.assumptions?.length > 0 && <section className="settings-section"><h3>Assumptions</h3><ul className="detail-list">{summary.assumptions.map((item, index) => <li key={index}>{item}</li>)}</ul></section>}<details className="disclosure"><summary>Technical details</summary><h3>Structured intent</h3><pre>{JSON.stringify(summary.intent, null, 2)}</pre><h3>Resolved parameters</h3><pre>{JSON.stringify(summary.parameters, null, 2)}</pre></details></>}</Modal>}
      {modal === "view" && <Modal title="View controls" onClose={() => setModal(null)}><p className="helper-text">These controls change the preview only. Use Adjust to change exported geometry.</p><section className="settings-section"><h3>Rotation</h3><div className="rotation-fields">{["x", "y", "z"].map((axis) => <label key={axis} htmlFor={`rotation-${axis}`}>{axis.toUpperCase()}<div className="unit-input"><input id={`rotation-${axis}`} type="number" value={rotation[axis]} onChange={(event) => setRotation((current) => ({ ...current, [axis]: event.target.value }))} /><span>°</span></div></label>)}</div></section><section className="settings-section"><label htmlFor="preview-scale" className="section-label">Preview scale</label><div className="unit-input"><input id="preview-scale" type="number" min="0.1" max="10" step="0.05" value={scale} onChange={(event) => setScale(event.target.value === "" ? "" : Math.max(0.1, Math.min(10, Number(event.target.value))))} /><span>×</span></div></section><button className="button button-secondary" onClick={() => { setRotation({ x: 0, y: 0, z: 0 }); setScale(1); requestAnimationFrame(() => fitView()); }}>Reset preview</button><p className="helper-text">Drag to rotate · Right-drag to pan · Scroll or pinch to zoom</p></Modal>}
    </div>
  );
}
