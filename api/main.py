"""
Inspection Intelligence - FastAPI Backend
Exposes all pipeline and model modules as REST API endpoints on port 8000
"""
import sys
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── path setup so all local modules resolve ────────────────────────────────────
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ── pipeline imports ────────────────────────────────────────────────────────────
from pipeline.extract import simple_extract
from pipeline.loader import (
    extract_pdf_text,
    get_image_counts,
    get_image_samples,
    load_sample_reports,
)

# ── model imports ───────────────────────────────────────────────────────────────
from models import RAGQuery
from models.defect_extractor import DefectExtractor
from models.document_processor import DocumentProcessor, process_uploaded_file
from models.rag_engine import RAGEngine
from models.risk import risk_score
from models.risk_scorer import RiskScoringEngine

# ── app setup ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Inspection Intelligence API",
    description=(
        "REST backend exposing all pipeline and model modules: "
        "defect extraction, risk scoring, RAG Q&A, PDF processing, "
        "and image dataset access."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── singleton engines (initialised once at startup) ─────────────────────────────
extractor = DefectExtractor()
risk_engine = RiskScoringEngine()
rag_engine = RAGEngine()
processor = DocumentProcessor()
latest_upload_result: dict | None = None


def build_analysis_id(prefix: str = "analysis") -> str:
    """Create a unique identifier for an analysis run."""
    return f"{prefix}_{uuid4().hex}"


def normalize_upload_result(result: dict) -> dict:
    """Add backward-compatible top-level aliases for upload/result payloads."""
    normalized = dict(result)
    extraction = normalized.get("extraction", {})
    risk = normalized.get("risk", {})
    legacy = normalized.get("legacy", {})
    rag = normalized.get("rag", {})

    normalized.setdefault("summary", extraction.get("summary"))
    normalized.setdefault("defects", extraction.get("defects", []))
    normalized.setdefault("defect_count", extraction.get("defect_count", normalized.get("defects_found", 0)))
    normalized.setdefault("defects_found", normalized.get("defect_count", len(normalized.get("defects", []))))
    normalized.setdefault("risk_category", risk.get("category"))
    normalized.setdefault("risk_score", risk.get("score"))
    normalized.setdefault("recommendations", risk.get("recommendations", []))
    normalized.setdefault("advanced_risk", risk)
    normalized.setdefault("legacy_risk", legacy.get("risk", normalized.get("risk_category")))
    normalized.setdefault(
        "guidance",
        rag.get("answer") or " ".join(normalized.get("recommendations", []))
    )

    return normalized


def build_rag_response(question: str) -> dict:
    """Run a knowledge-base question through the RAG engine."""
    return rag_engine.answer_question(RAGQuery(question=question))


def build_statistics_payload() -> dict:
    """Build aggregate statistics used by dashboard-style clients."""
    reports = load_sample_reports()
    pdf_pages = extract_pdf_text()
    image_counts = get_image_counts()

    risk_counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }
    total_defects = 0

    for idx, report in enumerate(reports):
        project_name = report.get("project", f"Report {idx + 1}")
        extraction = extractor.extract_defects(report.get("report_text", ""), project_name=project_name)
        risk = risk_engine.calculate_risk(extraction)
        total_defects += len(extraction.defects)

        category = risk.risk_category.value.lower()
        if "critical" in category:
            risk_counts["critical"] += 1
        elif "high" in category:
            risk_counts["high"] += 1
        elif "medium" in category:
            risk_counts["medium"] += 1
        else:
            risk_counts["low"] += 1

    total_reports = len(reports)
    latest_upload = normalize_upload_result(latest_upload_result) if latest_upload_result else {}
    analyses = [dict(latest_upload)] if latest_upload else []

    risk_scores = []
    for analysis in analyses:
        score = analysis.get("risk_score")
        if score is None:
            score = analysis.get("risk", {}).get("score")
        if score is None:
            score = analysis.get("advanced_risk", {}).get("score")
        if isinstance(score, (int, float)):
            risk_scores.append(float(score))

    average_risk_score = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0

    return {
        "sample_reports": total_reports,
        "total_reports": total_reports,
        "total_analyses": len(analyses),
        "analyses": analyses,
        "latest_analysis": latest_upload if latest_upload else None,
        "average_risk_score": average_risk_score,
        "pdf_pages": len(pdf_pages),
        "positive_images": image_counts.get("positive", 0),
        "negative_images": image_counts.get("negative", 0),
        "total_images": image_counts.get("positive", 0) + image_counts.get("negative", 0),
        "total_defects": total_defects,
        "defects_found": total_defects,
        "average_defects_per_report": round(total_defects / total_reports, 2) if total_reports else 0.0,
        "high_risk_reports": risk_counts["high"],
        "medium_risk_reports": risk_counts["medium"],
        "low_risk_reports": risk_counts["low"],
        "critical_risk_reports": risk_counts["critical"],
        "latest_upload_available": bool(latest_upload),
        "latest_upload": latest_upload,
        "risk_breakdown": risk_counts,
    }


# ── request/response schemas ────────────────────────────────────────────────────
class TextRequest(BaseModel):
    text: str
    project_name: str = "Unknown"


class QuestionRequest(BaseModel):
    question: str


# ══════════════════════════════════════════════════════════════════════════════
#  ROOT / HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
def root():
    """API health check and module inventory."""
    return {
        "status": "running",
        "app": "Inspection Intelligence API",
        "version": "1.0.0",
        "endpoints": {
            "health":          "GET  /health",
            "reports":         "GET  /reports",
            "pdf":             "GET  /pdf",
            "image_counts":    "GET  /images/counts",
            "image_samples":   "GET  /images/samples/{category}?limit=3",
            "simple_extract":  "POST /extract/simple",
            "defect_extract":  "POST /extract/defects",
            "risk_score":      "POST /risk",
            "full_analyze":    "POST /analyze",
            "rag_query":       "POST /rag/query",
            "ask_post":        "POST /ask",
            "ask_get":         "GET  /ask?question=...",
            "upload_file":     "POST /upload",
            "results":         "GET  /results",
            "statistics":      "GET  /statistics",
        },
    }


@app.get("/health", tags=["Health"])
def health():
    """Liveness probe."""
    return {"status": "healthy"}


@app.get("/results", tags=["Models – DocumentProcessor"])
def get_latest_results():
    """Return latest analysis plus collection-style metadata for compatibility."""
    if latest_upload_result is None:
        return {
            "status": "empty",
            "detail": "No upload analysis available yet.",
            "total_analyses": 0,
            "analyses": [],
            "latest_analysis": None,
        }

    latest = normalize_upload_result(latest_upload_result)
    return {
        **latest,
        "total_analyses": 1,
        "analyses": [dict(latest)],
        "latest_analysis": latest,
    }


@app.get("/statistics", tags=["Dashboard"])
def get_statistics():
    """Return aggregate statistics for reports, PDF pages, images, and latest upload."""
    return build_statistics_payload()


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE ── loader.py
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/reports", tags=["Pipeline – Loader"])
def get_reports():
    """
    Load all inspection reports from ``data/sample_reports.json``.

    Returns every report with its project name, text, and label.
    """
    reports = load_sample_reports()
    return {"count": len(reports), "reports": reports}


@app.get("/pdf", tags=["Pipeline – Loader"])
def get_pdf_pages():
    """
    Extract text from ``data/The_Merged_Approved_Documents_Oct24.pdf``
    (first 5 pages).
    """
    pages = extract_pdf_text()
    return {"page_count": len(pages), "pages": pages}


@app.get("/images/counts", tags=["Pipeline – Loader"])
def get_image_stats():
    """Return the number of positive/negative crack images in the dataset."""
    return get_image_counts()


@app.get("/images/samples/{category}", tags=["Pipeline – Loader"])
def get_image_sample_paths(category: str, limit: int = 3):
    """
    Return file paths for sample images.

    - **category**: ``positive`` or ``negative``
    - **limit**: number of images to return (default 3)
    """
    if category.lower() not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="category must be 'positive' or 'negative'")
    paths = get_image_samples(category, limit=limit)
    return {"category": category, "count": len(paths), "paths": paths}


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE ── extract.py   (simple keyword-based extractor)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/extract/simple", tags=["Pipeline – Extract"])
def simple_extract_endpoint(req: TextRequest):
    """
    Keyword-based defect extraction (``pipeline/extract.py``).

    Returns raw defect list + legacy risk label.
    """
    defects = simple_extract(req.text.lower())
    legacy_risk = risk_score(defects)
    return {
        "defect_count": len(defects),
        "defects": defects,
        "risk": legacy_risk,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MODELS ── defect_extractor.py
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/extract/defects", tags=["Models – DefectExtractor"])
def extract_defects(req: TextRequest):
    """
    Advanced defect extraction using ``DefectExtractor``.

    Uses OpenAI GPT-3.5 when an API key is set; falls back to
    heuristic keyword extraction automatically.
    """
    result = extractor.extract_defects(req.text, project_name=req.project_name)
    return {
        "analysis_id": build_analysis_id("defects"),
        "project_name": result.project_name,
        "summary": result.summary,
        "defect_count": len(result.defects),
        "defects": [
            {
                "type": d.type,
                "severity": d.severity.value,
                "location": d.location,
                "description": d.description,
                "confidence": round(d.confidence, 3),
            }
            for d in result.defects
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MODELS ── risk_scorer.py + risk.py
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/risk", tags=["Models – RiskScorer"])
def calculate_risk(req: TextRequest):
    """
    Advanced risk scoring via ``RiskScoringEngine``.

    Runs ``DefectExtractor`` first, then scores the result.
    Also returns the legacy risk label from ``models/risk.py``.
    """
    extraction = extractor.extract_defects(req.text, project_name=req.project_name)
    risk = risk_engine.calculate_risk(extraction)
    legacy_defects = simple_extract(req.text.lower())
    legacy_risk = risk_score(legacy_defects)

    return {
        "analysis_id": build_analysis_id("risk"),
        "project_name": risk.project_name,
        "advanced_risk": {
            "category": risk.risk_category.value,
            "score": risk.risk_score,
            "total_defects": risk.total_defects,
            "severity_breakdown": risk.severity_breakdown,
            "recommendations": risk.recommendations,
        },
        "legacy_risk": legacy_risk,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MODELS ── rag_engine.py
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/rag/query", tags=["Models – RAGEngine"])
def rag_query(req: QuestionRequest):
    """
    RAG-based Q&A over building regulations using ``RAGEngine``.

    Returns an answer, supporting sources, and confidence.
    """
    return build_rag_response(req.question)


@app.post("/ask", tags=["Models – RAGEngine"])
def ask_question(payload: dict):
    """Backward-compatible alias for question answering."""
    question = payload.get("question") or payload.get("query") or payload.get("q")
    if not question:
        raise HTTPException(status_code=422, detail="Provide 'question', 'query', or 'q'.")
    return build_rag_response(question)


@app.get("/ask", tags=["Models – RAGEngine"])
def ask_question_get(
    question: str | None = Query(default=None),
    q: str | None = Query(default=None),
    query: str | None = Query(default=None),
):
    """GET alias for question answering, useful for browser-based clients."""
    resolved_question = question or q or query
    if not resolved_question:
        return {
            "status": "ready",
            "detail": "Use ?question=... (or ?q=... / ?query=...) or POST JSON to /ask.",
        }
    return build_rag_response(resolved_question)


# ══════════════════════════════════════════════════════════════════════════════
#  COMBINED ── full analysis pipeline
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/analyze", tags=["Full Pipeline"])
def full_analysis(req: TextRequest):
    """
    **Full pipeline** – runs every module in one shot:

    1. ``DefectExtractor`` → structured defects
    2. ``RiskScoringEngine`` → advanced risk score
    3. ``simple_extract`` + ``risk_score`` → legacy baseline
    4. ``RAGEngine`` → contextual action guidance
    """
    extraction = extractor.extract_defects(req.text, project_name=req.project_name)
    advanced_risk = risk_engine.calculate_risk(extraction)
    legacy_defects = simple_extract(req.text.lower())
    legacy_risk = risk_score(legacy_defects)

    top_defect = (
        extraction.defects[0].type if extraction.defects else "inspection findings"
    )
    guidance = rag_engine.answer_question(
        RAGQuery(question=f"What immediate actions are recommended for {top_defect} issues?")
    )

    return {
        "analysis_id": build_analysis_id("analysis"),
        "project_name": req.project_name,
        "extraction": {
            "summary": extraction.summary,
            "defect_count": len(extraction.defects),
            "defects": [
                {
                    "type": d.type,
                    "severity": d.severity.value,
                    "location": d.location,
                    "description": d.description,
                    "confidence": round(d.confidence, 3),
                }
                for d in extraction.defects
            ],
        },
        "advanced_risk": {
            "category": advanced_risk.risk_category.value,
            "score": advanced_risk.risk_score,
            "total_defects": advanced_risk.total_defects,
            "severity_breakdown": advanced_risk.severity_breakdown,
            "recommendations": advanced_risk.recommendations,
        },
        "legacy": {
            "defects": legacy_defects,
            "risk": legacy_risk,
        },
        "guidance": guidance["answer"],
        "guidance_sources": guidance.get("sources", []),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MODELS ── document_processor.py  (file upload)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/upload", tags=["Models – DocumentProcessor"])
async def upload_and_analyze(file: UploadFile = File(...)):
    """
    Upload a **PDF, TXT, PNG, JPG** file.

    Extracts text via ``DocumentProcessor``, then runs the full
    ``DefectExtractor`` + ``RiskScoringEngine`` pipeline on it.
    """
    content = await file.read()
    try:
        extracted_text, file_type = process_uploaded_file(content, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    extraction = extractor.extract_defects(extracted_text, project_name=file.filename)
    risk = risk_engine.calculate_risk(extraction)

    result = {
        "analysis_id": build_analysis_id("upload"),
        "project_name": file.filename,
        "filename": file.filename,
        "file_type": file_type,
        "text_preview": extracted_text[:600] + ("…" if len(extracted_text) > 600 else ""),
        "defects_found": len(extraction.defects),
        "risk_category": risk.risk_category.value,
        "extraction": {
            "summary": extraction.summary,
            "defect_count": len(extraction.defects),
            "defects": [
                {
                    "type": d.type,
                    "severity": d.severity.value,
                    "location": d.location,
                    "description": d.description,
                    "confidence": round(d.confidence, 3),
                }
                for d in extraction.defects
            ],
        },
        "risk": {
            "category": risk.risk_category.value,
            "score": risk.risk_score,
            "recommendations": risk.recommendations,
        },
    }

    result = normalize_upload_result(result)

    global latest_upload_result
    latest_upload_result = result
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

