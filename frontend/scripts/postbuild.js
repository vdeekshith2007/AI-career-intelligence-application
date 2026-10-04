const fs = require("fs");
const path = require("path");

const outDir = path.join(__dirname, "..", "out");
const distDir = path.join(__dirname, "..", "dist");
const buildDir = path.join(__dirname, "..", "build");

try {
  if (fs.existsSync(outDir)) {
    fs.cpSync(outDir, distDir, { recursive: true, force: true });
    fs.cpSync(outDir, buildDir, { recursive: true, force: true });
    console.log("[Postbuild] Successfully synced out/ to dist/ and build/");
  }
} catch (err) {
  console.warn("[Postbuild] Warning while copying build artifacts:", err.message);
}
