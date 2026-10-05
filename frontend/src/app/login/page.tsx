"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * /login redirects to / — the auth form lives on the root page.
 * This is a client-side redirect so the static export works on Render.
 */
export default function LoginPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/");
  }, [router]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#020617",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ color: "#94a3b8", fontSize: "14px" }}>Redirecting...</div>
    </div>
  );
}
