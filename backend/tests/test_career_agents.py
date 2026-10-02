"""
Comprehensive Verification and Audit Tests for the LangGraph Multi-Agent Architecture.

Verifies:
1. State management (CareerAgentState tracking, messages, context, citations, token count)
2. Nodes (router, resume_advisor, job_match_advisor, interview_coach, skill_roadmap_agent, general_advisor, tool_executor, synthesizer)
3. Edges & Routing (conditional routing, multi-branch dispatch, fallback execution)
4. Tools (resume retrieval, ATS scoring, job search, skill gap, RAG vector query)
5. Independent agent execution
6. Unnecessary tool call prevention (conceptual and general questions make ZERO tool calls)
7. Error handling & resilience (safe error trapping in tools without crashing graph)
8. End-to-end multi-agent execution & API integration
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.resume import Resume
from app.services.career_agents import (
    CareerAgentState,
    execute_career_agent_graph,
    general_advisor_node,
    interview_coach_node,
    job_match_advisor_node,
    response_synthesizer_node,
    resume_advisor_node,
    router_node,
    tool_analyze_skill_gap,
    tool_executor_node,
    tool_query_ats_scorer,
    tool_retrieve_user_resume,
    tool_search_job_postings,
)
from tests.test_resume_pipeline import (
    get_authenticated_user_token,
)

# ============================================================================
# 1. ROUTER NODE TESTS
# ============================================================================

def test_router_classification_resume_optimization():
    """Verify router selects resume_advisor for resume and ATS queries."""
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "Can you review my resume and check my ATS score for formatting errors?",
        "intent": None,
        "selected_agent": None,
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = router_node(state)
    assert result["selected_agent"] == "resume_advisor"
    assert result["intent"] == "resume_optimization"


def test_router_classification_job_search():
    """Verify router selects job_match_advisor for job market queries."""
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "What companies are hiring for Python backend engineers right now?",
        "intent": None,
        "selected_agent": None,
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = router_node(state)
    assert result["selected_agent"] == "job_match_advisor"
    assert result["intent"] == "job_search"


def test_router_classification_interview_coaching():
    """Verify router selects interview_coach for interview questions."""
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "How do I use the STAR method to answer behavioral interview questions?",
        "intent": None,
        "selected_agent": None,
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = router_node(state)
    assert result["selected_agent"] == "interview_coach"
    assert result["intent"] == "interview_prep"


def test_router_classification_skill_roadmap():
    """Verify router selects skill_roadmap_agent for learning and upskilling queries."""
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "What skills do I need to learn to become a Principal AI Architect?",
        "intent": None,
        "selected_agent": None,
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = router_node(state)
    assert result["selected_agent"] == "skill_roadmap_agent"
    assert result["intent"] == "skill_roadmap"


def test_router_classification_general_mentorship():
    """Verify router selects general_advisor for greetings and broad mentoring."""
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "Hello! I am thinking about switching my career direction. How can you mentor me?",
        "intent": None,
        "selected_agent": None,
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = router_node(state)
    assert result["selected_agent"] == "general_advisor"
    assert result["intent"] == "general_advice"


# ============================================================================
# 2. INDEPENDENT AGENT TESTS & UNNECESSARY TOOL PREVENTION
# ============================================================================

def test_resume_advisor_conceptual_calls_zero_tools():
    """
    Verify that conceptual resume questions DO NOT call unnecessary database tools.
    """
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "What font and format should be used for ATS friendly resumes?",
        "intent": "resume_optimization",
        "selected_agent": "resume_advisor",
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = resume_advisor_node(state)
    assert len(result["tool_calls_requested"]) == 0, "Conceptual resume question must NOT request tools!"


def test_resume_advisor_personal_resume_schedules_retrieval():
    """
    Verify that personal resume questions schedule the retrieve_user_resume_tool.
    """
    user_id = str(uuid4())
    state: CareerAgentState = {
        "user_id": user_id,
        "query": "Can you score my resume and tell me what is missing?",
        "intent": "resume_optimization",
        "selected_agent": "resume_advisor",
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = resume_advisor_node(state)
    tool_names = [t["tool_name"] for t in result["tool_calls_requested"]]
    assert "retrieve_user_resume_tool" in tool_names


def test_job_match_advisor_does_not_call_ats_tool():
    """
    Verify that job matching schedules job search, but NEVER unnecessarily schedules ATS scoring.
    """
    user_id = str(uuid4())
    state: CareerAgentState = {
        "user_id": user_id,
        "query": "Find me remote jobs hiring Senior Backend Engineers",
        "intent": "job_search",
        "selected_agent": "job_match_advisor",
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = job_match_advisor_node(state)
    tool_names = [t["tool_name"] for t in result["tool_calls_requested"]]
    assert "search_job_postings_tool" in tool_names
    assert "query_ats_scorer_tool" not in tool_names, "Job search must NOT call ATS scorer!"


def test_interview_coach_conceptual_calls_zero_tools():
    """
    Verify that general interview prep (STAR method) makes ZERO tool calls.
    """
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "What is the STAR method and how do I structure my behavioral answers?",
        "intent": "interview_prep",
        "selected_agent": "interview_coach",
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = interview_coach_node(state)
    assert len(result["tool_calls_requested"]) == 0, "General interview prep must NOT call tools!"


def test_general_advisor_calls_zero_tools():
    """
    Verify that general advisor calls ZERO unnecessary tools for greetings/questions.
    """
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "Good morning! Can you explain how this AI Career Intelligence platform works?",
        "intent": "general_advice",
        "selected_agent": "general_advisor",
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }
    result = general_advisor_node(state)
    assert len(result["tool_calls_requested"]) == 0, "General advisor must make ZERO tool calls!"


# ============================================================================
# 3. INDEPENDENT TOOL TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_tool_retrieve_user_resume(db_session: AsyncSession):
    """Verify tool_retrieve_user_resume retrieves resume and parses skills."""
    user_id = uuid4()
    resume = Resume(
        user_id=user_id,
        original_filename="sarah_dev.pdf",
        file_path="/tmp/sarah_dev.pdf",
        status="parsed",
        version=1,
        raw_text="Sarah Dev. Python, Docker, Kubernetes developer.",
        parsed_data={"skills": ["Python", "Docker", "Kubernetes"]},
    )
    db_session.add(resume)
    await db_session.commit()

    res = await tool_retrieve_user_resume(db_session, str(user_id))
    assert res["status"] == "success"
    assert res["filename"] == "sarah_dev.pdf"
    assert "Python" in res["skills"]
    assert "Docker" in res["skills"]


@pytest.mark.asyncio
async def test_tool_query_ats_scorer():
    """Verify tool_query_ats_scorer computes scores and recommendations."""
    resume_text = """
    Jane Doe
    Skills: Python, FastAPI, Docker, PostgreSQL, Redis, Git
    Experience: Senior Software Engineer at FinTech Inc (2020-Present).
    Designed and deployed microservices handling 5M requests daily with 99.9% uptime.
    Education: B.S. in Computer Science, 2019.
    """
    job_desc = "Seeking Senior Python Engineer with Docker, Kubernetes, AWS, and FastAPI experience."

    res = await tool_query_ats_scorer(resume_text, job_desc)
    assert res["status"] == "success"
    assert res["overall_score"] > 50.0
    assert "matched_skills" in res
    assert "missing_skills" in res


@pytest.mark.asyncio
async def test_tool_search_job_postings(db_session: AsyncSession):
    """Verify tool_search_job_postings retrieves active listings from database."""
    job = Job(
        title="Staff AI Platform Engineer",
        company="AeroTech AI",
        location="Remote",
        description="Lead our AI infrastructure and LangGraph agents.",
        requirements="Python, LangChain, Kubernetes, Distributed Systems",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    res = await tool_search_job_postings(db_session, "Platform Engineer", limit=2)
    assert res["status"] == "success"
    assert res["count"] >= 1
    titles = [j["title"] for j in res["jobs"]]
    assert "Staff AI Platform Engineer" in titles


def test_tool_analyze_skill_gap():
    """Verify skill gap tool computes match percentage and missing skills."""
    user_skills = ["Python", "Docker", "FastAPI", "PostgreSQL"]
    target_reqs = ["Python", "Docker", "Kubernetes", "AWS"]

    gap = tool_analyze_skill_gap(user_skills, target_reqs)
    assert gap["status"] == "success"
    assert "python" in gap["matched_skills"]
    assert "docker" in gap["matched_skills"]
    assert "kubernetes" in gap["missing_skills"]
    assert "aws" in gap["missing_skills"]
    assert gap["match_percentage"] == 50.0


# ============================================================================
# 4. TOOL EXECUTOR NODE & ERROR RESILIENCE
# ============================================================================

@pytest.mark.asyncio
async def test_tool_executor_node_resilience(db_session: AsyncSession):
    """
    Verify tool_executor executes scheduled tools safely and handles unknown tools or errors without crashing.
    """
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "Review test query",
        "intent": "resume_optimization",
        "selected_agent": "resume_advisor",
        "messages": [],
        "context_data": {},
        "tool_calls_requested": [
            {"tool_name": "unknown_tool_xyz", "args": {}},
            {"tool_name": "analyze_skill_gap_tool", "args": {"resume_skills": ["Python"], "target_keywords": ["Go", "Python"]}},
        ],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }

    result = await tool_executor_node(state, db_session)
    assert len(result["tool_results"]) == 2
    assert result["tool_results"][0]["output"]["status"] == "error"
    assert result["tool_results"][1]["output"]["status"] == "success"
    assert "unknown_tool_xyz" in result["tool_calls_made"]
    assert "analyze_skill_gap_tool" in result["tool_calls_made"]
    assert len(result["tool_calls_requested"]) == 0  # Cleared


# ============================================================================
# 5. RESPONSE SYNTHESIZER NODE
# ============================================================================

@pytest.mark.asyncio
async def test_response_synthesizer_produces_structured_output():
    """
    Verify response synthesizer produces markdown with citations and recommendations.
    """
    state: CareerAgentState = {
        "user_id": str(uuid4()),
        "query": "How do I improve my interview performance?",
        "intent": "interview_prep",
        "selected_agent": "interview_coach",
        "messages": [],
        "context_data": {
            "agent_notes": "Emphasizing STAR technique",
        },
        "tool_calls_requested": [],
        "tool_results": [],
        "tool_calls_made": [],
        "sources": [
            {
                "source_id": "Prep Guide",
                "title": "STAR Method Behavioral Guide",
                "doc_type": "career_guide",
                "snippet": "Structure responses into Situation, Task, Action, and Result.",
            }
        ],
        "final_response": None,
        "error": None,
        "token_count": 0,
    }

    result = await response_synthesizer_node(state)
    assert result["final_response"] is not None
    assert "### 🎯" in result["final_response"]
    assert "STAR" in result["final_response"]
    assert result["token_count"] > 10


# ============================================================================
# 6. COMPLETE LANGGRAPH WORKFLOW END-TO-END TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_complete_workflow_general_greeting_calls_zero_tools(db_session: AsyncSession):
    """
    Workflow Test 1: User greeting -> Router -> General Advisor -> 0 tools -> Synthesizer -> Response.
    Verifies that agents do not call unnecessary tools.
    """
    user_id = uuid4()
    query = "Hello, what features do you provide to assist my career growth?"

    res = await execute_career_agent_graph(db_session, user_id, query)

    assert res["selected_agent"] == "general_advisor"
    assert res["intent"] == "general_advice"
    assert len(res["tool_calls_made"]) == 0, "General query must NOT execute any tools!"
    assert "### 🎯 Senior AI Career Mentor" in res["content"]
    assert len(res["content"]) > 100


@pytest.mark.asyncio
async def test_complete_workflow_job_search_with_resume_matching(db_session: AsyncSession):
    """
    Workflow Test 2: User job fit question -> Router -> Job Match Advisor -> Search Job + Resume Tools -> Synthesizer.
    """
    user_id = uuid4()

    # Seed candidate resume
    resume = Resume(
        user_id=user_id,
        original_filename="marcus_ml_engineer.pdf",
        file_path="/tmp/marcus_ml.pdf",
        status="parsed",
        version=1,
        raw_text="Marcus Vance. ML Engineer with Python, PyTorch, Kubernetes, FastAPI, and Docker experience.",
        parsed_data={"skills": ["Python", "PyTorch", "Kubernetes", "FastAPI", "Docker"]},
    )
    db_session.add(resume)

    # Seed job opening
    job = Job(
        title="Senior Machine Learning Platform Engineer",
        company="CognitiveLabs",
        location="Remote",
        description="Looking for an ML engineer with PyTorch and Kubernetes experience.",
        requirements="Python, PyTorch, Docker, Kubernetes, MLOps",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    query = "What ML jobs are available and do my skills qualify me to apply?"
    res = await execute_career_agent_graph(db_session, user_id, query)

    assert res["selected_agent"] == "job_match_advisor"
    assert res["intent"] == "job_search"
    # Must have executed job search and resume retrieval
    assert "search_job_postings_tool" in res["tool_calls_made"]
    assert "retrieve_user_resume_tool" in res["tool_calls_made"]
    # Must NOT have called ATS scorer unnecessarily
    assert "query_ats_scorer_tool" not in res["tool_calls_made"]
    assert res["sources"]["retrieved_count"] >= 1
    assert len(res["content"]) > 100


@pytest.mark.asyncio
async def test_complete_workflow_resume_ats_analysis(db_session: AsyncSession):
    """
    Workflow Test 3: User resume optimization -> Router -> Resume Advisor -> Resume & ATS Scorer Tools -> Synthesizer.
    """
    user_id = uuid4()

    resume = Resume(
        user_id=user_id,
        original_filename="candidate_cv.pdf",
        file_path="/tmp/candidate_cv.pdf",
        status="parsed",
        version=1,
        raw_text="""
        Devon Scott
        Summary: Full stack developer with 4 years building web apps.
        Skills: Python, TypeScript, React, PostgreSQL, Docker, Git.
        Experience: Software Engineer at Acme Tech. Built REST APIs and dashboards.
        Education: B.S. in Computer Science.
        """,
        parsed_data={"skills": ["Python", "TypeScript", "React", "PostgreSQL", "Docker", "Git"]},
    )
    db_session.add(resume)
    await db_session.commit()

    query = "Can you review my resume and score my ATS compatibility for a Senior Python and Docker developer job description?"
    res = await execute_career_agent_graph(db_session, user_id, query)

    assert res["selected_agent"] == "resume_advisor"
    assert res["intent"] == "resume_optimization"
    assert "retrieve_user_resume_tool" in res["tool_calls_made"]
    assert "query_ats_scorer_tool" in res["tool_calls_made"]
    assert "Candidate Resume" in res["content"] or "ATS Scoring" in res["content"]
    assert res["sources"]["retrieved_count"] >= 1


# ============================================================================
# 7. CHAT API ENDPOINT INTEGRATION TEST
# ============================================================================

@pytest.mark.asyncio
async def test_chat_api_endpoint_executes_langgraph_multi_agent(client: AsyncClient, db_session: AsyncSession):
    """
    Verify that POST /api/v1/chat/sessions/{session_id}/messages triggers the multi-agent graph.
    """
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a chat session
    create_res = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Multi-Agent Advisory Session"},
        headers=headers,
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    # 2. Send message asking for interview coaching
    msg_res = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "How do I prepare for a Senior Backend Engineering system design interview using the STAR method?"},
        headers=headers,
    )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()

    assert msg_data["role"] == "assistant"
    assert len(msg_data["content"]) > 100
    assert "STAR" in msg_data["content"] or "Interview" in msg_data["content"]
    assert msg_data["token_count"] > 10
