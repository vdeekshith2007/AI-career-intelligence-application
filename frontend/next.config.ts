import type { NextConfig } from "next";

// In production (Docker/Render/Railway), NEXT_PUBLIC_API_URL points to the deployed backend.
// In local dev, the Next.js rewrite proxies /api/v1/* to the local FastAPI.
const BACKEND_URL =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000/api/v1";

// Strip trailing /api/v1 if present so we can construct the right destination
const BACKEND_BASE = BACKEND_URL.replace(/\/api\/v1\/?$/, "");

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_BASE}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
