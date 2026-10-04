"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  api,
  UserProfile,
  ResumeItem,
  ATSScoreData,
  JobItem,
  ChatSessionItem,
  ChatMessageItem,
  ApiTraceRecord,
} from "@/lib/api";

// ── Score Circle SVG Component ────────────────────────────────────────────────
function ScoreCircle({ score, size = 90, label }: { score: number; size?: number; label?: string }) {
  const radius = (size - 10) / 2;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;
  const color = score >= 75 ? "#34d399" : score >= 50 ? "#f59e0b" : "#f87171";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
      <div style={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#1e293b" strokeWidth={8} />
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth={8}
            strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 1s ease" }} />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: "1.4rem", fontWeight: 800, color, lineHeight: 1 }}>{score}</span>
          {label && <span style={{ fontSize: "9px", color: "#94a3b8", marginTop: "2px" }}>{label}</span>}
        </div>
      </div>
    </div>
  );
}

// ── Animated Progress Bar ─────────────────────────────────────────────────────
function ProgressBar({ value, color = "bg-indigo-500", label, showValue = true }: {
  value: number; color?: string; label?: string; showValue?: boolean;
}) {
  return (
    <div>
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-1">
          {label && <span className="text-xs text-slate-400">{label}</span>}
          {showValue && <span className="text-xs font-bold text-slate-300">{Math.round(value)}%</span>}
        </div>
      )}
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${Math.min(value, 100)}%`, transition: "width 0.8s ease" }} />
      </div>
    </div>
  );
}

// ── Skill Badge ───────────────────────────────────────────────────────────────
function SkillBadge({ skill, variant = "default" }: { skill: string; variant?: "default" | "match" | "missing" }) {
  const cls = {
    default: "bg-indigo-950/60 border-indigo-800/40 text-indigo-300",
    match: "bg-emerald-950/60 border-emerald-700/40 text-emerald-300",
    missing: "bg-rose-950/60 border-rose-700/40 text-rose-300",
  }[variant];
  return (
    <span className={`px-2.5 py-1 rounded-md border text-xs font-medium ${cls}`}>
      {variant === "match" && "✓ "}{variant === "missing" && "! "}{skill}
    </span>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color, icon }: { label: string; value: string | number; sub?: string; color: string; icon: string }) {
  return (
    <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</div>
          <div className={`text-3xl font-extrabold mt-2 ${color}`}>{value}</div>
          {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
        </div>
        <div className="text-2xl opacity-40">{icon}</div>
      </div>
    </div>
  );
}

export default function Home() {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("vataparthideekshith18@gmail.com");
  const [authPassword, setAuthPassword] = useState("Deekshith@807");
  const [authFullName, setAuthFullName] = useState("Vataparthi Deekshith");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"dashboard" | "resumes" | "jobs" | "chat" | "tracer">("dashboard");
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [atsScore, setAtsScore] = useState<ATSScoreData | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const selectedResume = resumes.find((r) => r.id === selectedResumeId);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [recommendedJobs, setRecommendedJobs] = useState<JobItem[]>([]);
  const [jobQuery, setJobQuery] = useState("");
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobTypeFilter, setJobTypeFilter] = useState("all");
  const [jobLevelFilter, setJobLevelFilter] = useState("all");
  const [chatSessions, setChatSessions] = useState<ChatSessionItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [traceLogs, setTraceLogs] = useState<ApiTraceRecord[]>([]);
  const [isTracing, setIsTracing] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline" | "waking">("checking");
  const [backendWaking, setBackendWaking] = useState(false);

  useEffect(() => {
    setMounted(true);
    try {
      const t = localStorage.getItem("ai_career_token");
      if (t) setToken(t);
    } catch {}
    // Warm up backend — Render free tier sleeps after 15min of inactivity.
    // We ping with a timeout; if it fails, mark as waking and retry.
    const warmup = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 8000);
        const r = await fetch(`${api.getBaseUrl()}/health`, { signal: controller.signal });
        clearTimeout(timeout);
        setApiStatus(r.ok ? "online" : "offline");
      } catch {
        // Backend likely in cold sleep — start wake-up and retry in 55s
        setApiStatus("waking");
        setBackendWaking(true);
        setTimeout(async () => {
          try {
            const r = await fetch(`${api.getBaseUrl()}/health`);
            setApiStatus(r.ok ? "online" : "offline");
          } catch {
            setApiStatus("offline");
          } finally {
            setBackendWaking(false);
          }
        }, 55000);
      }
    };
    void warmup();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleLogout = useCallback(async () => {
    if (token) { try { await api.logout(token); } catch {} }
    setToken(null); setCurrentUser(null); setResumes([]); setJobs([]);
    setRecommendedJobs([]); setChatSessions([]); setMessages([]); setAtsScore(null);
    try { localStorage.removeItem("ai_career_token"); } catch {}
  }, [token]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    const init = async () => {
      setJobsLoading(true);
      try {
        // Authenticate user identity first
        const user = await api.getMe(token);
        if (!active) return;
        setCurrentUser(user);

        // Load dashboard and auxiliary data resiliently
        const [resumesRes, jobsRes, recsRes, sessionsRes] = await Promise.allSettled([
          api.listResumes(token),
          api.listJobs(token),
          api.getJobRecommendations(token),
          api.listChatSessions(token),
        ]);
        if (!active) return;

        if (resumesRes.status === "fulfilled") setResumes(resumesRes.value);
        if (jobsRes.status === "fulfilled") setJobs(jobsRes.value);
        if (recsRes.status === "fulfilled") setRecommendedJobs(recsRes.value);
        if (sessionsRes.status === "fulfilled") {
          const sessions = sessionsRes.value;
          setChatSessions(sessions);
          if (sessions.length > 0) {
            setCurrentSessionId(sessions[0].id);
            try {
              const h = await api.getChatHistory(token, sessions[0].id);
              if (active) setMessages(h.messages);
            } catch {}
          }
        }
      } catch {
        if (active) {
          // Only clear session if getMe failed (invalid/expired token)
          setToken(null);
          setCurrentUser(null);
          try { localStorage.removeItem("ai_career_token"); } catch {}
        }
      } finally {
        if (active) setJobsLoading(false);
      }
    };
    void init();
    return () => { active = false; };
  }, [token]);

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setAuthLoading(true); setAuthError(null);
    console.log(`[Auth] Submitting ${authMode} for: ${authEmail}`);

    const attemptLogin = async () => {
      if (authMode === "register") {
        console.log("[Auth] Registering user...");
        await api.register({ email: authEmail, password: authPassword, full_name: authFullName });
      }
      console.log("[Auth] Authenticating with backend...");
      const tokenRes = await api.login({ email: authEmail, password: authPassword });
      console.log("[Auth] Token received successfully.");
      setToken(tokenRes.access_token);
      localStorage.setItem("ai_career_token", tokenRes.access_token);
      console.log("[Auth] Loading user profile...");
      const user = await api.getMe(tokenRes.access_token);
      setCurrentUser(user);
      console.log(`[Auth] Logged in successfully as ${user.email} (${user.role})`);
    };

    try {
      await attemptLogin();
    } catch (err: unknown) {
      const errMsg = (err as { message?: string })?.message || "";
      // Auto-retry once if backend was cold-sleeping (Failed to fetch / network error)
      if (errMsg.toLowerCase().includes("failed to fetch") || errMsg.toLowerCase().includes("unable to connect") || (err as { status?: number })?.status === 0) {
        console.warn("[Auth] Backend cold start detected, waiting 60s then retrying...");
        setApiStatus("waking");
        setBackendWaking(true);
        setAuthError("⏳ Backend is waking up from sleep (Render free tier). Auto-retrying in ~60 seconds...");
        await new Promise(resolve => setTimeout(resolve, 62000));
        setAuthError(null);
        setBackendWaking(false);
        try {
          await attemptLogin();
          setApiStatus("online");
        } catch (retryErr: unknown) {
          const retryMsg = (retryErr as { message?: string })?.message || "Authentication failed.";
          console.error("[Auth] Retry also failed:", retryMsg);
          setAuthError(retryMsg);
          setApiStatus("offline");
        }
      } else {
        console.error("[Auth] Authentication error:", errMsg, err);
        setAuthError(errMsg || "Authentication failed.");
      }
    } finally {
      setAuthLoading(false);
    }
  };

  const handleAnalyzeResume = async (resumeId: string) => {
    if (!token) return;
    setResumeLoading(true);
    try { const a = await api.analyzeResume(token, resumeId); setAtsScore(a); }
    catch (err: unknown) { setUploadStatus(`Analysis error: ${(err as { message?: string })?.message || "failed"}`); }
    finally { setResumeLoading(false); }
  };

  const processFile = async (file: File) => {
    if (!token) return;
    if (!file.name.match(/\.(pdf|docx)$/i)) { setUploadStatus("Only PDF and DOCX accepted."); return; }
    setUploadStatus("Uploading and parsing resume...");
    try {
      const u = await api.uploadResume(token, file);
      setUploadStatus(`Uploaded "${u.original_filename}" successfully!`);
      const list = await api.listResumes(token); setResumes(list);
      setSelectedResumeId(u.id);
      await handleAnalyzeResume(u.id);
    } catch (err: unknown) { setUploadStatus(`Upload failed: ${(err as { message?: string })?.message || "error"}`); }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]; if (f) await processFile(f);
  };
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false);
    const f = e.dataTransfer.files[0]; if (f) await processFile(f);
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !token || !currentSessionId) return;
    const userText = inputMessage.trim(); setInputMessage(""); setChatLoading(true);
    setMessages((prev) => [...prev, { id: "tmp-" + Date.now(), role: "user", content: userText, created_at: new Date().toISOString() }]);
    try {
      const bot = await api.sendChatMessage(token, currentSessionId, userText);
      setMessages((prev) => [...prev, bot]);
    } catch (err: unknown) {
      setMessages((prev) => [...prev, {
        id: "err-" + Date.now(), role: "assistant",
        content: `Error: ${(err as { message?: string })?.message || "failed"}`,
        created_at: new Date().toISOString()
      }]);
    } finally { setChatLoading(false); }
  };

  const displayJobs = (recommendedJobs.length > 0 ? recommendedJobs : jobs).filter((j) => {
    const q = !jobQuery || j.title.toLowerCase().includes(jobQuery.toLowerCase()) || j.company.toLowerCase().includes(jobQuery.toLowerCase());
    const t = jobTypeFilter === "all" || j.work_type === jobTypeFilter;
    const l = jobLevelFilter === "all" || j.experience_level === jobLevelFilter;
    return q && t && l;
  });

  const runLiveIntegrationTrace = async () => {
    setIsTracing(true);
    const records: ApiTraceRecord[] = [];
    const trace = async <T,>(step: string, endpoint: string, method: string, fn: () => Promise<T>): Promise<T> => {
      const start = performance.now();
      try {
        const r = await fn();
        records.push({ step, endpoint, method, status: 200, durationMs: Math.round(performance.now() - start), ok: true, details: r });
        setTraceLogs([...records]); return r;
      } catch (err: unknown) {
        const e = err as { status?: number; detail?: unknown; message?: string };
        records.push({ step, endpoint, method, status: e.status || 500, durationMs: Math.round(performance.now() - start), ok: false, details: e.detail || e.message });
        setTraceLogs([...records]); throw err;
      }
    };
    try {
      const email = `test_${Date.now()}@integration.com`, pass = "Password123!";
      await trace("API Health", "/health", "GET", async () => (await fetch(`${api.getBaseUrl()}/health`)).json());
      await trace("Register", "/auth/register", "POST", () => api.register({ email, password: pass, full_name: "Integration User" }));
      const { access_token } = await trace("Login", "/auth/login", "POST", () => api.login({ email, password: pass }));
      await trace("Get Me", "/auth/me", "GET", () => api.getMe(access_token));
      await trace("Update Profile", "/users/profile", "PUT", () => api.updateProfile(access_token, { full_name: "Verified User" }));
      const fakeFile = new File(["Senior Software Engineer\nSkills: Python, FastAPI, React, Docker, AWS, Kubernetes\n5 years experience"], "resume.pdf", { type: "application/pdf" });
      const uploaded = await trace("Upload Resume", "/resumes/upload", "POST", () => api.uploadResume(access_token, fakeFile));
      await trace("ATS Analysis", `/resumes/${uploaded.id}/analyze`, "POST", () => api.analyzeResume(access_token, uploaded.id));
      await trace("Job Recommendations", "/jobs/recommendations", "GET", () => api.getJobRecommendations(access_token));
      const sess = await trace("Create Chat Session", "/chat/sessions", "POST", () => api.createChatSession(access_token, "E2E Test"));
      await trace("Send Message", `/chat/sessions/${sess.id}/messages`, "POST", () => api.sendChatMessage(access_token, sess.id, "What jobs match my Python skills?"));
      await trace("Logout", "/auth/logout", "POST", () => api.logout(access_token));
    } catch {} finally { setIsTracing(false); }
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-indigo-600 via-violet-600 to-cyan-400 flex items-center justify-center animate-pulse">
            <span className="font-extrabold text-white text-2xl">CI</span>
          </div>
          <p className="text-sm text-slate-400">Loading AI Career Intelligence...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/70 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-violet-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <span className="font-extrabold text-white text-lg">CI</span>
            </div>
            <div className="hidden sm:block">
              <span className="font-bold text-lg bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">AI Career Intelligence</span>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">v1.0</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${
                  apiStatus === "online" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                  apiStatus === "offline" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" :
                  apiStatus === "waking" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                  "bg-slate-700/50 text-slate-400 border-slate-700"}`}>
                  {apiStatus === "checking" ? "⟳ Checking" :
                   apiStatus === "online" ? "● API Online" :
                   apiStatus === "waking" ? "⟳ API Waking..." :
                   "● API Offline"}
                </span>
              </div>
            </div>
          </div>
          {token && (
            <nav className="flex gap-0.5 bg-slate-800/60 p-1 rounded-xl border border-slate-700/50 overflow-x-auto">
              {([
                { id: "dashboard", label: "Dashboard", icon: "⚡" },
                { id: "resumes", label: "Resume ATS", icon: "📄" },
                { id: "jobs", label: "Job Matcher", icon: "🎯" },
                { id: "chat", label: "AI Advisor", icon: "💬" },
                { id: "tracer", label: "Diagnostics", icon: "🔍" },
              ] as const).map((tab) => (
                <button key={tab.id} id={`tab-${tab.id}`} onClick={() => setActiveTab(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap flex items-center gap-1.5 ${activeTab === tab.id ? "bg-indigo-600 text-white shadow-sm" : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"}`}>
                  <span>{tab.icon}</span><span className="hidden md:inline">{tab.label}</span>
                </button>
              ))}
            </nav>
          )}
          <div className="flex items-center gap-3 flex-shrink-0">
            {currentUser ? (
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-sm">
                  {currentUser.full_name.charAt(0).toUpperCase()}
                </div>
                <div className="hidden sm:block">
                  <div className="text-sm font-semibold text-slate-200">{currentUser.full_name}</div>
                  <div className="text-[10px] text-indigo-400">{currentUser.role.toUpperCase()}</div>
                </div>
                <button id="btn-logout" onClick={handleLogout}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-rose-900/50 text-slate-300 hover:text-rose-300 border border-slate-700 transition cursor-pointer">
                  Sign Out
                </button>
              </div>
            ) : authLoading ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium">
                <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse"></span>
                <span>Signing In...</span>
              </div>
            ) : (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/40 border border-slate-700/50 text-xs text-slate-400">
                <span className="h-1.5 w-1.5 rounded-full bg-slate-500"></span>
                <span>Secure Portal</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 lg:p-8">
        {!token ? (
          /* Auth Screen */
          <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center">
            <div className="w-full max-w-md">
              <div className="text-center mb-8">
                <div className="inline-flex h-16 w-16 rounded-2xl bg-gradient-to-tr from-indigo-600 via-violet-600 to-cyan-400 items-center justify-center shadow-xl shadow-indigo-600/30 mb-4">
                  <span className="text-3xl font-extrabold text-white">CI</span>
                </div>
                <h1 className="text-3xl font-extrabold text-white mb-2">{authMode === "login" ? "Welcome Back" : "Get Started"}</h1>
                <p className="text-sm text-slate-400">{authMode === "login" ? "Access your AI-powered career analytics." : "Start analyzing resumes and matching jobs."}</p>
              </div>
              <div className="p-8 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-2xl backdrop-blur-xl">
                {authMode === "login" && (
                  <div className="mb-5 p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs">
                    <span className="font-semibold text-indigo-200">🔑 Demo credentials pre-filled.</span>{" "}
                    Hit Sign In to explore the platform, or register a new account.
                  </div>
                )}
                {authError && (
                  <div className="mb-5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex gap-2">
                    <span>⚠️</span><span>{authError}</span>
                  </div>
                )}
                <form onSubmit={handleAuthSubmit} className="space-y-4">
                  {authMode === "register" && (
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">Full Name</label>
                      <input id="input-fullname" type="text" required value={authFullName} onChange={(e) => setAuthFullName(e.target.value)}
                        className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none transition" placeholder="Jane Doe" />
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">Email Address</label>
                    <input id="input-email" type="email" required value={authEmail} onChange={(e) => setAuthEmail(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none transition" placeholder="name@company.com" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">Password</label>
                    <input id="input-password" type="password" required value={authPassword} onChange={(e) => setAuthPassword(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none transition" placeholder="••••••••" />
                  </div>
                  <button id="btn-auth-submit" type="submit" disabled={authLoading}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-sm transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50 cursor-pointer mt-2">
                    {authLoading ? "Authenticating..." : authMode === "login" ? "Sign In" : "Create Account"}
                  </button>
                </form>
                <div className="mt-5 text-center text-xs text-slate-400">
                  {authMode === "login" ? (
                    <span>No account?{" "}<button id="btn-switch-register" onClick={() => { setAuthMode("register"); setAuthError(null); }} className="text-indigo-400 hover:underline font-semibold cursor-pointer">Register</button></span>
                  ) : (
                    <span>Have an account?{" "}<button id="btn-switch-login" onClick={() => { setAuthMode("login"); setAuthError(null); }} className="text-indigo-400 hover:underline font-semibold cursor-pointer">Sign In</button></span>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-5">
                {[{ icon: "📄", label: "Resume ATS" }, { icon: "🎯", label: "Job Matching" }, { icon: "🤖", label: "AI Advisor" }].map((f) => (
                  <div key={f.label} className="p-3 rounded-xl bg-slate-900/50 border border-slate-800 text-center">
                    <div className="text-xl mb-1">{f.icon}</div>
                    <div className="text-xs text-slate-400 font-medium">{f.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div>
            {/* Dashboard */}
            {activeTab === "dashboard" && (
              <div className="space-y-6">
                <div className="p-6 rounded-2xl bg-gradient-to-r from-indigo-950/80 via-slate-900 to-violet-950/60 border border-indigo-900/40 flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-extrabold text-white mb-1">Welcome back, {currentUser?.full_name}!</h2>
                    <p className="text-sm text-slate-400">Your AI-powered career intelligence platform.</p>
                  </div>
                  <button onClick={() => setActiveTab("resumes")} className="hidden md:block px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition cursor-pointer">Upload Resume</button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard label="Resumes" value={resumes.length} sub="Uploaded" color="text-indigo-400" icon="📄" />
                  <StatCard label="ATS Score" value={atsScore ? `${Math.round(atsScore.overall_score)}%` : "—"} sub="Latest" color="text-emerald-400" icon="✅" />
                  <StatCard label="Job Matches" value={jobs.length} sub="Active roles" color="text-cyan-400" icon="🎯" />
                  <StatCard label="AI Sessions" value={chatSessions.length} sub="Career chats" color="text-violet-400" icon="💬" />
                </div>
                {atsScore && (
                  <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800">
                    <h3 className="text-base font-bold text-white mb-5 flex items-center gap-2">📊 Latest ATS Analysis <span className="text-xs font-normal text-slate-400">— {selectedResume?.original_filename}</span></h3>
                    <div className="flex flex-col md:flex-row items-center gap-6">
                      <ScoreCircle score={Math.round(atsScore.overall_score)} size={100} label="Overall" />
                      <div className="flex-1 grid grid-cols-2 gap-3 w-full">
                        <ProgressBar value={atsScore.keyword_score ?? 0} label="Keywords" color="bg-cyan-500" />
                        <ProgressBar value={atsScore.format_score ?? 0} label="Formatting" color="bg-emerald-500" />
                        <ProgressBar value={atsScore.experience_score ?? 0} label="Experience" color="bg-amber-500" />
                        <ProgressBar value={atsScore.impact_score ?? 0} label="Impact" color="bg-violet-500" />
                      </div>
                    </div>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { tab: "resumes" as const, icon: "📄", title: "Resume ATS Analyzer", desc: "Upload PDF/DOCX for ATS scores, keyword analysis, and improvement tips.", border: "hover:border-indigo-500/50" },
                    { tab: "jobs" as const, icon: "🎯", title: "AI Job Recommendations", desc: "Explore AI-matched roles ranked by skills and experience fit.", border: "hover:border-cyan-500/50" },
                    { tab: "chat" as const, icon: "🤖", title: "AI Career Advisor", desc: "Get personalized career guidance from our LangGraph multi-agent system.", border: "hover:border-violet-500/50" },
                  ].map((a) => (
                    <div key={a.tab} onClick={() => setActiveTab(a.tab)}
                      className={`p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 ${a.border} cursor-pointer transition-all hover:bg-slate-900/90`}>
                      <div className="text-2xl mb-3">{a.icon}</div>
                      <h3 className="font-semibold text-white text-sm mb-1">{a.title}</h3>
                      <p className="text-xs text-slate-400 leading-relaxed">{a.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Resume ATS */}
            {activeTab === "resumes" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="space-y-4">
                  <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
                    <h3 className="text-base font-bold text-white mb-1">Upload Resume</h3>
                    <p className="text-xs text-slate-400 mb-4">PDF or DOCX, max 10MB.</p>
                    <input ref={fileInputRef} type="file" accept=".pdf,.docx" onChange={handleFileUpload} className="hidden" id="file-resume-input" />
                    <div
                      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                      onDragLeave={() => setIsDragging(false)}
                      onDrop={handleDrop}
                      onClick={() => fileInputRef.current?.click()}
                      className={`w-full py-8 rounded-xl border-2 border-dashed text-center cursor-pointer transition-all ${isDragging ? "border-indigo-500 bg-indigo-500/10" : "border-indigo-500/30 bg-indigo-500/5 hover:border-indigo-500/60 hover:bg-indigo-500/10"}`}>
                      <div className="text-3xl mb-2">📂</div>
                      <div className="text-indigo-300 text-xs font-semibold">Drop file here or click to browse</div>
                      <div className="text-slate-500 text-[10px] mt-1">PDF • DOCX</div>
                    </div>
                    <button id="btn-upload-resume" onClick={() => fileInputRef.current?.click()}
                      className="w-full mt-3 py-2.5 rounded-xl bg-indigo-600/80 hover:bg-indigo-600 text-white text-xs font-semibold transition cursor-pointer">
                      Select File
                    </button>
                    {uploadStatus && (
                      <div className={`mt-3 text-xs p-3 rounded-lg ${uploadStatus.includes("failed") || uploadStatus.includes("error") ? "bg-rose-950/40 text-rose-400" : uploadStatus.includes("success") || uploadStatus.includes("successfully") ? "bg-emerald-950/40 text-emerald-400" : "bg-indigo-950/40 text-indigo-400"}`}>
                        {uploadStatus}
                      </div>
                    )}
                  </div>
                  <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
                    <h3 className="text-base font-bold text-white mb-3">Your Resumes ({resumes.length})</h3>
                    {resumes.length === 0 ? (
                      <div className="text-center py-8 text-slate-500"><div className="text-3xl mb-2">📭</div><p className="text-xs">No resumes uploaded yet.</p></div>
                    ) : (
                      <div className="space-y-2">
                        {resumes.map((r) => (
                          <div key={r.id} onClick={() => { setSelectedResumeId(r.id); handleAnalyzeResume(r.id); }}
                            className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${selectedResumeId === r.id ? "bg-indigo-950/50 border-indigo-500 text-indigo-200" : "bg-slate-950/50 border-slate-800 text-slate-300 hover:border-slate-700"}`}>
                            <div className="font-semibold truncate">📄 {r.original_filename}</div>
                            <div className="flex justify-between text-slate-500 mt-1.5">
                              <span className="px-1.5 py-0.5 rounded bg-slate-800">v{r.version}</span>
                              <span className={`px-1.5 py-0.5 rounded capitalize ${r.status === "analyzed" ? "bg-emerald-900/40 text-emerald-400" : "bg-slate-800"}`}>{r.status}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="lg:col-span-2">
                  {resumeLoading ? (
                    <div className="flex flex-col items-center justify-center h-64 rounded-2xl border border-slate-800 bg-slate-900/50 gap-4">
                      <div className="h-10 w-10 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
                      <p className="text-sm text-slate-400">Analyzing with ATS AI engine...</p>
                    </div>
                  ) : atsScore ? (
                    <div className="space-y-4">
                      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800">
                        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
                          <ScoreCircle score={Math.round(atsScore.overall_score)} size={110} label="ATS Score" />
                          <div className="flex-1 space-y-3 w-full">
                            <div>
                              <h3 className="text-lg font-bold text-white">ATS Compatibility Report</h3>
                              <p className="text-xs text-slate-400 mt-0.5">Evaluated against industry hiring criteria.</p>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                              {[
                                { label: "Keywords", val: atsScore.keyword_score ?? 0, color: "text-cyan-400" },
                                { label: "Formatting", val: atsScore.format_score ?? 0, color: "text-emerald-400" },
                                { label: "Experience", val: atsScore.experience_score ?? 0, color: "text-amber-400" },
                                { label: "Impact", val: atsScore.impact_score ?? 0, color: "text-violet-400" },
                              ].map((s) => (
                                <div key={s.label} className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                                  <div className="text-xs text-slate-400">{s.label}</div>
                                  <div className={`text-xl font-bold mt-0.5 ${s.color}`}>{s.val}%</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Score Breakdown</h4>
                        <ProgressBar value={atsScore.keyword_score ?? 0} label="Keyword Match" color="bg-cyan-500" />
                        <ProgressBar value={atsScore.format_score ?? 0} label="Format Quality" color="bg-emerald-500" />
                        <ProgressBar value={atsScore.experience_score ?? 0} label="Experience Depth" color="bg-amber-500" />
                        <ProgressBar value={atsScore.impact_score ?? 0} label="Impact & Achievements" color="bg-violet-500" />
                        <ProgressBar value={atsScore.education_score ?? 0} label="Education Match" color="bg-indigo-500" />
                      </div>
                      {(atsScore.improvement_suggestions?.matching_skills?.length || atsScore.improvement_suggestions?.missing_skills?.length) ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {atsScore.improvement_suggestions?.matching_skills && atsScore.improvement_suggestions.matching_skills.length > 0 && (
                            <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-800/30 space-y-2">
                              <div className="flex items-center justify-between">
                                <h4 className="text-xs font-bold text-emerald-400 uppercase">Matching Skills</h4>
                                <span className="text-[10px] bg-emerald-900/60 text-emerald-300 px-2 py-0.5 rounded-full">{atsScore.improvement_suggestions.matching_skills.length} matched</span>
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                {atsScore.improvement_suggestions.matching_skills.map((sk: string, i: number) => <SkillBadge key={i} skill={sk} variant="match" />)}
                              </div>
                            </div>
                          )}
                          {atsScore.improvement_suggestions?.missing_skills && atsScore.improvement_suggestions.missing_skills.length > 0 && (
                            <div className="p-4 rounded-2xl bg-rose-950/20 border border-rose-800/30 space-y-2">
                              <div className="flex items-center justify-between">
                                <h4 className="text-xs font-bold text-rose-400 uppercase">Skills to Add</h4>
                                <span className="text-[10px] bg-rose-900/60 text-rose-300 px-2 py-0.5 rounded-full">{atsScore.improvement_suggestions.missing_skills.length} missing</span>
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                {atsScore.improvement_suggestions.missing_skills.map((sk: string, i: number) => <SkillBadge key={i} skill={sk} variant="missing" />)}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : null}
                      {atsScore.improvement_suggestions?.top_recommendations && atsScore.improvement_suggestions.top_recommendations.length > 0 && (
                        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Top Recommendations</h4>
                          <ul className="space-y-2">
                            {atsScore.improvement_suggestions.top_recommendations.map((rec: string, i: number) => (
                              <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                                <span className="text-indigo-400 mt-0.5 flex-shrink-0">→</span><span>{rec}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {selectedResume?.parsed_data?.skills?.all && selectedResume.parsed_data.skills.all.length > 0 && (
                        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Extracted Skills ({selectedResume.parsed_data.skills.all.length})</h4>
                          <div className="flex flex-wrap gap-1.5">
                            {selectedResume.parsed_data.skills.all.map((sk: string, i: number) => <SkillBadge key={i} skill={sk} />)}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-64 rounded-2xl border-2 border-dashed border-slate-800 bg-slate-900/30 gap-3 text-center p-8">
                      <div className="text-4xl">📋</div>
                      <p className="text-sm text-slate-400 font-medium">Select or upload a resume to view ATS analysis</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Job Matcher */}
            {activeTab === "jobs" && (
              <div className="space-y-5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-white">Job Matching Engine</h2>
                    <p className="text-xs text-slate-400 mt-0.5">AI-matched opportunities ranked by your skills.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <input type="text" placeholder="Search roles, companies..." value={jobQuery} onChange={(e) => setJobQuery(e.target.value)}
                      className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 w-48" />
                    <select value={jobTypeFilter} onChange={(e) => setJobTypeFilter(e.target.value)}
                      className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none cursor-pointer">
                      <option value="all">All Types</option>
                      <option value="remote">Remote</option>
                      <option value="hybrid">Hybrid</option>
                      <option value="onsite">On-site</option>
                    </select>
                    <select value={jobLevelFilter} onChange={(e) => setJobLevelFilter(e.target.value)}
                      className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none cursor-pointer">
                      <option value="all">All Levels</option>
                      <option value="entry">Entry</option>
                      <option value="mid">Mid</option>
                      <option value="senior">Senior</option>
                      <option value="lead">Lead</option>
                    </select>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span className="font-medium text-slate-300">{displayJobs.length} results</span>
                  {recommendedJobs.length > 0 && <span className="px-2 py-0.5 rounded-full bg-indigo-900/40 text-indigo-400 border border-indigo-800/40">AI-Ranked</span>}
                </div>
                {jobsLoading ? (
                  <div className="flex justify-center items-center h-48 gap-3 text-slate-400">
                    <div className="h-6 w-6 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
                    <span className="text-sm">Loading jobs...</span>
                  </div>
                ) : displayJobs.length === 0 ? (
                  <div className="text-center py-16 text-slate-500">
                    <div className="text-4xl mb-3">🔍</div>
                    <p className="text-sm">No jobs found. Try different filters.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {displayJobs.map((job) => {
                      const ext = job as JobItem & { match_score?: number; matching_skills?: string[]; recommendation?: string };
                      const ms = ext.match_score;
                      const mc = ms != null ? (ms >= 75 ? "text-emerald-400 bg-emerald-950/30 border-emerald-800/30" : ms >= 50 ? "text-amber-400 bg-amber-950/30 border-amber-800/30" : "text-rose-400 bg-rose-950/30 border-rose-800/30") : "text-slate-400 bg-slate-800 border-slate-700";
                      return (
                        <div key={job.id} className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition space-y-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <h3 className="font-bold text-white text-sm truncate">{job.title}</h3>
                              <p className="text-xs text-indigo-400 font-medium mt-0.5">{job.company}</p>
                            </div>
                            <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                              {ms != null && <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${mc}`}>{Math.round(ms)}% match</span>}
                              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active</span>
                            </div>
                          </div>
                          {ms != null && <ProgressBar value={ms} color={ms >= 75 ? "bg-emerald-500" : ms >= 50 ? "bg-amber-500" : "bg-rose-500"} showValue={false} />}
                          <div className="flex flex-wrap gap-1.5 text-[11px]">
                            {job.location && <span className="px-2 py-0.5 rounded-lg bg-slate-800 text-slate-400">📍 {job.location}</span>}
                            {job.work_type && <span className="px-2 py-0.5 rounded-lg bg-slate-800 text-slate-400 capitalize">💼 {job.work_type}</span>}
                            {job.experience_level && <span className="px-2 py-0.5 rounded-lg bg-slate-800 text-slate-400 capitalize">📈 {job.experience_level}</span>}
                            {job.salary_range && <span className="px-2 py-0.5 rounded-lg bg-emerald-950/30 text-emerald-400">💰 {job.salary_range}</span>}
                          </div>
                          {ext.matching_skills && ext.matching_skills.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {ext.matching_skills.slice(0, 4).map((sk, i) => <SkillBadge key={i} skill={sk} variant="match" />)}
                              {ext.matching_skills.length > 4 && <span className="text-[10px] text-slate-500 self-center">+{ext.matching_skills.length - 4} more</span>}
                            </div>
                          )}
                          {ext.recommendation && <p className="text-[11px] text-slate-400 border-t border-slate-800 pt-2 line-clamp-2">{ext.recommendation}</p>}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Chat */}
            {activeTab === "chat" && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-5" style={{ height: "calc(100vh - 200px)", minHeight: "520px" }}>
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-bold text-white text-sm">Conversations</h3>
                    <button id="btn-new-chat" onClick={async () => {
                      if (!token) return;
                      try {
                        const s = await api.createChatSession(token, `Session ${chatSessions.length + 1}`);
                        setChatSessions([s, ...chatSessions]); setCurrentSessionId(s.id); setMessages([]);
                      } catch (e: unknown) { alert((e as { message?: string })?.message); }
                    }}
                      className="px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer transition">
                      + New
                    </button>
                  </div>
                  <div className="flex-1 overflow-y-auto space-y-1.5">
                    {chatSessions.length === 0 ? (
                      <div className="text-center py-8 text-xs text-slate-500"><div className="text-2xl mb-2">💬</div><p>No sessions yet.</p></div>
                    ) : chatSessions.map((s) => (
                      <div key={s.id} onClick={async () => {
                        if (!token) return;
                        setCurrentSessionId(s.id);
                        try { const h = await api.getChatHistory(token, s.id); setMessages(h.messages); } catch { setMessages([]); }
                      }}
                        className={`p-2.5 rounded-xl text-xs cursor-pointer transition-all ${currentSessionId === s.id ? "bg-indigo-950/60 border border-indigo-500 text-indigo-200" : "bg-slate-950/40 text-slate-400 hover:bg-slate-800/50 border border-transparent"}`}>
                        <div className="font-medium truncate">💬 {s.title}</div>
                        <div className="text-[10px] text-slate-500 mt-0.5">{s.message_count} messages</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="md:col-span-3 p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col">
                  <div className="flex items-center gap-3 pb-3 border-b border-slate-800 mb-3">
                    <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center text-sm">🤖</div>
                    <div>
                      <div className="text-sm font-bold text-white">AI Career Advisor</div>
                      <div className="text-xs text-emerald-400">● LangGraph Multi-Agent System</div>
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                    {!currentSessionId ? (
                      <div className="flex flex-col items-center justify-center h-full text-center gap-4">
                        <div className="text-4xl">🤖</div>
                        <p className="text-sm font-semibold text-slate-300">Create a session to get started</p>
                      </div>
                    ) : messages.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-full text-center gap-3">
                        <div className="text-3xl">👋</div>
                        <p className="text-sm text-slate-400">Ask your AI Career Advisor anything!</p>
                        <div className="grid grid-cols-2 gap-2 w-full max-w-xs">
                          {["What jobs match my skills?", "Resume improvement tips", "Career roadmap advice", "Interview prep help"].map((q) => (
                            <button key={q} onClick={() => setInputMessage(q)} className="px-3 py-2 text-[11px] rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-left transition cursor-pointer">{q}</button>
                          ))}
                        </div>
                      </div>
                    ) : (
                      messages.map((m) => (
                        <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                          {m.role !== "user" && <div className="h-7 w-7 rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center text-xs flex-shrink-0 mr-2 mt-0.5">🤖</div>}
                          <div className={`max-w-[75%] p-3 rounded-2xl text-xs leading-relaxed ${m.role === "user" ? "bg-indigo-600 text-white rounded-tr-sm" : "bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm"}`}>
                            <div className="whitespace-pre-wrap">{m.content}</div>
                            <div className={`text-[10px] mt-1.5 ${m.role === "user" ? "text-indigo-300" : "text-slate-500"}`}>
                              {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                    {chatLoading && (
                      <div className="flex justify-start">
                        <div className="h-7 w-7 rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center text-xs flex-shrink-0 mr-2">🤖</div>
                        <div className="p-3 rounded-2xl bg-slate-800 border border-slate-700">
                          <div className="flex gap-1">
                            {[0, 150, 300].map((d) => <span key={d} className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: `${d}ms` }} />)}
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                  <form onSubmit={handleSendMessage} className="pt-3 border-t border-slate-800 flex gap-2 mt-3">
                    <input id="input-chat-message" type="text" placeholder={currentSessionId ? "Ask about careers, resumes, jobs..." : "Create a session first..."} value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)} disabled={chatLoading || !currentSessionId}
                      className="flex-1 px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition disabled:opacity-50" />
                    <button id="btn-chat-send" type="submit" disabled={chatLoading || !inputMessage.trim() || !currentSessionId}
                      className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold disabled:opacity-40 cursor-pointer transition">
                      {chatLoading ? "⟳" : "Send"}
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* Diagnostics */}
            {activeTab === "tracer" && (
              <div className="space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-white">API Integration Diagnostics</h2>
                    <p className="text-xs text-slate-400 mt-0.5">Live end-to-end API trace across all subsystems.</p>
                  </div>
                  <div className="flex gap-3 items-center">
                    <div className={`px-3 py-1.5 rounded-full text-xs font-medium border ${
                      apiStatus === "online" ? "bg-emerald-950/40 text-emerald-400 border-emerald-800/40" :
                      apiStatus === "offline" ? "bg-rose-950/40 text-rose-400 border-rose-800/40" :
                      apiStatus === "waking" ? "bg-amber-950/40 text-amber-400 border-amber-800/40" :
                      "bg-slate-800 text-slate-400 border-slate-700"}`}>
                      {apiStatus === "online" ? "● Backend Online" :
                       apiStatus === "offline" ? "● Backend Offline" :
                       apiStatus === "waking" ? "⟳ Backend Waking Up..." :
                       "Checking..."}
                    </div>
                    <button id="btn-run-trace" onClick={runLiveIntegrationTrace} disabled={isTracing}
                      className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold disabled:opacity-50 cursor-pointer transition flex items-center gap-2">
                      {isTracing ? (<><span className="h-3 w-3 rounded-full border-2 border-white border-t-transparent animate-spin" /> Running...</>) : "Run Full Trace"}
                    </button>
                  </div>
                </div>
                <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-xs text-slate-400">
                  <span className="text-slate-300 font-semibold">Backend API:</span>{" "}
                  <code className="text-indigo-400">{api.getBaseUrl()}</code>
                </div>
                {traceLogs.length > 0 && (
                  <div>
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-center">
                        <div className="text-2xl font-bold text-white">{traceLogs.length}</div>
                        <div className="text-xs text-slate-400 mt-0.5">Steps</div>
                      </div>
                      <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-800/30 text-center">
                        <div className="text-2xl font-bold text-emerald-400">{traceLogs.filter((l) => l.ok).length}</div>
                        <div className="text-xs text-emerald-500 mt-0.5">Passed</div>
                      </div>
                      <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-800/30 text-center">
                        <div className="text-2xl font-bold text-rose-400">{traceLogs.filter((l) => !l.ok).length}</div>
                        <div className="text-xs text-rose-500 mt-0.5">Failed</div>
                      </div>
                    </div>
                    <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-900/80">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                          <tr>
                            <th className="py-3 px-4">#</th><th className="py-3 px-4">Step</th>
                            <th className="py-3 px-4">Method</th><th className="py-3 px-4">Endpoint</th>
                            <th className="py-3 px-4">Status</th><th className="py-3 px-4">Latency</th><th className="py-3 px-4">Result</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 font-mono">
                          {traceLogs.map((log, i) => (
                            <tr key={i} className="hover:bg-slate-800/40">
                              <td className="py-3 px-4 text-slate-500 font-sans">{i + 1}</td>
                              <td className="py-3 px-4 font-sans text-slate-200 font-medium">{log.step}</td>
                              <td className="py-3 px-4"><span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${log.method === "POST" ? "bg-blue-500/20 text-blue-400" : log.method === "PUT" ? "bg-amber-500/20 text-amber-400" : "bg-emerald-500/20 text-emerald-400"}`}>{log.method}</span></td>
                              <td className="py-3 px-4 text-slate-300">{log.endpoint}</td>
                              <td className="py-3 px-4"><span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${log.ok ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"}`}>{log.status}</span></td>
                              <td className="py-3 px-4 text-slate-400">{log.durationMs}ms</td>
                              <td className="py-3 px-4 font-sans">{log.ok ? <span className="text-emerald-400">OK</span> : <span className="text-rose-400">FAIL</span>}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                {traceLogs.length === 0 && !isTracing && (
                  <div className="text-center py-16 text-slate-500">
                    <div className="text-4xl mb-3">🧪</div>
                    <p className="text-sm font-medium text-slate-400">Click Run Full Trace to test all API endpoints.</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
      <footer className="border-t border-slate-800/60 py-4 px-6 text-center">
        <p className="text-[11px] text-slate-500">
          AI Career Intelligence · FastAPI + Next.js + LangGraph ·{" "}
          <a href="https://ai-career-backend-codr.onrender.com/docs" target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">API Docs</a>
        </p>
      </footer>
    </div>
  );
}
