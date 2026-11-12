import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const backend = join(root, "backend");
const frontend = join(root, "frontend");
const windows = process.platform === "win32";
const children = new Set();
let stopping = false;

function stop(exitCode = 0) {
  if (stopping) return;
  stopping = true;
  process.exitCode = exitCode;
  for (const child of children) {
    if (!child.pid) continue;
    if (windows) {
      // uv and Vite may own subprocesses; terminate the entire service tree.
      spawnSync("taskkill", ["/pid", String(child.pid), "/t", "/f"], {
        stdio: "ignore",
        windowsHide: true,
      });
    } else {
      try {
        process.kill(-child.pid, "SIGTERM");
      } catch (error) {
        if (error.code !== "ESRCH") console.error(error.message);
      }
    }
  }
}

function launch(command, args, cwd, label, service = true) {
  const child = spawn(command, args, {
    cwd,
    stdio: "inherit",
    detached: !windows,
    windowsHide: true,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
  });
  children.add(child);
  child.on("error", (error) => {
    console.error(`${label}: ${error.message}`);
    stop(1);
  });
  child.on("exit", (code, signal) => {
    if (!stopping && (service || code !== 0)) {
      console.error(`${label} exited (${signal || code}). Stopping both services.`);
      stop(code || 1);
    }
    children.delete(child);
  });
  return child;
}

function runSetup(command, args, cwd, label) {
  const child = launch(command, args, cwd, label, false);
  return new Promise((resolve, reject) => {
    child.once("error", reject);
    child.once("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${label} failed.`));
    });
  });
}

async function ensureBackend() {
  const pythonVersion = (await readFile(join(backend, ".python-version"), "utf8")).trim();
  if (!pythonVersion) throw new Error("backend/.python-version must specify a Python version.");

  console.log(`Preparing backend with Python ${pythonVersion}...`);
  // uv run can trust an existing venv whose base interpreter was removed.
  // Restore the pinned runtime first; this is a no-op when it is installed.
  // Keep the user's default Python, PATH, and registry registrations unchanged.
  await runSetup("uv", ["python", "install", pythonVersion, "--no-bin", "--no-registry"], backend, "Backend Python setup");
  if (!stopping) {
    await runSetup("uv", ["sync", "--locked", "--python", pythonVersion], backend, "Backend dependency setup");
  }
}

async function ensureFrontend() {
  const fingerprint = createHash("sha256")
    .update(await readFile(join(frontend, "package.json")))
    .update(await readFile(join(frontend, "package-lock.json")))
    .update(`${process.platform}:${process.arch}:${process.versions.node.split(".")[0]}`)
    .digest("hex");
  const marker = join(frontend, "node_modules", ".cadrix-install");
  const require = createRequire(join(frontend, "package.json"));
  try {
    if ((await readFile(marker, "utf8")) === fingerprint) {
      require.resolve("vite");
      require.resolve("react");
      require.resolve("three");
      return;
    }
  } catch {
    // A fresh checkout or a different platform needs a local npm install.
  }

  console.log("Installing frontend dependencies from package-lock.json...");
  // npm_execpath lets npm run dev work on Windows without a shell wrapper.
  const npmCli = process.env.npm_execpath;
  if (!npmCli) throw new Error("Start the project with npm run dev (or npm start).");
  await runSetup(process.execPath, [npmCli, "ci", "--no-audit", "--no-fund"], frontend, "Frontend setup");
  if (!stopping) await writeFile(marker, fingerprint);
}

process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());

try {
  const uv = spawnSync("uv", ["--version"], { stdio: "ignore", windowsHide: true });
  if (uv.error || uv.status !== 0) {
    throw new Error("uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/ and reopen your terminal.");
  }
  await ensureBackend();
  if (!stopping) await ensureFrontend();
  if (!stopping) {
    console.log("Starting CadrixAI: frontend http://localhost:5173 | backend http://localhost:8000");
    console.log("Press Ctrl+C to stop both services.");
    launch("uv", ["run", "--locked", "python", "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], backend, "Backend");
    launch(process.execPath, [join(frontend, "node_modules", "vite", "bin", "vite.js"), "--host", "127.0.0.1", "--port", "5173", "--strictPort"], frontend, "Frontend");
  }
} catch (error) {
  console.error(error.message);
  stop(1);
}
