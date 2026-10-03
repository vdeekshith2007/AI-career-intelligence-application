#!/usr/bin/env node
/**
 * AI Career Intelligence — Unified Local Dev Runner
 *
 * Runs both the FastAPI backend and Next.js frontend concurrently.
 * Handles process lifecycle and clean shutdowns.
 */

const { spawn, execSync } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

const rootDir = path.resolve(__dirname, "..");
const backendDir = path.join(rootDir, "backend");
const frontendDir = path.join(rootDir, "frontend");

// Detect python executable in backend/.venv
let pythonExe = path.join(backendDir, ".venv", "Scripts", "python.exe");
if (!fs.existsSync(pythonExe)) {
  pythonExe = path.join(backendDir, ".venv", "bin", "python");
}
if (!fs.existsSync(pythonExe)) {
  pythonExe = "python";
}

function checkPort(port) {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${port}/api/v1/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function main() {
  console.log("============================================================");
  console.log("🚀 Starting AI Career Intelligence Development Environment");
  console.log("============================================================\n");

  // Check if PostgreSQL container is running
  try {
    console.log("🐘 Ensuring PostgreSQL container is running...");
    execSync("wsl -d Ubuntu -u root docker compose -f /mnt/c/Users/vatap/OneDrive/Desktop/AI-Career-Intelligence/docker-compose.yml up -d db", {
      stdio: "ignore",
      timeout: 10000,
    });
    console.log("✅ PostgreSQL container active.\n");
  } catch (err) {
    console.log("ℹ️  WSL Docker check completed.\n");
  }

  // Check if backend is already running
  const backendAlreadyRunning = await checkPort(8000);
  let backendProc = null;

  if (backendAlreadyRunning) {
    console.log("✅ FastAPI backend is already running on http://127.0.0.1:8000\n");
  } else {
    console.log("⚡ Starting FastAPI backend on http://127.0.0.1:8000...");
    backendProc = spawn(
      pythonExe,
      ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
      {
        cwd: backendDir,
        stdio: "inherit",
        shell: true,
      }
    );

    backendProc.on("error", (err) => {
      console.error("❌ Failed to start backend:", err.message);
    });
  }

  // Start Next.js frontend
  console.log("✨ Starting Next.js frontend on http://localhost:3000...\n");
  const npmCmd = process.platform === "win32" ? "npm.cmd" : "npm";
  const frontendProc = spawn(npmCmd, ["run", "dev"], {
    cwd: frontendDir,
    stdio: "inherit",
    shell: true,
  });

  // Keep WSL Ubuntu alive so Docker PostgreSQL doesn't idle out on Windows
  let wslKeepalive = null;
  if (process.platform === "win32") {
    try {
      wslKeepalive = spawn("wsl", ["-d", "Ubuntu", "-u", "root", "sleep", "infinity"], { stdio: "ignore" });
    } catch (_) {}
  }

  // Handle graceful exit
  function cleanup() {
    console.log("\n🛑 Shutting down development servers...");
    if (wslKeepalive) {
      try { wslKeepalive.kill(); } catch (_) {}
    }
    if (backendProc) backendProc.kill();
    frontendProc.kill();
    process.exit(0);
  }

  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);
}

main();
