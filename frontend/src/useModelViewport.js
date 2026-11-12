import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

function disposeObject(object) {
  object.traverse((child) => {
    child.geometry?.dispose();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    materials.forEach((material) => material?.dispose());
  });
}

export default function useModelViewport({ theme, showGrid, rotation, scale }) {
  const mountRef = useRef(null);
  const viewport = useRef(null);
  const lastPreviewUrl = useRef(null);
  const [previewError, setPreviewError] = useState("");
  const [hasModel, setHasModel] = useState(false);
  const transforms = useRef({ rotation, scale });
  transforms.current = { rotation, scale };

  function fitView(direction = "iso") {
    const state = viewport.current;
    if (!state) return;
    const { camera, controls, model } = state;
    const box = model ? new THREE.Box3().setFromObject(model) : null;
    const center = box ? box.getCenter(new THREE.Vector3()) : new THREE.Vector3();
    const size = box ? box.getSize(new THREE.Vector3()) : new THREE.Vector3(1, 1, 1);
    const maxDim = Math.max(size.x, size.y, size.z, 0.01);
    // Fit both portrait and landscape canvases instead of cropping narrow views.
    const distance = maxDim / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * Math.max(1, 1 / camera.aspect) * 1.8;
    const offset = direction === "top" ? new THREE.Vector3(0, 1, 0.001) : direction === "front" ? new THREE.Vector3(0, 0.2, 1) : new THREE.Vector3(1, 0.75, 1);
    camera.near = Math.max(0.001, maxDim / 100);
    camera.far = Math.max(100, distance * 20);
    controls.maxDistance = Math.max(50, distance * 10);
    camera.position.copy(center).add(offset.normalize().multiplyScalar(distance));
    controls.target.copy(center);
    camera.updateProjectionMatrix();
    controls.update();
  }

  function applyTransforms() {
    const model = viewport.current?.model;
    if (!model) return;
    const { rotation: angles, scale: multiplier } = transforms.current;
    model.rotation.set(...["x", "y", "z"].map((axis) => THREE.MathUtils.degToRad(Number(angles[axis]) || 0)));
    model.scale.setScalar(model.userData.baseScale * (Number(multiplier) || 1));
    model.updateWorldMatrix(true, true);
  }

  useEffect(() => {
    const mount = mountRef.current;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.001, 1000);
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setPreviewError("3D preview is unavailable in this browser. You can still generate and export your model.");
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.domElement.setAttribute("aria-label", "Interactive 3D model. Drag to rotate, right-drag to pan, and scroll to zoom.");
    mount.appendChild(renderer.domElement);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x68758a, 2.4));
    const light = new THREE.DirectionalLight(0xffffff, 2.6);
    light.position.set(3, 5, 4);
    scene.add(light);
    const grid = new THREE.GridHelper(8, 40);
    scene.add(grid);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 0.15;
    viewport.current = { scene, camera, renderer, controls, grid, model: null };
    const resize = () => {
      const width = Math.max(mount.clientWidth, 1);
      const height = Math.max(mount.clientHeight, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    resize();
    fitView();
    renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
    setHasModel(false);
    // Restore the preview if development hot reload recreates the WebGL context.
    if (lastPreviewUrl.current) loadPreview(lastPreviewUrl.current).catch(() => setPreviewError("Couldn't reload the preview. Generate the model again or export its files."));
    return () => {
      observer.disconnect();
      renderer.setAnimationLoop(null);
      controls.dispose();
      disposeObject(scene);
      renderer.dispose();
      renderer.domElement.remove();
      viewport.current = null;
    };
  }, []);

  useEffect(() => {
    const grid = viewport.current?.grid;
    if (!grid) return;
    grid.visible = showGrid;
    const material = grid.material;
    material.transparent = true;
    material.opacity = theme === "dark" ? 0.055 : 0.09;
    material.depthWrite = false;
    const colors = grid.geometry.getAttribute("color");
    const color = new THREE.Color(theme === "dark" ? "#8495b1" : "#7b8ba3");
    for (let index = 0; index < colors.count; index++) colors.setXYZ(index, color.r, color.g, color.b);
    colors.needsUpdate = true;
  }, [theme, showGrid]);

  useEffect(() => { applyTransforms(); }, [rotation.x, rotation.y, rotation.z, scale]);

  async function loadPreview(url) {
    if (!viewport.current) return;
    setPreviewError("");
    const gltf = await new GLTFLoader().loadAsync(url);
    const state = viewport.current;
    if (!state) { disposeObject(gltf.scene); return; }
    const mesh = gltf.scene;
    mesh.rotation.x = -Math.PI / 2;
    mesh.updateWorldMatrix(true, true);
    const box = new THREE.Box3().setFromObject(mesh);
    const center = box.getCenter(new THREE.Vector3());
    mesh.position.set(-center.x, -box.min.y, -center.z);
    const model = new THREE.Group();
    model.add(mesh);
    model.updateWorldMatrix(true, true);
    const size = new THREE.Box3().setFromObject(model).getSize(new THREE.Vector3());
    model.userData.baseScale = 1.8 / (Math.max(size.x, size.y, size.z) || 1);
    if (state.model) { state.scene.remove(state.model); disposeObject(state.model); }
    state.model = model;
    state.scene.add(model);
    applyTransforms();
    fitView();
    lastPreviewUrl.current = url;
    setHasModel(true);
  }

  return { mountRef, hasModel, previewError, loadPreview, fitView };
}
