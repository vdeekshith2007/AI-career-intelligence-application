"""
ATS (Applicant Tracking System) Scoring Engine.

Implements realistic, deterministic, multi-dimensional scoring of resumes
both independently (general industry benchmark) and targeted against specific
job descriptions.

Pipeline:
Resume Text & Parsed Data
→ Skill & Keyword Extraction
→ Job Description Analysis (Targeted vs General)
→ Keyword Matching & Missing Skills Identification
→ Dimensional Scoring (Keyword, Format, Experience, Impact, Education)
→ Weighted Composite Calculation
→ Tailored Section Feedback & Actionable Recommendations
"""

import re
from typing import Any

from app.services.resume_parser import extract_skills

# Standard core industry technical skills for general benchmark scoring
BENCHMARK_INDUSTRY_KEYWORDS = [
    "python", "javascript", "typescript", "react", "next.js", "fastapi",
    "sql", "postgresql", "docker", "kubernetes", "aws", "git", "ci/cd",
    "rest", "graphql", "machine learning", "agile", "testing", "api", "linux"
]

# Action verbs indicating ownership, execution, and leadership
STRONG_ACTION_VERBS = [
    "built", "designed", "implemented", "optimized", "managed", "led",
    "developed", "created", "architected", "deployed", "scaled", "automated",
    "mentored", "orchestrated", "spearheaded", "engineered", "refactored",
    "streamlined", "delivered", "launched"
]

# Regex for detecting quantifiable impact metrics (percentages, dollar amounts, multiples, numbers)
METRIC_PATTERNS = [
    r"\d+(?:\.\d+)?%",                         # e.g., 45%, 100%
    r"\$\d+(?:\.\d+)?[MBkK]?",                 # e.g., $50M, $10k, $2.5M
    r"\b\d+(?:\.\d+)?x\b",                     # e.g., 10x, 2.5x
    r"\b\d+(?:\.\d+)?[MBkK]?\+",               # e.g., 10M+, 500+
    r"\b(?:reduced|increased|improved|saved|accelerated|cutting|handling)\b[^\.\n]*?\b\d+",
]


def score_resume(
    raw_text: str,
    parsed_data: dict[str, Any] | None = None,
    job_description: str | None = None,
) -> dict[str, Any]:
    """
    Score a resume across all ATS dimensions.

    Returns a dictionary containing:
    - overall_score (float, 0.0 - 100.0)
    - format_score (float, 0.0 - 100.0)
    - keyword_score (float, 0.0 - 100.0)
    - experience_score (float, 0.0 - 100.0)
    - education_score (float, 0.0 - 100.0)
    - impact_score (float, 0.0 - 100.0)
    - section_feedback (dict)
    - improvement_suggestions (dict containing top_recommendations, matching_skills, missing_skills)
    """
    cleaned_text = (raw_text or "").strip()
    words = cleaned_text.split()
    word_count = len(words)

    # ------------------------------------------------------------------------
    # 1. EMPTY RESUME SAFETY CHECK
    # ------------------------------------------------------------------------
    if not cleaned_text or word_count < 5:
        return {
            "overall_score": 0.0,
            "format_score": 0.0,
            "keyword_score": 0.0,
            "experience_score": 0.0,
            "education_score": 0.0,
            "impact_score": 0.0,
            "section_feedback": {
                "contact_info": "No contact information detected.",
                "work_experience": "No work experience detected.",
                "skills_section": "No technical skills detected.",
                "education": "No education section detected.",
            },
            "improvement_suggestions": {
                "top_recommendations": [
                    "Resume appears to be empty or unreadable. Please upload a valid document containing your work history, skills, and education.",
                    "Ensure text in PDF/DOCX is selectable and not an image-only scanned document.",
                ],
                "keywords_found": [],
                "matching_skills": [],
                "missing_skills": [],
            },
        }

    text_lower = cleaned_text.lower()

    # Extract or retrieve candidate's skills
    if parsed_data and "skills" in parsed_data and "all" in parsed_data["skills"]:
        candidate_skills = list(parsed_data["skills"]["all"])
    else:
        candidate_skills = extract_skills(cleaned_text)["all"]
    candidate_skills_lower = {s.lower() for s in candidate_skills}

    # ------------------------------------------------------------------------
    # 2. KEYWORD & SKILL MATCHING (JOB DESCRIPTION VS GENERAL BENCHMARK)
    # ------------------------------------------------------------------------
    keywords_found: list[str] = []
    matching_skills: list[str] = []
    missing_skills: list[str] = []

    if job_description and job_description.strip():
        # Targeted ATS matching against the provided job description
        job_extracted = extract_skills(job_description)
        job_skills = job_extracted["all"]

        if job_skills:
            for js in job_skills:
                # Direct match or word match in candidate skills or text
                js_lower = js.lower()
                pattern = rf"(?<![\w\.\+#]){re.escape(js_lower)}(?![\w\.\+#])"
                if js_lower in candidate_skills_lower or re.search(pattern, text_lower):
                    matching_skills.append(js)
                else:
                    missing_skills.append(js)

            # Keyword score = matching skills / total job required skills
            match_ratio = len(matching_skills) / float(len(job_skills))
            keyword_score = min(100.0, round(match_ratio * 100.0, 1))
            keywords_found = matching_skills
        else:
            # Fallback if job description has no recognized technical skills:
            # Extract common technical and domain words (> 3 chars)
            job_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", job_description.lower()))
            resume_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", text_lower))
            overlap = job_tokens.intersection(resume_tokens)
            keyword_score = min(100.0, round((len(overlap) / max(1, len(job_tokens))) * 100.0, 1))
            keywords_found = list(overlap)[:10]

    else:
        # General ATS benchmark against 20 core industry technical keywords
        keywords_found = [
            kw for kw in BENCHMARK_INDUSTRY_KEYWORDS
            if re.search(rf"(?<![\w\.\+#]){re.escape(kw)}(?![\w\.\+#])", text_lower)
        ]
        # Benchmark score: 10 detected technical keywords = 100%
        keyword_score = min(100.0, round((len(keywords_found) / 10.0) * 100.0, 1))

    # ------------------------------------------------------------------------
    # 3. FORMATTING SCORE (Section Parseability & Machine Readability)
    # ------------------------------------------------------------------------
    has_contact = bool(
        "@" in text_lower
        or "email" in text_lower
        or "phone" in text_lower
        or (parsed_data and parsed_data.get("contact_info", {}).get("email"))
    )
    has_exp = bool(
        "experience" in text_lower
        or "employment" in text_lower
        or "work history" in text_lower
        or (parsed_data and len(parsed_data.get("experience", [])) > 0)
    )
    has_edu = bool(
        "education" in text_lower
        or "university" in text_lower
        or "degree" in text_lower
        or "college" in text_lower
        or (parsed_data and len(parsed_data.get("education", [])) > 0)
    )
    has_skills = bool(
        "skills" in text_lower
        or "technologies" in text_lower
        or len(candidate_skills) > 0
    )

    format_items = [has_contact, has_exp, has_edu, has_skills]
    present_count = sum(1 for item in format_items if item)
    format_score = round((present_count / float(len(format_items))) * 100.0, 1)

    # ------------------------------------------------------------------------
    # 4. EXPERIENCE SCORE (Action Verbs & Structural Roles)
    # ------------------------------------------------------------------------
    verb_count = sum(
        1 for v in STRONG_ACTION_VERBS
        if re.search(rf"\b{re.escape(v)}\b", text_lower)
    )

    if not has_exp and verb_count == 0:
        # Incomplete resume with no experience section and no action verbs
        experience_score = 0.0
    elif not has_exp and verb_count > 0:
        # Some action verbs present without a structured section
        experience_score = min(40.0, round(verb_count * 5.0, 1))
    else:
        # Experience section present: base 40 + points for strong action verbs
        base_exp = 40.0
        # If multiple jobs detected in parsed_data
        if parsed_data and len(parsed_data.get("experience", [])) >= 2:
            base_exp = 55.0
        experience_score = min(100.0, round(base_exp + (verb_count * 6.0), 1))

    # ------------------------------------------------------------------------
    # 5. EDUCATION SCORE
    # ------------------------------------------------------------------------
    if not has_edu:
        education_score = 0.0
    else:
        has_advanced = bool(re.search(r"\b(Ph\.?D|Doctorate|Master|M\.?S|M\.?A|MBA)\b", cleaned_text, re.IGNORECASE))
        has_bachelors = bool(re.search(r"\b(Bachelor|B\.?S|B\.?A|B\.?Tech|B\.?E)\b", cleaned_text, re.IGNORECASE))
        if has_advanced:
            education_score = 100.0
        elif has_bachelors:
            education_score = 90.0
        else:
            education_score = 75.0

    # ------------------------------------------------------------------------
    # 6. IMPACT SCORE (Metrics, Results, Achievements)
    # ------------------------------------------------------------------------
    metrics_count = 0
    for pattern in METRIC_PATTERNS:
        metrics_count += len(re.findall(pattern, cleaned_text, re.IGNORECASE))

    if verb_count == 0 and metrics_count == 0:
        impact_score = 0.0
    else:
        # Balanced formula: up to 50 pts for action verbs, up to 50 pts for quantifiable metrics
        impact_from_verbs = min(50.0, verb_count * 5.0)
        impact_from_metrics = min(50.0, metrics_count * 15.0)
        impact_score = min(100.0, round(impact_from_verbs + impact_from_metrics, 1))

    # ------------------------------------------------------------------------
    # 7. OVERALL COMPOSITE WEIGHTED SCORE
    # ------------------------------------------------------------------------
    # Weights: Keywords (35%), Formatting (25%), Experience (20%), Impact (10%), Education (10%)
    overall_score = round(
        (keyword_score * 0.35)
        + (format_score * 0.25)
        + (experience_score * 0.20)
        + (impact_score * 0.10)
        + (education_score * 0.10),
        1,
    )

    # ------------------------------------------------------------------------
    # 8. SECTION FEEDBACK & ACTIONABLE RECOMMENDATIONS
    # ------------------------------------------------------------------------
    section_feedback = {
        "contact_info": "Complete contact information detected." if has_contact else "Missing contact email, phone, or location.",
        "work_experience": f"Found {verb_count} strong action verbs across work experience." if verb_count > 0 else "Include more quantifiable impact and strong action verbs (e.g., built, deployed, optimized).",
        "skills_section": f"Detected {len(candidate_skills)} technical and professional skills." if candidate_skills else "Add a dedicated technical skills section.",
        "education": "Education credentials verified." if has_edu else "Ensure your highest degree and institution are clearly stated.",
    }

    recommendations: list[str] = []

    # Targeted advice based on score deficits
    if missing_skills:
        recs_missing = ", ".join(missing_skills[:5])
        recommendations.append(f"Target role requires skills missing from your resume: {recs_missing}. Consider adding related projects or experience.")

    if not has_contact:
        recommendations.append("Add complete contact details (email, phone number, location, and LinkedIn/GitHub links).")

    if not has_edu:
        recommendations.append("Include an Education section indicating your degree, university, and graduation year.")

    if not has_exp:
        recommendations.append("Include a detailed Work Experience section with role titles, companies, and employment dates.")
    elif verb_count < 3:
        recommendations.append("Use more strong action verbs (e.g., architected, scaled, engineered) to highlight your direct contributions.")

    if metrics_count == 0:
        recommendations.append("Quantify your achievements with numbers, percentages, or dollar amounts (e.g., 'reduced latency by 40%').")

    if not recommendations:
        recommendations.append("Resume demonstrates strong ATS compatibility across structure, keywords, and quantifiable achievements.")

    improvement_suggestions = {
        "top_recommendations": recommendations,
        "keywords_found": keywords_found,
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
    }

    return {
        "overall_score": overall_score,
        "format_score": format_score,
        "keyword_score": keyword_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "impact_score": impact_score,
        "section_feedback": section_feedback,
        "improvement_suggestions": improvement_suggestions,
    }
