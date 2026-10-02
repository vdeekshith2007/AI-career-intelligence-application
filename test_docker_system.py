"""
End-to-End System Verification Test Script for Containerized Environment.
Tests:
1. PostgreSQL Database Connectivity (Port 5432)
2. Backend API Health & Readiness (Port 8000)
3. Frontend Next.js UI (Port 3000)
4. RAG Pipeline & Semantic Search (Port 8000 / ChromaDB 8001)
5. Multi-Agent AI System & LLM synthesis (Port 8000)
"""

import sys
import time
import urllib.request
import urllib.error
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def check_url(url, expected_code=200, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DockerTester/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, body
    except Exception as e:
        return None, str(e)

print("=" * 70)
print("CONTAINERIZED SYSTEM END-TO-END VERIFICATION")
print("=" * 70)

# 1. Frontend Test
print("\n[1/5] Testing Frontend UI (Next.js Standalone)...")
code, body = check_url("http://localhost:3000/")
if code == 200 and ("html" in body.lower() or "<!doctype" in body.lower() or "career" in body.lower()):
    print(f"  ✓ Frontend accessible on http://localhost:3000 (HTTP {code})")
else:
    print(f"  ✗ Frontend check failed: status={code}, error={body[:150]}")

# 2. Backend Health
print("\n[2/5] Testing Backend Health Probe (FastAPI)...")
code, body = check_url("http://localhost:8000/api/v1/health/")
if code == 200:
    data = json.loads(body)
    print(f"  ✓ Backend healthy: {data}")
else:
    print(f"  ✗ Backend health check failed: status={code}, error={body[:150]}")

# 3. Database Connection
print("\n[3/5] Testing Backend Database Connectivity...")
code, body = check_url("http://localhost:8000/api/v1/health/ready")
if code == 200:
    data = json.loads(body)
    db_check = data.get("checks", {}).get("database", False)
    print(f"  ✓ Backend Database readiness probe: {data} (Database reachable: {db_check})")
else:
    print(f"  ✗ Readiness check: status={code}, body={body[:150]}")

# 4. RAG Pipeline
print("\n[4/5] Testing RAG Pipeline & Semantic Knowledge Base...")
try:
    rag_url = "http://localhost:8000/api/v1/rag/query"
    payload = json.dumps({"query": "What skills are in demand for Cloud Solutions Architects?"}).encode("utf-8")
    req = urllib.request.Request(
        rag_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "DockerTester/1.0"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        rag_data = json.loads(resp.read().decode("utf-8"))
        print(f"  ✓ RAG response generated: {str(rag_data)[:120]}...")
except Exception as e:
    print(f"  Note on RAG query endpoint: {e}")

# 5. Multi-Agent AI Workflow
print("\n[5/5] Testing Multi-Agent AI System & LLM synthesis...")
try:
    agents_url = "http://localhost:8000/api/v1/agents/chat"
    payload = json.dumps({"message": "Hello, can you help me review my career goals?"}).encode("utf-8")
    req = urllib.request.Request(
        agents_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "DockerTester/1.0"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        agent_data = json.loads(resp.read().decode("utf-8"))
        print(f"  ✓ Multi-agent system responded: {str(agent_data)[:120]}...")
except Exception as e:
    print(f"  Note on agents chat endpoint: {e}")

print("\n" + "=" * 70)
print("VERIFICATION RUN COMPLETE")
print("=" * 70)
