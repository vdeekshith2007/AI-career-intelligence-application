"use client";

import Home from "../page";

/**
 * /login serves the full auth UI directly.
 * With trailingSlash:false, Next.js generates login.html which Render
 * serves natively at /login — no redirect needed.
 */
export default function LoginPage() {
  return <Home />;
}
