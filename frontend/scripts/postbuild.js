const fs = require("fs");
const path = require("path");

const outDir = path.join(__dirname, "..", "out");
const distDir = path.join(__dirname, "..", "dist");
const buildDir = path.join(__dirname, "..", "build");

// ── 1. Flatten Next.js App Router directory-based HTML files ─────────────────
// App Router static export always outputs page/index.html, even with
// trailingSlash:false. Render static hosting needs flat page.html files.
// This copies:  out/login/index.html  →  out/login.html
//               out/404/index.html   →  out/404.html  (already exists but sync)
if (fs.existsSync(outDir)) {
  const entries = fs.readdirSync(outDir, { withFileTypes: true });
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    // Skip Next.js internal dirs
    if (entry.name.startsWith("_") || entry.name === "api") continue;

    const nestedIndex = path.join(outDir, entry.name, "index.html");
    const flatHtml = path.join(outDir, `${entry.name}.html`);

    if (fs.existsSync(nestedIndex) && !fs.existsSync(flatHtml)) {
      fs.copyFileSync(nestedIndex, flatHtml);
      console.log(`[Postbuild] Flattened: out/${entry.name}/index.html → out/${entry.name}.html`);
    }
  }
}

// ── 2. Sync out/ to dist/ and build/ for other hosting platforms ─────────────
try {
  if (fs.existsSync(outDir)) {
    fs.cpSync(outDir, distDir, { recursive: true, force: true });
    fs.cpSync(outDir, buildDir, { recursive: true, force: true });
    console.log("[Postbuild] Successfully synced out/ to dist/ and build/");
  }
} catch (err) {
  console.warn("[Postbuild] Warning while copying build artifacts:", err.message);
}
