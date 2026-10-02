import urllib.request
import json
import io
import time

BASE = "https://ai-career-backend-codr.onrender.com/api/v1"

def req(endpoint, method="GET", data=None, token=None, files=None):
    url = f"{BASE}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if files:
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        buf = io.BytesIO()
        for field, (fname, fcontent, ftype) in files.items():
            buf.write(f"--{boundary}\r\n".encode())
            buf.write(f'Content-Disposition: form-data; name="{field}"; filename="{fname}"\r\n'.encode())
            buf.write(f"Content-Type: {ftype}\r\n\r\n".encode())
            buf.write(fcontent if isinstance(fcontent, bytes) else fcontent.encode("utf-8"))
            buf.write(b"\r\n")
        buf.write(f"--{boundary}--\r\n".encode())
        body = buf.getvalue()
    elif data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def make_valid_pdf(resume_text: str) -> bytes:
    # A standard conforming PDF byte stream with text
    escaped_text = resume_text.replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 10 Tf 50 720 Td ({escaped_text}) Tj ET"
    stream_bytes = stream.encode("latin-1")
    
    obj4 = f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n{stream}\nendstream\nendobj\n"
    
    pdf_header = "%PDF-1.4\n"
    obj1 = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    obj5 = "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    
    # Calculate byte offsets
    o1 = len(pdf_header)
    o2 = o1 + len(obj1)
    o3 = o2 + len(obj2)
    o4 = o3 + len(obj3)
    o5 = o4 + len(obj4)
    xref_pos = o5 + len(obj5)
    
    xref = (
        f"xref\n0 6\n"
        f"0000000000 65535 f \n"
        f"{o1:010d} 00000 n \n"
        f"{o2:010d} 00000 n \n"
        f"{o3:010d} 00000 n \n"
        f"{o4:010d} 00000 n \n"
        f"{o5:010d} 00000 n \n"
    )
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    
    full_pdf = (pdf_header + obj1 + obj2 + obj3 + obj4 + obj5 + xref + trailer).encode("latin-1")
    return full_pdf

print("=" * 60)
print("LIVE VERIFICATION: https://ai-career-backend-codr.onrender.com")
print("=" * 60)

# 1. Health
s, r = req("/health")
assert s == 200
print(f"1. [PASS] Health check: {r['status']} (v{r['version']})")

# 2. Register
email = f"candidate.{int(time.time())}@careertest.com"
s, r = req("/auth/register", "POST", {"email": email, "password": "Password123!", "full_name": "Senior Full Stack Dev"})
assert s == 201
print(f"2. [PASS] Register: {r['email']}")

# 3. Login
s, r = req("/auth/login", "POST", {"email": email, "password": "Password123!"})
assert s == 200
token = r["access_token"]
print("3. [PASS] Login: JWT acquired")

# 4. Profile
s, r = req("/auth/me", token=token)
assert s == 200
print(f"4. [PASS] Profile: {r['full_name']} | Role: {r['role']}")

# 5. List Seeded Jobs
s, r = req("/jobs", token=token)
assert s == 200
print(f"5. [PASS] Seeded Jobs in DB: {len(r)} listings available")

# 6. Upload PDF Resume
sample_resume = "Alex Dev, Senior Full Stack Engineer. Skills: Python, FastAPI, React, Next.js, Docker, PostgreSQL."
pdf_bytes = make_valid_pdf(sample_resume)
s, r = req("/resumes/upload", "POST", token=token, files={"file": ("alex_dev_resume.pdf", pdf_bytes, "application/pdf")})
assert s == 201
resume_id = r["id"]
print(f"6. [PASS] Upload Resume: ID {resume_id} ({r['original_filename']})")

# 7. ATS Analysis
s, r = req(f"/resumes/{resume_id}/analyze", "POST", {}, token=token)
assert s == 200
print(f"7. [PASS] ATS Score: {r['overall_score']}% | Breakdown: format={r.get('format_score')}, keyword={r.get('keyword_score')}")

# 8. AI Recommendations & Match Ranking
s, r = req("/jobs/recommendations", token=token)
assert s == 200
print(f"8. [PASS] Job Recommendations: {len(r)} roles evaluated")
for j in r[:2]:
    print(f"   -> {j['title']} @ {j['company']} (Score: {j.get('match_score')}%)")

# 9. Create Chat Session
s, r = req("/chat/sessions", "POST", {"title": "Interview Prep Advice"}, token=token)
assert s == 201
session_id = r["id"]
print(f"9. [PASS] Chat Session: {session_id}")

# 10. AI Career Advisor Message
s, r = req(f"/chat/sessions/{session_id}/messages", "POST", {"content": "Give me a quick 2-bullet summary on how to optimize my resume."}, token=token)
assert s in (200, 201)
safe_advisor_text = r['content'][:80].replace(chr(10), ' ').encode('ascii', 'replace').decode('ascii')
print(f"10. [PASS] AI Advisor: {safe_advisor_text}...")

print("=" * 60)
print("ALL 10 VERIFICATIONS PASSED ON LIVE RENDER DEPLOYMENT!")
print("=" * 60)
