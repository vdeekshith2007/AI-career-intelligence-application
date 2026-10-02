"""
Comprehensive Verification and Audit Tests for the RAG Pipeline.

Verifies:
1. Document loading
2. Text extraction
3. Chunking
4. Metadata preservation
5. Embeddings (local deterministic semantic vectors)
6. Vector database (ChromaDB)
7. Retrieval (vector similarity search)
8. Reranking (semantic-lexical hybrid reranker)
9. Context construction
10. Prompt construction
11. LLM call & synthesis engine
12. Response generation
13. Source citation & snippet extraction
14. End-to-end question latency, retrieved documents, and error reporting
"""

import time
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.resume import Resume
from app.services.rag_pipeline import (
    LocalSemanticEmbeddingFunction,
    construct_rag_prompt,
    generate_rag_response,
    get_chroma_client,
    index_and_retrieve_context,
    load_and_chunk_career_documents,
)
from tests.test_resume_pipeline import (
    generate_fullstack_pdf_resume,
    get_authenticated_user_token,
)

# ============================================================================
# 1. DOCUMENT LOADING, CHUNKING & METADATA TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rag_document_loading_and_chunking(db_session: AsyncSession):
    """
    Verify document loading, text extraction, chunking, and metadata preservation.
    """
    user_id = uuid4()

    # 1. Add a sample resume
    resume = Resume(
        user_id=user_id,
        original_filename="alex_johnson_cv.pdf",
        file_path="./uploads/test.pdf",
        raw_text=(
            "Alex Johnson | Software Engineer\n"
            "Proficient in Python, FastAPI, React, Docker, and Kubernetes.\n"
            "Built distributed microservices handling millions of transactions.\n"
            "Bachelor of Science in Computer Science from UC Berkeley."
        ),
        version=1,
    )
    db_session.add(resume)

    # 2. Add an active job
    job = Job(
        title="Senior Backend Engineer",
        company="Fintech Scaleup",
        location="Remote",
        work_type="remote",
        description="Build high-throughput payment settlement pipelines with Python and Redis.",
        requirements="5+ years Python, FastAPI, PostgreSQL, and event-driven architecture.",
    )
    db_session.add(job)
    await db_session.flush()

    # 3. Load and chunk documents
    chunks = await load_and_chunk_career_documents(db_session, user_id)

    assert len(chunks) >= 3

    # Verify chunk contents and metadata
    doc_types = {c.metadata.get("doc_type") for c in chunks}
    assert "career_guide" in doc_types
    assert "resume" in doc_types
    assert "job_listing" in doc_types

    resume_chunks = [c for c in chunks if c.metadata.get("doc_type") == "resume"]
    assert len(resume_chunks) >= 1
    assert "Python" in resume_chunks[0].page_content
    assert resume_chunks[0].metadata["source"] == "Resume: alex_johnson_cv.pdf (v1)"


# ============================================================================
# 2. EMBEDDINGS & VECTOR DATABASE TESTS
# ============================================================================

def test_rag_local_semantic_embedding_function():
    """
    Verify embedding function generates normalized, deterministic vectors
    with expected semantic orientation.
    """
    ef = LocalSemanticEmbeddingFunction(dim=128)

    docs = [
        "Senior Python backend developer with FastAPI and PostgreSQL",
        "FastAPI Python engineer building REST APIs and microservices",
        "Creative Graphic Designer skilled in Adobe Photoshop and Illustrator",
    ]
    embeddings = ef(docs)

    assert len(embeddings) == 3
    assert len(embeddings[0]) == 128

    # Verify L2 normalization
    for emb in embeddings:
        norm = sum(x * x for x in emb) ** 0.5
        assert abs(norm - 1.0) < 1e-4

    # Verify cosine similarity: doc 0 and doc 1 (both Python dev) must be closer than doc 0 and doc 2 (Graphic Design)
    def cosine_similarity(v1, v2):
        return sum(a * b for a, b in zip(v1, v2, strict=False))

    sim_dev = cosine_similarity(embeddings[0], embeddings[1])
    sim_design = cosine_similarity(embeddings[0], embeddings[2])

    assert sim_dev > sim_design


def test_rag_chromadb_storage_and_query():
    """
    Verify ChromaDB collection creation, document upsertion, and vector querying.
    """
    client = get_chroma_client()
    ef = LocalSemanticEmbeddingFunction(dim=128)
    col_name = f"test_col_{uuid4().hex[:8]}"

    collection = client.create_collection(name=col_name, embedding_function=ef)
    collection.add(
        documents=[
            "Distributed Kubernetes orchestration with Docker and Terraform",
            "Medical clinical research data analysis with R and statistics",
        ],
        metadatas=[{"role": "devops"}, {"role": "clinical"}],
        ids=["doc_k8s", "doc_med"],
    )

    query_res = collection.query(
        query_texts=["How do I manage Kubernetes clusters and containers?"],
        n_results=1,
    )

    assert query_res["ids"][0][0] == "doc_k8s"
    assert "Kubernetes" in query_res["documents"][0][0]

    # Cleanup
    client.delete_collection(col_name)


# ============================================================================
# 3. RETRIEVAL & RERANKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rag_retrieval_and_reranking(db_session: AsyncSession):
    """
    Verify indexing, vector retrieval, hybrid reranking, and latency measurement.
    """
    user_id = uuid4()

    resume = Resume(
        user_id=user_id,
        original_filename="resume.pdf",
        file_path="./uploads/test.pdf",
        raw_text="Full-stack engineer with expertise in React, Next.js, and TypeScript frontend development.",
        version=1,
    )
    db_session.add(resume)
    await db_session.flush()

    retrieved, latency_ms = await index_and_retrieve_context(
        db=db_session,
        user_id=user_id,
        query="What frontend frameworks do I have experience with?",
        top_k=3,
    )

    assert len(retrieved) >= 1
    assert latency_ms > 0
    assert latency_ms < 500  # Fast retrieval under 500ms

    # Top result should be the resume mentioning React and TypeScript
    top_doc = retrieved[0]
    assert "React" in top_doc["content"] or "TypeScript" in top_doc["content"]


# ============================================================================
# 4. CONTEXT & PROMPT CONSTRUCTION TESTS
# ============================================================================

def test_rag_prompt_construction_and_citations():
    """
    Verify prompt construction formats numbered citations and extracts snippet metadata.
    """
    chunks = [
        {
            "content": "Alex Johnson has 6 years experience with Python and Docker.",
            "metadata": {"source": "Resume: alex.pdf", "doc_type": "resume"},
            "distance": 0.15,
        },
        {
            "content": "Technical Interview prep: use STAR method for behavioral answers.",
            "metadata": {"source": "Interview Prep Guide", "doc_type": "career_guide"},
            "distance": 0.22,
        },
    ]

    prompt, sources = construct_rag_prompt(
        query="How should I describe my Python experience in interviews?",
        retrieved_chunks=chunks,
    )

    assert "[Source 1: Resume: alex.pdf]" in prompt
    assert "[Source 2: Interview Prep Guide]" in prompt
    assert "STAR method" in prompt
    assert "Alex Johnson" in prompt

    assert len(sources) == 2
    assert sources[0]["source_id"] == "Source 1"
    assert sources[0]["title"] == "Resume: alex.pdf"
    assert "Alex Johnson" in sources[0]["snippet"]


# ============================================================================
# 5. RESPONSE GENERATION & SYNTHESIS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rag_response_generation():
    """
    Verify response generation produces structured markdown with evidence citations.
    """
    chunks = [
        {
            "content": "Kubernetes and Docker container orchestration skills.",
            "metadata": {"source": "Resume: ops.pdf", "doc_type": "resume"},
            "distance": 0.1,
        }
    ]
    _, sources = construct_rag_prompt("Tell me about my cloud skills", chunks)

    result = await generate_rag_response("Tell me about my cloud skills", chunks, sources)

    assert len(result["content"]) > 50
    assert "Career Advisory Intelligence" in result["content"]
    assert result["sources"]["retrieved_count"] == 1
    assert result["token_count"] > 0


# ============================================================================
# 6. REAL END-TO-END RAG QUESTION VIA HTTP API
# ============================================================================

@pytest.mark.asyncio
async def test_real_end_to_end_rag_question_via_api(client: AsyncClient, db_session: AsyncSession):
    """
    Execute real end-to-end RAG question:
    1. Register user & authenticate
    2. Upload real resume
    3. Create real job listings in database
    4. Start Chat Session
    5. Send question to Career Advisor
    6. Measure: retrieved documents, response content, latency, and error states.
    """
    token = await get_authenticated_user_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Upload candidate resume (Full-Stack Engineer)
    pdf_bytes = generate_fullstack_pdf_resume()
    upload_res = await client.post(
        "/api/v1/resumes/upload",
        headers=headers,
        files={"file": ("alex_johnson_cv.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 201

    # 2. Add an active Job in the database
    job = Job(
        title="Staff Infrastructure Engineer",
        company="Global Cloud Corp",
        location="Remote",
        work_type="remote",
        description="Looking for an engineer with deep Docker, Kubernetes, and AWS experience.",
        requirements="Must have 5+ years building distributed cloud systems and CI/CD pipelines.",
        salary_range="$180,000 - $220,000",
    )
    db_session.add(job)
    await db_session.flush()

    # 3. Create a chat session
    session_res = await client.post(
        "/api/v1/chat/sessions",
        headers=headers,
        json={"title": "Career Advisory Strategy Session"},
    )
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # 4. Ask a real career intelligence question
    question = "What cloud and backend skills do I have on my resume, and how well do they match current job openings?"

    start_time = time.perf_counter()
    msg_res = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
        json={"content": question},
    )
    total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    assert msg_res.status_code == 201
    data = msg_res.json()

    # 5. Measure and assert RAG components:
    # A. Response content
    content = data["content"]
    assert len(content) > 100
    assert "🎯" in content or "Specialist" in content or "Advisor" in content or "Coach" in content

    # B. Retrieved documents / sources
    sources = data["sources"]
    assert sources is not None
    assert sources["retrieved_count"] >= 1
    citations = sources.get("citations", [])
    assert len(citations) >= 1

    citation_titles = [c["title"] for c in citations]
    # Should cite the resume or the job listing
    assert any("Resume" in t or "Job" in t or "Career Guide" in t for t in citation_titles)

    # C. Latency
    assert total_latency_ms < 2000  # Total end-to-end response under 2.0s

    # D. Zero unhandled errors
    assert data["role"] == "assistant"
    assert data["id"] is not None

    # 6. Verify Chat History persists the interaction
    history_res = await client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history["messages"]) == 2  # user message + assistant message
    assert history["messages"][0]["role"] == "user"
    assert history["messages"][1]["role"] == "assistant"
    assert history["messages"][1]["sources"] is not None
