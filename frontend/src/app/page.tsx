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

export default function Home() {
  // --- Auth State ---
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("alex.dev@example.com");
  const [authPassword, setAuthPassword] = useState("Password123!");
  const [authFullName, setAuthFullName] = useState("Alex Developer");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  // --- Active View ---
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "resumes" | "jobs" | "chat" | "tracer"
  >("dashboard");

  // --- Resumes State ---
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [atsScore, setAtsScore] = useState<ATSScoreData | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const selectedResume = resumes.find((r) => r.id === selectedResumeId);

  // --- Jobs State ---
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [recommendedJobs, setRecommendedJobs] = useState<JobItem[]>([]);
  const [jobQuery, setJobQuery] = useState("");
  const [jobsLoading, setJobsLoading] = useState(false);

  // --- Chat State ---
  const [chatSessions, setChatSessions] = useState<ChatSessionItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // --- Trace State ---
  const [traceLogs, setTraceLogs] = useState<ApiTraceRecord[]>([]);
  const [isTracing, setIsTracing] = useState(false);

  const [token, setToken] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("ai_career_token");
    }
    return null;
  });

  const handleLogout = useCallback(async () => {
    if (token) {
      try {
        await api.logout(token);
      } catch {
        // ignore
      }
    }
    setToken(null);
    setCurrentUser(null);
    localStorage.removeItem("ai_career_token");
  }, [token]);

  // Load resources when token updates
  useEffect(() => {
    if (!token) return;
    let active = true;

    const initData = async () => {
      setJobsLoading(true);
      try {
        const [user, resumeList, allJobs, recJobs, sessions] = await Promise.all([
          api.getMe(token),
          api.listResumes(token),
          api.listJobs(token),
          api.getJobRecommendations(token),
          api.listChatSessions(token),
        ]);
        if (!active) return;
        setCurrentUser(user);
        setResumes(resumeList);
        setJobs(allJobs);
        setRecommendedJobs(recJobs);
        setChatSessions(sessions);
        if (sessions.length > 0) {
          setCurrentSessionId(sessions[0].id);
          const history = await api.getChatHistory(token, sessions[0].id);
          if (active) setMessages(history.messages);
        }
      } catch {
        if (active) {
          setToken(null);
          setCurrentUser(null);
          localStorage.removeItem("ai_career_token");
        }
      } finally {
        if (active) {
          setJobsLoading(false);
        }
      }
    };

    void initData();

    return () => {
      active = false;
    };
  }, [token]);

  // --- Helper functions for data loading ---
  const fetchUserData = async (t: string) => {
    try {
      const user = await api.getMe(t);
      setCurrentUser(user);
    } catch {
      // token invalid — handled by caller
    }
  };

  const loadResumes = async (t: string) => {
    try {
      const resumeList = await api.listResumes(t);
      setResumes(resumeList);
    } catch {
      // ignore — list will remain stale
    }
  };

  const selectChatSession = async (t: string | null, sessionId: string) => {
    if (!t) return;
    setCurrentSessionId(sessionId);
    try {
      const history = await api.getChatHistory(t, sessionId);
      setMessages(history.messages);
    } catch {
      setMessages([]);
    }
  };

  // --- Auth Handlers ---
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);

    try {
      if (authMode === "register") {
        await api.register({
          email: authEmail,
          password: authPassword,
          full_name: authFullName,
        });
      }

      const tokenRes = await api.login({
        email: authEmail,
        password: authPassword,
      });

      setToken(tokenRes.access_token);
      localStorage.setItem("ai_career_token", tokenRes.access_token);
      await fetchUserData(tokenRes.access_token);
      setAuthError(null);
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || "Authentication failed.";
      setAuthError(msg);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleAnalyzeResume = async (resumeId: string) => {
    if (!token) return;
    setResumeLoading(true);
    try {
      const analysis = await api.analyzeResume(token, resumeId);
      setAtsScore(analysis);
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || "Analysis failed";
      setUploadStatus(`Analysis error: ${msg}`);
    } finally {
      setResumeLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;

    setUploadStatus("Uploading resume...");
    try {
      const uploaded = await api.uploadResume(token, file);
      setUploadStatus(`Uploaded ${uploaded.original_filename} successfully!`);
      await loadResumes(token);
      setSelectedResumeId(uploaded.id);
      await handleAnalyzeResume(uploaded.id);
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || "Upload failed";
      setUploadStatus(`Upload failed: ${msg}`);
    }
  };

  const handleCreateSession = async () => {
    if (!token) return;
    try {
      const newSession = await api.createChatSession(
        token,
        `Advisory Session ${chatSessions.length + 1}`
      );
      setChatSessions([newSession, ...chatSessions]);
      setCurrentSessionId(newSession.id);
      setMessages([]);
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || "Could not create session";
      alert(`Could not create session: ${msg}`);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !token || !currentSessionId) return;

    const userText = inputMessage.trim();
    setInputMessage("");
    setChatLoading(true);

    const tempUserMsg: ChatMessageItem = {
      id: "temp-" + Date.now(),
      role: "user",
      content: userText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const botResponse = await api.sendChatMessage(
        token,
        currentSessionId,
        userText
      );
      setMessages((prev) => [...prev, botResponse]);
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message || "Chat failed";
      alert(`Chat error: ${msg}`);
    } finally {
      setChatLoading(false);
    }
  };

  // --- Automated End-to-End Tracer ---
  const runLiveIntegrationTrace = async () => {
    setIsTracing(true);
    const records: ApiTraceRecord[] = [];

    const trace = async <T,>(
      step: string,
      endpoint: string,
      method: string,
      fn: () => Promise<T>
    ): Promise<T> => {
      const start = performance.now();
      try {
        const result = await fn();
        const duration = Math.round(performance.now() - start);
        const record: ApiTraceRecord = {
          step,
          endpoint,
          method,
          status: 200,
          durationMs: duration,
          ok: true,
          details: result,
        };
        records.push(record);
        setTraceLogs([...records]);
        return result;
      } catch (err: unknown) {
        const duration = Math.round(performance.now() - start);
        const errObj = err as { status?: number; detail?: unknown; message?: string };
        const record: ApiTraceRecord = {
          step,
          endpoint,
          method,
          status: errObj.status || 500,
          durationMs: duration,
          ok: false,
          details: errObj.detail || errObj.message,
        };
        records.push(record);
        setTraceLogs([...records]);
        throw err;
      }
    };

    try {
      const testEmail = `test_${Date.now()}@integration.com`;
      const testPassword = "Password123!";

      // 1. Health Probe
      await trace("API Health Probe", "/health", "GET", async () => {
        const res = await fetch(`${api.getBaseUrl()}/health`);
        return res.json();
      });

      // 2. User Registration
      await trace("User Registration", "/auth/register", "POST", async () => {
        return api.register({
          email: testEmail,
          password: testPassword,
          full_name: "Integration Test User",
        });
      });

      // 3. User Login
      const loginData = await trace("User Login", "/auth/login", "POST", async () => {
        return api.login({ email: testEmail, password: testPassword });
      });
      const jwtToken = loginData.access_token;

      // 4. Authenticated Profile
      await trace("Get Profile (/auth/me)", "/auth/me", "GET", async () => {
        return api.getMe(jwtToken);
      });

      // 5. Update Profile
      await trace("Update Profile", "/users/profile", "PUT", async () => {
        return api.updateProfile(jwtToken, {
          full_name: "Verified Integration User",
        });
      });

      // 6. Resume Upload
      const fakePdf = new File(
        [
          "John Doe - Senior Software Engineer\n" +
            "Email: john.doe@integration.com | Phone: 555-0199\n" +
            "Experience: Built scalable microservices with Python, FastAPI, React, and TypeScript. Optimized SQL queries.\n" +
            "Education: Bachelor of Science in Computer Science.\n" +
            "Skills: Python, TypeScript, React, Docker, Kubernetes, AWS, SQL, REST API, Git.",
        ],
        "john_doe_resume.pdf",
        { type: "application/pdf" }
      );

      const resumeUploaded = await trace(
        "Upload Resume",
        "/resumes/upload",
        "POST",
        async () => {
          return api.uploadResume(jwtToken, fakePdf);
        }
      );

      // 7. Resume ATS Analysis
      await trace(
        "Analyze Resume ATS",
        `/resumes/${resumeUploaded.id}/analyze`,
        "POST",
        async () => {
          return api.analyzeResume(jwtToken, resumeUploaded.id);
        }
      );

      // 8. Job Recommendations
      await trace(
        "Job Recommendations",
        "/jobs/recommendations",
        "GET",
        async () => {
          return api.getJobRecommendations(jwtToken);
        }
      );

      // 9. Create Chat Session
      const session = await trace(
        "Create Chat Session",
        "/chat/sessions",
        "POST",
        async () => {
          return api.createChatSession(jwtToken, "E2E Integration Verification");
        }
      );

      // 10. Send Chat Message
      await trace(
        "Send Chat Message",
        `/chat/sessions/${session.id}/messages`,
        "POST",
        async () => {
          return api.sendChatMessage(
            jwtToken,
            session.id,
            "What roles best match my experience with FastAPI and React?"
          );
        }
      );

      // 11. Logout
      await trace("User Logout", "/auth/logout", "POST", async () => {
        return api.logout(jwtToken);
      });
    } catch {
      // stop trace on error
    } finally {
      setIsTracing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Navigation */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-violet-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <span className="font-extrabold text-white text-lg tracking-wider">
                CI
              </span>
            </div>
            <div>
              <span className="font-bold text-lg bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">
                AI Career Intelligence
              </span>
              <span className="ml-2.5 text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                v1.0 Live
              </span>
            </div>
          </div>

          {/* Navigation Tabs */}
          {token && (
            <nav className="flex space-x-1 bg-slate-800/50 p-1 rounded-xl border border-slate-700/50">
              {(
                [
                  { id: "dashboard", label: "Dashboard" },
                  { id: "resumes", label: "Resume Analyzer" },
                  { id: "jobs", label: "Job Matcher" },
                  { id: "chat", label: "Career Advisor" },
                  { id: "tracer", label: "API Diagnostics" },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  id={`tab-${tab.id}`}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                    activeTab === tab.id
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          )}

          {/* User Profile / Auth Toggle */}
          <div className="flex items-center space-x-4">
            {currentUser ? (
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <div className="text-sm font-semibold text-slate-200">
                    {currentUser.full_name}
                  </div>
                  <div className="text-xs text-indigo-400">
                    {currentUser.role.toUpperCase()}
                  </div>
                </div>
                <button
                  id="btn-logout"
                  onClick={handleLogout}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-rose-900/40 text-slate-300 hover:text-rose-300 border border-slate-700 transition cursor-pointer"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <span className="text-xs text-slate-400">Not authenticated</span>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8">
        {!token ? (
          /* Authentication Screen */
          <div className="max-w-md mx-auto my-12 p-8 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-2xl backdrop-blur-xl">
            <div className="text-center mb-6">
              <h1 className="text-2xl font-bold text-white mb-2">
                {authMode === "login" ? "Welcome Back" : "Create Your Account"}
              </h1>
              <p className="text-sm text-slate-400">
                {authMode === "login"
                  ? "Access your AI-powered career analytics & roadmap."
                  : "Start analyzing resumes and matching high-impact jobs."}
              </p>
            </div>

            {authError && (
              <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} className="space-y-4">
              {authMode === "register" && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Full Name
                  </label>
                  <input
                    id="input-fullname"
                    type="text"
                    required
                    value={authFullName}
                    onChange={(e) => setAuthFullName(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
                    placeholder="Jane Doe"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Email Address
                </label>
                <input
                  id="input-email"
                  type="email"
                  required
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
                  placeholder="name@company.com"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Password
                </label>
                <input
                  id="input-password"
                  type="password"
                  required
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:border-indigo-500 focus:outline-none"
                  placeholder="••••••••"
                />
              </div>

              <button
                id="btn-auth-submit"
                type="submit"
                disabled={authLoading}
                className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition shadow-lg shadow-indigo-600/30 disabled:opacity-50 cursor-pointer"
              >
                {authLoading
                  ? "Authenticating..."
                  : authMode === "login"
                  ? "Sign In"
                  : "Register"}
              </button>
            </form>

            <div className="mt-6 text-center text-xs text-slate-400">
              {authMode === "login" ? (
                <span>
                  Don&apos;t have an account?{" "}
                  <button
                    id="btn-switch-register"
                    onClick={() => setAuthMode("register")}
                    className="text-indigo-400 hover:underline font-semibold cursor-pointer"
                  >
                    Register now
                  </button>
                </span>
              ) : (
                <span>
                  Already have an account?{" "}
                  <button
                    id="btn-switch-login"
                    onClick={() => setAuthMode("login")}
                    className="text-indigo-400 hover:underline font-semibold cursor-pointer"
                  >
                    Sign In
                  </button>
                </span>
              )}
            </div>
          </div>
        ) : (
          /* Authenticated Views */
          <div>
            {/* View 1: Dashboard */}
            {activeTab === "dashboard" && (
              <div className="space-y-6">
                <div className="p-6 rounded-2xl bg-gradient-to-r from-indigo-950/60 via-slate-900 to-slate-900 border border-indigo-900/40">
                  <h2 className="text-xl font-bold text-white mb-1">
                    Welcome back, {currentUser?.full_name}!
                  </h2>
                  <p className="text-sm text-slate-400">
                    Your career intelligence dashboard is live and connected to
                    the backend analytics engine.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Resumes Uploaded
                    </div>
                    <div className="text-3xl font-extrabold text-indigo-400 mt-2">
                      {resumes.length}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      Ready for ATS evaluation
                    </div>
                  </div>

                  <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Job Matches
                    </div>
                    <div className="text-3xl font-extrabold text-cyan-400 mt-2">
                      {recommendedJobs.length || jobs.length}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      Active matching opportunities
                    </div>
                  </div>

                  <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Advisory Sessions
                    </div>
                    <div className="text-3xl font-extrabold text-violet-400 mt-2">
                      {chatSessions.length}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      Consultation threads
                    </div>
                  </div>

                  <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Status
                    </div>
                    <div className="text-3xl font-extrabold text-emerald-400 mt-2">
                      Active
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      API Gateway Online
                    </div>
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  <div
                    onClick={() => setActiveTab("resumes")}
                    className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-indigo-500/50 cursor-pointer transition"
                  >
                    <h3 className="font-semibold text-white text-base">
                      📄 Resume ATS Analyzer
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Upload PDF/DOCX to get detailed scoring, keywords, and
                      recommendations.
                    </p>
                  </div>
                  <div
                    onClick={() => setActiveTab("jobs")}
                    className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-cyan-500/50 cursor-pointer transition"
                  >
                    <h3 className="font-semibold text-white text-base">
                      🎯 Job Recommendations
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Explore matching roles based on your skills and
                      experience.
                    </p>
                  </div>
                  <div
                    onClick={() => setActiveTab("chat")}
                    className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-violet-500/50 cursor-pointer transition"
                  >
                    <h3 className="font-semibold text-white text-base">
                      💬 AI Career Advisor
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Get personalized career guidance and roadmap strategy.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* View 2: Resumes & ATS Analysis */}
            {activeTab === "resumes" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Upload & List Column */}
                <div className="space-y-4">
                  <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
                    <h3 className="text-base font-bold text-white mb-2">
                      Upload New Resume
                    </h3>
                    <p className="text-xs text-slate-400 mb-4">
                      Accepts PDF and DOCX formats (max 10MB).
                    </p>

                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="file-resume-input"
                    />

                    <button
                      id="btn-upload-resume"
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full py-2.5 rounded-lg border-2 border-dashed border-indigo-500/40 hover:border-indigo-500 bg-indigo-500/5 hover:bg-indigo-500/10 text-indigo-300 text-xs font-semibold transition flex items-center justify-center space-x-2 cursor-pointer"
                    >
                      <span>Select PDF or DOCX File</span>
                    </button>

                    {uploadStatus && (
                      <div className="mt-3 text-xs text-indigo-400 bg-indigo-950/40 p-2 rounded">
                        {uploadStatus}
                      </div>
                    )}
                  </div>

                  {/* Resumes List */}
                  <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
                    <h3 className="text-base font-bold text-white mb-3">
                      Your Resumes
                    </h3>
                    {resumes.length === 0 ? (
                      <p className="text-xs text-slate-500">
                        No resumes uploaded yet.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {resumes.map((r) => (
                          <div
                            key={r.id}
                            onClick={() => {
                              setSelectedResumeId(r.id);
                              handleAnalyzeResume(r.id);
                            }}
                            className={`p-3 rounded-lg border text-xs cursor-pointer transition ${
                              selectedResumeId === r.id
                                ? "bg-indigo-950/40 border-indigo-500 text-indigo-200"
                                : "bg-slate-950/50 border-slate-800 text-slate-300 hover:border-slate-700"
                            }`}
                          >
                            <div className="font-semibold truncate">
                              {r.original_filename}
                            </div>
                            <div className="flex justify-between text-slate-500 mt-1">
                              <span>Version {r.version}</span>
                              <span className="capitalize">{r.status}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* ATS Analysis Display Column */}
                <div className="lg:col-span-2">
                  {resumeLoading ? (
                    <div className="p-12 text-center text-slate-400 bg-slate-900/50 rounded-2xl border border-slate-800">
                      Analyzing resume with ATS AI engine...
                    </div>
                  ) : atsScore ? (
                    <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-6">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                        <div>
                          <h3 className="text-lg font-bold text-white">
                            ATS Score & Compatibility
                          </h3>
                          <p className="text-xs text-slate-400">
                            Evaluated against industry technical hiring criteria.
                          </p>
                        </div>
                        <div className="flex items-center space-x-3">
                          <div className="text-3xl font-extrabold text-indigo-400">
                            {atsScore.overall_score}
                            <span className="text-sm text-slate-500 font-normal">
                              /100
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Score Breakdown Metrics */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                          <div className="text-xs text-slate-400">Keywords</div>
                          <div className="text-xl font-bold text-cyan-400 mt-1">
                            {atsScore.keyword_score}%
                          </div>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                          <div className="text-xs text-slate-400">Formatting</div>
                          <div className="text-xl font-bold text-emerald-400 mt-1">
                            {atsScore.format_score}%
                          </div>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                          <div className="text-xs text-slate-400">Experience</div>
                          <div className="text-xl font-bold text-amber-400 mt-1">
                            {atsScore.experience_score}%
                          </div>
                        </div>
                        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                          <div className="text-xs text-slate-400">Impact</div>
                          <div className="text-xl font-bold text-violet-400 mt-1">
                            {atsScore.impact_score}%
                          </div>
                        </div>
                      </div>

                      {/* Section Feedback */}
                      {atsScore.section_feedback && (
                        <div>
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                            Section Breakdown
                          </h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                            {Object.entries(atsScore.section_feedback).map(
                              ([key, val]) => (
                                <div
                                  key={key}
                                  className="p-3 rounded-lg bg-slate-950 border border-slate-800"
                                >
                                  <div className="font-semibold text-slate-300 capitalize mb-1">
                                    {key.replace("_", " ")}
                                  </div>
                                  <div className="text-slate-400">{String(val)}</div>
                                </div>
                              )
                            )}
                          </div>
                        </div>
                      )}

                      {/* Improvement Suggestions */}
                      {atsScore.improvement_suggestions?.top_recommendations && (
                        <div>
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                            Top Recommendations
                          </h4>
                          <ul className="space-y-1.5 text-xs text-slate-300">
                            {atsScore.improvement_suggestions.top_recommendations.map(
                              (rec: string, idx: number) => (
                                <li key={idx} className="flex items-start space-x-2">
                                  <span className="text-indigo-400">✓</span>
                                  <span>{rec}</span>
                                </li>
                              )
                            )}
                          </ul>
                        </div>
                      )}

                      {/* Matching & Missing Skills (when evaluated against job description) */}
                      {atsScore.improvement_suggestions && (
                        Boolean(atsScore.improvement_suggestions.matching_skills && atsScore.improvement_suggestions.matching_skills.length > 0) ||
                        Boolean(atsScore.improvement_suggestions.missing_skills && atsScore.improvement_suggestions.missing_skills.length > 0)
                      ) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {atsScore.improvement_suggestions.matching_skills && atsScore.improvement_suggestions.matching_skills.length > 0 && (
                            <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-800/40 space-y-2">
                              <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center justify-between">
                                <span>Matching Skills</span>
                                <span className="px-1.5 py-0.5 rounded bg-emerald-900/60 text-emerald-300 text-[10px]">
                                  {atsScore.improvement_suggestions.matching_skills.length} matched
                                </span>
                              </div>
                              <div className="flex flex-wrap gap-1.5 pt-1">
                                {atsScore.improvement_suggestions.matching_skills.map((sk: string, idx: number) => (
                                  <span key={idx} className="px-2 py-0.5 rounded bg-emerald-900/40 border border-emerald-700/40 text-emerald-200 text-xs">
                                    ✓ {sk}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {atsScore.improvement_suggestions.missing_skills && atsScore.improvement_suggestions.missing_skills.length > 0 && (
                            <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-800/40 space-y-2">
                              <div className="text-xs font-semibold text-rose-400 uppercase tracking-wider flex items-center justify-between">
                                <span>Missing Skills</span>
                                <span className="px-1.5 py-0.5 rounded bg-rose-900/60 text-rose-300 text-[10px]">
                                  {atsScore.improvement_suggestions.missing_skills.length} missing
                                </span>
                              </div>
                              <div className="flex flex-wrap gap-1.5 pt-1">
                                {atsScore.improvement_suggestions.missing_skills.map((sk: string, idx: number) => (
                                  <span key={idx} className="px-2 py-0.5 rounded bg-rose-900/40 border border-rose-700/40 text-rose-200 text-xs">
                                    ! {sk}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Parsed Resume Details: Contact, Skills, Education, Projects */}
                      {selectedResume && (selectedResume.contact_info || selectedResume.parsed_data) && (
                        <div className="border-t border-slate-800 pt-5 space-y-4">
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                            <span>Extracted Resume Structure</span>
                          </h4>

                          {/* Candidate Contact Details */}
                          {selectedResume.contact_info && (
                            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Candidate Contact Info</div>
                              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 text-xs">
                                {selectedResume.contact_info.name && (
                                  <div><span className="text-slate-500">Name:</span> <span className="text-slate-200 font-medium">{selectedResume.contact_info.name}</span></div>
                                )}
                                {selectedResume.contact_info.email && (
                                  <div><span className="text-slate-500">Email:</span> <span className="text-indigo-400">{selectedResume.contact_info.email}</span></div>
                                )}
                                {selectedResume.contact_info.phone && (
                                  <div><span className="text-slate-500">Phone:</span> <span className="text-slate-200">{selectedResume.contact_info.phone}</span></div>
                                )}
                                {selectedResume.contact_info.location && (
                                  <div><span className="text-slate-500">Location:</span> <span className="text-slate-200">{selectedResume.contact_info.location}</span></div>
                                )}
                                {selectedResume.contact_info.github && (
                                  <div><span className="text-slate-500">GitHub:</span> <a href={selectedResume.contact_info.github} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline">{selectedResume.contact_info.github}</a></div>
                                )}
                                {selectedResume.contact_info.linkedin && (
                                  <div><span className="text-slate-500">LinkedIn:</span> <a href={selectedResume.contact_info.linkedin} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline">{selectedResume.contact_info.linkedin}</a></div>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Extracted Skills Badges */}
                          {selectedResume.parsed_data?.skills?.all && selectedResume.parsed_data.skills.all.length > 0 && (
                            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                              <div className="flex items-center justify-between">
                                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                                  Extracted Skills ({selectedResume.parsed_data.skills.all.length})
                                </div>
                              </div>
                              <div className="flex flex-wrap gap-1.5 pt-1">
                                {selectedResume.parsed_data.skills.all.map((sk: string, idx: number) => (
                                  <span
                                    key={idx}
                                    className="px-2.5 py-1 rounded-md bg-indigo-950/60 border border-indigo-800/40 text-indigo-300 text-xs font-medium"
                                  >
                                    {sk}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Extracted Education */}
                          {selectedResume.parsed_data?.education && selectedResume.parsed_data.education.length > 0 && (
                            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                                Education
                              </div>
                              <div className="space-y-2">
                                {selectedResume.parsed_data.education.map((edu, idx: number) => (
                                  <div key={idx} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 text-xs">
                                    <div className="font-semibold text-slate-200">
                                      {edu.degree} {edu.field ? `in ${edu.field}` : ""}
                                    </div>
                                    <div className="text-slate-400 mt-0.5 flex items-center justify-between">
                                      <span>{edu.institution}</span>
                                      {edu.graduation_year && <span className="text-slate-500">{edu.graduation_year}</span>}
                                    </div>
                                    {edu.gpa && <div className="text-slate-400 mt-0.5">GPA: {edu.gpa}</div>}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Extracted Projects */}
                          {selectedResume.parsed_data?.projects && selectedResume.parsed_data.projects.length > 0 && (
                            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                                Projects
                              </div>
                              <div className="space-y-2">
                                {selectedResume.parsed_data.projects.map((proj, idx: number) => (
                                  <div key={idx} className="p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 text-xs">
                                    <div className="flex items-center justify-between">
                                      <span className="font-semibold text-slate-200">{proj.title}</span>
                                      {proj.link && (
                                        <a href={proj.link} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline text-[11px]">
                                          Link ↗
                                        </a>
                                      )}
                                    </div>
                                    {proj.description && <p className="text-slate-400 mt-1 line-clamp-2">{proj.description}</p>}
                                    {proj.technologies && proj.technologies.length > 0 && (
                                      <div className="flex flex-wrap gap-1 mt-2">
                                        {proj.technologies.map((t: string, tidx: number) => (
                                          <span key={tidx} className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300">
                                            {t}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-12 text-center text-slate-500 bg-slate-900/30 rounded-2xl border border-slate-800/60">
                      Select or upload a resume to view comprehensive ATS analysis.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* View 3: Job Matcher */}
            {activeTab === "jobs" && (
              <div className="space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-white">
                      Job Matching Engine
                    </h2>
                    <p className="text-xs text-slate-400">
                      Explore AI-matched active job listings.
                    </p>
                  </div>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      placeholder="Filter by keyword (e.g. React, Engineer)..."
                      value={jobQuery}
                      onChange={(e) => setJobQuery(e.target.value)}
                      className="px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                {jobsLoading ? (
                  <div className="p-12 text-center text-slate-400">
                    Loading job listings...
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {(recommendedJobs.length > 0 ? recommendedJobs : jobs).map(
                      (job) => (
                        <div
                          key={job.id}
                          className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition space-y-3"
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <h3 className="font-bold text-white text-base">
                                {job.title}
                              </h3>
                              <p className="text-xs text-indigo-400 font-medium">
                                {job.company}
                              </p>
                            </div>
                            <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              Active
                            </span>
                          </div>

                          <div className="flex flex-wrap gap-2 text-[11px] text-slate-400">
                            {job.location && (
                              <span className="px-2 py-0.5 rounded bg-slate-800">
                                📍 {job.location}
                              </span>
                            )}
                            {job.work_type && (
                              <span className="px-2 py-0.5 rounded bg-slate-800 capitalize">
                                💼 {job.work_type}
                              </span>
                            )}
                            {job.experience_level && (
                              <span className="px-2 py-0.5 rounded bg-slate-800 capitalize">
                                📈 {job.experience_level}
                              </span>
                            )}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}
              </div>
            )}

            {/* View 4: Chat Advisory */}
            {activeTab === "chat" && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 h-[600px]">
                {/* Chat Sessions Sidebar */}
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="font-bold text-white text-sm">Conversations</h3>
                    <button
                      id="btn-new-chat"
                      onClick={handleCreateSession}
                      className="px-2 py-1 text-xs font-semibold rounded bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer"
                    >
                      + New
                    </button>
                  </div>

                  <div className="flex-1 overflow-y-auto space-y-2">
                    {chatSessions.map((s) => (
                      <div
                        key={s.id}
                        onClick={() => selectChatSession(token, s.id)}
                        className={`p-2.5 rounded-lg text-xs cursor-pointer truncate ${
                          currentSessionId === s.id
                            ? "bg-indigo-950/50 border border-indigo-500 text-indigo-200"
                            : "bg-slate-950/40 text-slate-400 hover:bg-slate-800/40"
                        }`}
                      >
                        {s.title}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Chat Message Window */}
                <div className="md:col-span-3 p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col">
                  <div className="flex-1 overflow-y-auto space-y-3 p-2">
                    {messages.length === 0 ? (
                      <div className="text-center text-slate-500 text-xs py-24">
                        Start a conversation with the AI Career Advisor.
                      </div>
                    ) : (
                      messages.map((m) => (
                        <div
                          key={m.id}
                          className={`flex ${
                            m.role === "user" ? "justify-end" : "justify-start"
                          }`}
                        >
                          <div
                            className={`max-w-lg p-3 rounded-xl text-xs ${
                              m.role === "user"
                                ? "bg-indigo-600 text-white"
                                : "bg-slate-800 text-slate-200 border border-slate-700"
                            }`}
                          >
                            <div className="whitespace-pre-wrap">{m.content}</div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Message Input */}
                  <form
                    onSubmit={handleSendMessage}
                    className="pt-3 border-t border-slate-800 flex space-x-2"
                  >
                    <input
                      id="input-chat-message"
                      type="text"
                      placeholder="Ask the Career Advisor..."
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      disabled={chatLoading}
                      className="flex-1 px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                    <button
                      id="btn-chat-send"
                      type="submit"
                      disabled={chatLoading || !inputMessage.trim()}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold disabled:opacity-50 cursor-pointer"
                    >
                      {chatLoading ? "Thinking..." : "Send"}
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* View 5: Live Integration Diagnostic Tracer */}
            {activeTab === "tracer" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-white">
                      Live Frontend-to-Backend Integration Tracer
                    </h2>
                    <p className="text-xs text-slate-400">
                      Executes real end-to-end API calls across all subsystems and
                      measures response codes and latency.
                    </p>
                  </div>
                  <button
                    id="btn-run-trace"
                    onClick={runLiveIntegrationTrace}
                    disabled={isTracing}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/30 disabled:opacity-50 cursor-pointer"
                  >
                    {isTracing ? "Executing Trace..." : "▶ Run Full Integration Trace"}
                  </button>
                </div>

                {traceLogs.length > 0 && (
                  <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-900/80">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="py-2.5 px-4">Step</th>
                          <th className="py-2.5 px-4">Method</th>
                          <th className="py-2.5 px-4">Endpoint</th>
                          <th className="py-2.5 px-4">Status</th>
                          <th className="py-2.5 px-4">Latency</th>
                          <th className="py-2.5 px-4">State</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 font-mono">
                        {traceLogs.map((log, index) => (
                          <tr key={index} className="hover:bg-slate-800/40">
                            <td className="py-2.5 px-4 font-sans text-slate-200 font-medium">
                              {log.step}
                            </td>
                            <td className="py-2.5 px-4">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                  log.method === "POST"
                                    ? "bg-blue-500/20 text-blue-400"
                                    : log.method === "PUT"
                                    ? "bg-amber-500/20 text-amber-400"
                                    : "bg-emerald-500/20 text-emerald-400"
                                }`}
                              >
                                {log.method}
                              </span>
                            </td>
                            <td className="py-2.5 px-4 text-slate-300">
                              {log.endpoint}
                            </td>
                            <td className="py-2.5 px-4">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                  log.ok
                                    ? "bg-emerald-500/20 text-emerald-400"
                                    : "bg-rose-500/20 text-rose-400"
                                }`}
                              >
                                {log.status}
                              </span>
                            </td>
                            <td className="py-2.5 px-4 text-slate-400">
                              {log.durationMs}ms
                            </td>
                            <td className="py-2.5 px-4">
                              {log.ok ? (
                                <span className="text-emerald-400 font-sans">
                                  ✓ Verified
                                </span>
                              ) : (
                                <span className="text-rose-400 font-sans">
                                  ✗ Failed
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
