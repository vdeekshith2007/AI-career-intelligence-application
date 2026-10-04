/**
 * AI Career Intelligence — Frontend API Client
 *
 * Full-featured HTTP client for interacting with the FastAPI backend.
 * Handles authentication tokens, file uploads, JSON payloads, and structured error responses.
 */

// In production (Render), NEXT_PUBLIC_API_URL is baked in at build time via Dockerfile ARG.
// If not set (e.g. running as static export or missing build arg), fall back to the production backend.
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://ai-career-backend-codr.onrender.com/api/v1";

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  role: string;
  profile_data?: Record<string, unknown> | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface ResumeItem {
  id: string;
  original_filename: string;
  status: string;
  version: number;
  created_at: string;
  parsed_data?: {
    summary?: string | null;
    skills?: {
      all?: string[];
      categories?: Record<string, string[]>;
      total_count?: number;
    } | null;
    education?: Array<{
      degree?: string;
      field?: string;
      institution?: string;
      graduation_year?: string | null;
      gpa?: string | null;
    }> | null;
    projects?: Array<{
      title?: string;
      description?: string;
      technologies?: string[];
      link?: string | null;
    }> | null;
    experience?: Array<{
      title?: string;
      company?: string;
      dates?: string;
      highlights?: string[];
    }> | null;
    sections_detected?: Record<string, boolean>;
    word_count?: number;
  } | null;
  contact_info?: {
    name?: string | null;
    email?: string | null;
    phone?: string | null;
    linkedin?: string | null;
    github?: string | null;
    website?: string | null;
    location?: string | null;
  } | null;
}

export interface ATSScoreData {
  id: string;
  resume_id: string;
  job_id?: string | null;
  overall_score: number;
  format_score?: number | null;
  keyword_score?: number | null;
  experience_score?: number | null;
  education_score?: number | null;
  impact_score?: number | null;
  section_feedback?: Record<string, unknown> | null;
  improvement_suggestions?: {
    top_recommendations?: string[];
    keywords_found?: string[];
    matching_skills?: string[];
    missing_skills?: string[];
    [key: string]: unknown;
  } | null;
  created_at: string;
}

export interface JobItem {
  id: string;
  title: string;
  company: string;
  location?: string | null;
  work_type: string;
  salary_range?: string | null;
  experience_level: string;
  is_active: boolean;
  posted_at?: string | null;
}

export interface ChatSessionItem {
  id: string;
  title: string;
  is_active: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageItem {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: Record<string, unknown> | null;
  token_count?: number | null;
  created_at: string;
}

export interface ChatHistory {
  session: ChatSessionItem;
  messages: ChatMessageItem[];
}

export interface ApiTraceRecord {
  step: string;
  endpoint: string;
  method: string;
  status: number;
  durationMs: number;
  ok: boolean;
  details: unknown;
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE.replace(/\/+$/, "");
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    token?: string
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
    const method = options.method || "GET";
    const headers = new Headers(options.headers || {});

    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    console.log(`[API Request] ${method} ${url}`);
    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
      });
    } catch (netErr: unknown) {
      const errorMsg = (netErr as { message?: string })?.message || "Failed to fetch";
      console.error(`[API Network Error] ${method} ${url}:`, errorMsg, netErr);
      throw {
        status: 0,
        message: `Unable to connect to backend (${errorMsg}). If the service was idle, Render may be waking up from cold sleep (takes ~50s). Please retry in a moment.`,
        detail: netErr,
      };
    }

    if (!response.ok) {
      let errorDetail: unknown = "Request failed";
      try {
        const errorJson = (await response.json()) as { detail?: unknown; message?: unknown };
        errorDetail = errorJson.detail || errorJson.message || JSON.stringify(errorJson);
      } catch {
        errorDetail = await response.text();
      }

      console.error(`[API Error ${response.status}] ${method} ${url}:`, errorDetail);
      const err: ApiError = {
        status: response.status,
        message: typeof errorDetail === "string" ? errorDetail : JSON.stringify(errorDetail),
        detail: errorDetail,
      };
      throw err;
    }

    console.log(`[API Response 200] ${method} ${url}`);
    return response.json() as Promise<T>;
  }

  // --- Auth Endpoints ---
  async register(data: { email: string; password: string; full_name: string }): Promise<UserProfile> {
    return this.request<UserProfile>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async login(data: { email: string; password: string }): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getMe(token: string): Promise<UserProfile> {
    return this.request<UserProfile>("/auth/me", { method: "GET" }, token);
  }

  async logout(token: string): Promise<{ message: string }> {
    return this.request<{ message: string }>("/auth/logout", { method: "POST" }, token);
  }

  // --- User Endpoints ---
  async getProfile(token: string): Promise<UserProfile> {
    return this.request<UserProfile>("/users/profile", { method: "GET" }, token);
  }

  async updateProfile(
    token: string,
    data: { full_name?: string; profile_data?: Record<string, unknown> }
  ): Promise<UserProfile> {
    return this.request<UserProfile>("/users/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }, token);
  }

  // --- Resumes Endpoints ---
  async uploadResume(token: string, file: File): Promise<ResumeItem> {
    const formData = new FormData();
    formData.append("file", file);

    const url = `${this.baseUrl}/resumes/upload`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const err = (await response.json().catch(() => ({ detail: "Upload failed" }))) as { detail?: string };
      throw {
        status: response.status,
        message: err.detail || "Upload failed",
      };
    }

    return response.json() as Promise<ResumeItem>;
  }

  async listResumes(token: string): Promise<ResumeItem[]> {
    return this.request<ResumeItem[]>("/resumes", { method: "GET" }, token);
  }

  async getResume(token: string, resumeId: string): Promise<ResumeItem> {
    return this.request<ResumeItem>(`/resumes/${resumeId}`, { method: "GET" }, token);
  }

  async analyzeResume(token: string, resumeId: string): Promise<ATSScoreData> {
    return this.request<ATSScoreData>(`/resumes/${resumeId}/analyze`, {
      method: "POST",
      body: JSON.stringify({}),
    }, token);
  }

  async getResumeAnalysis(token: string, resumeId: string): Promise<ATSScoreData> {
    return this.request<ATSScoreData>(`/resumes/${resumeId}/analysis`, { method: "GET" }, token);
  }

  // --- Jobs Endpoints ---
  async listJobs(token: string, params: { query?: string; limit?: number } = {}): Promise<JobItem[]> {
    const searchParams = new URLSearchParams();
    if (params.query) searchParams.set("query", params.query);
    if (params.limit) searchParams.set("limit", String(params.limit));

    const queryStr = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return this.request<JobItem[]>(`/jobs${queryStr}`, { method: "GET" }, token);
  }

  async getJobRecommendations(token: string): Promise<JobItem[]> {
    return this.request<JobItem[]>("/jobs/recommendations", { method: "GET" }, token);
  }

  // --- Chat Endpoints ---
  async createChatSession(token: string, title: string = "Career Advisory Session"): Promise<ChatSessionItem> {
    return this.request<ChatSessionItem>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ title }),
    }, token);
  }

  async listChatSessions(token: string): Promise<ChatSessionItem[]> {
    return this.request<ChatSessionItem[]>("/chat/sessions", { method: "GET" }, token);
  }

  async getChatHistory(token: string, sessionId: string): Promise<ChatHistory> {
    return this.request<ChatHistory>(`/chat/sessions/${sessionId}`, { method: "GET" }, token);
  }

  async sendChatMessage(token: string, sessionId: string, content: string): Promise<ChatMessageItem> {
    return this.request<ChatMessageItem>(`/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }, token);
  }
}

export const api = new ApiClient();
