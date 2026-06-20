import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add parent directory to path so imports work from any working directory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from models.defect_extractor import DefectExtractor
from models.document_processor import DocumentProcessor, process_uploaded_file
from models.rag_engine import RAGEngine
from models.risk import risk_score
from models.risk_scorer import RiskScoringEngine
from models import RAGQuery
from pipeline.extract import simple_extract
from pipeline.loader import load_sample_reports, get_image_counts, get_image_samples


def defects_to_rows(defects):
    rows = []
    for defect in defects:
        rows.append(
            {
                "type": defect.type,
                "severity": defect.severity.value,
                "location": defect.location,
                "description": defect.description,
                "confidence": round(defect.confidence, 2),
            }
        )
    return rows


@st.cache_resource
def get_engines():
    return {
        "processor": DocumentProcessor(),
        "extractor": DefectExtractor(),
        "risk_engine": RiskScoringEngine(),
        "rag_engine": RAGEngine(),
    }


def analyze_text(project_name, text):
    engines = get_engines()

    extraction_result = engines["extractor"].extract_defects(text, project_name=project_name)
    advanced_risk = engines["risk_engine"].calculate_risk(extraction_result)

    legacy_defects = simple_extract(text.lower())
    legacy_risk = risk_score(legacy_defects)

    top_defect = extraction_result.defects[0].type if extraction_result.defects else "inspection findings"
    rag_result = engines["rag_engine"].answer_question(
        RAGQuery(question=f"What immediate actions are recommended for {top_defect} issues?")
    )

    return {
        "extraction": extraction_result,
        "advanced_risk": advanced_risk,
        "legacy_risk": legacy_risk,
        "legacy_defects": legacy_defects,
        "rag": rag_result,
    }


def parse_pdf_pages(extracted_text):
    pages = []
    current_page = []
    current_title = None

    for line in extracted_text.splitlines():
        if line.startswith("--- Page ") and line.endswith(" ---"):
            if current_title is not None:
                pages.append({"source": current_title, "text": "\n".join(current_page).strip()})
            current_title = line.strip("-").strip()
            current_page = []
        else:
            current_page.append(line)

    if current_title is not None:
        pages.append({"source": current_title, "text": "\n".join(current_page).strip()})

    return [p for p in pages if p["text"]]


st.set_page_config(page_title="Inspection Intelligence", layout="wide")
st.title("Inspection Intelligence Assistant")

page = st.sidebar.radio(
    "Navigate to:",
    [
        "Dashboard",
        "Sample Reports",
        "PDF Documents",
        "Image Classification",
        "Upload Custom Report",
    ],
)

if page == "Dashboard":
    st.header("System Overview Dashboard")

    reports = load_sample_reports()
    image_counts = get_image_counts()

    pdf_pages = []
    pdf_path = project_root / "data" / "The_Merged_Approved_Documents_Oct24.pdf"
    if pdf_path.exists():
        pdf_text, _ = get_engines()["processor"].extract_from_file(str(pdf_path))
        pdf_pages = parse_pdf_pages(pdf_text)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sample Reports", len(reports))
    with col2:
        st.metric("PDF Pages", len(pdf_pages))
    with col3:
        st.metric("Positive Images", image_counts["positive"])
    with col4:
        st.metric("Negative Images", image_counts["negative"])

    st.divider()

    if reports:
        st.subheader("Processed Reports and Risk Assessment")
        results_data = []

        for idx, report in enumerate(reports):
            project = report.get("project", f"Report {idx + 1}")
            report_text = report.get("report_text", "")
            analysis = analyze_text(project, report_text)

            results_data.append(
                {
                    "Project": project,
                    "Defects": len(analysis["extraction"].defects),
                    "Advanced Risk": analysis["advanced_risk"].risk_category.value,
                    "Advanced Score": analysis["advanced_risk"].risk_score,
                    "Legacy Risk": analysis["legacy_risk"],
                }
            )

            with st.expander(f"Details: {project}"):
                st.write("Report Text")
                st.write(report_text)

                st.write("Advanced Defect Extraction")
                st.json(defects_to_rows(analysis["extraction"].defects))

                st.write("Advanced Risk")
                st.write(f"Category: {analysis['advanced_risk'].risk_category.value}")
                st.write(f"Score: {analysis['advanced_risk'].risk_score}")
                st.write("Recommendations")
                for rec in analysis["advanced_risk"].recommendations:
                    st.write(f"- {rec}")

                st.write("Legacy Baseline")
                st.write(f"Legacy Risk: {analysis['legacy_risk']}")
                st.json(analysis["legacy_defects"])

                st.write("Knowledge Guidance (RAG)")
                st.info(analysis["rag"]["answer"])

        df = pd.DataFrame(results_data)
        st.subheader("Summary Table")
        st.dataframe(df, use_container_width=True)

elif page == "Sample Reports":
    st.header("Sample Inspection Reports")
    reports = load_sample_reports()

    if not reports:
        st.warning("No sample reports found")
    else:
        for idx, report in enumerate(reports):
            project = report.get("project", f"Report {idx + 1}")
            text = report.get("report_text", "")
            analysis = analyze_text(project, text)

            st.subheader(f"{idx + 1}. {project}")
            st.info(text)
            st.write(f"Summary: {analysis['extraction'].summary}")
            st.json(defects_to_rows(analysis["extraction"].defects))

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Advanced Risk", analysis["advanced_risk"].risk_category.value)
            with c2:
                st.metric("Legacy Risk", analysis["legacy_risk"])
            st.divider()

elif page == "PDF Documents":
    st.header("PDF Document Analysis")

    pdf_path = project_root / "data" / "The_Merged_Approved_Documents_Oct24.pdf"
    if not pdf_path.exists():
        st.warning("PDF file not found in data folder")
    else:
        pdf_text, _ = get_engines()["processor"].extract_from_file(str(pdf_path))
        pages = parse_pdf_pages(pdf_text)
        st.info(f"Extracted {len(pages)} pages from PDF")

        for i, page_data in enumerate(pages[:5], start=1):
            text = page_data["text"]
            analysis = analyze_text(f"PDF Page {i}", text)
            st.subheader(page_data["source"])
            st.write(text[:700] + ("..." if len(text) > 700 else ""))
            st.write(f"Advanced Risk: {analysis['advanced_risk'].risk_category.value}")
            with st.expander("Guidance"):
                st.write(analysis["rag"]["answer"])

elif page == "Image Classification":
    st.header("Concrete Crack Classification Dataset")
    image_counts = get_image_counts()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Negative Samples (No Crack)", image_counts["negative"])
    with col2:
        st.metric("Positive Samples (Crack)", image_counts["positive"])

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sample Negative Images")
        for img_path in get_image_samples("negative", limit=3):
            st.image(img_path, use_container_width=True)
    with col2:
        st.subheader("Sample Positive Images")
        for img_path in get_image_samples("positive", limit=3):
            st.image(img_path, use_container_width=True)

else:
    st.header("Upload and Analyze Custom Report")
    uploaded = st.file_uploader("Upload report (.txt/.pdf/.jpg/.png)", type=["txt", "pdf", "png", "jpg", "jpeg"])

    if uploaded:
        extracted_text, detected_type = process_uploaded_file(uploaded.getvalue(), uploaded.name)
        analysis = analyze_text(uploaded.name, extracted_text)

        st.subheader("Detected File Type")
        st.write(detected_type)

        st.subheader("Extracted Text")
        st.write(extracted_text[:2000] + ("..." if len(extracted_text) > 2000 else ""))

        st.subheader("Advanced Defects")
        st.json(defects_to_rows(analysis["extraction"].defects))

        st.subheader("Advanced Risk Result")
        st.write(f"Category: {analysis['advanced_risk'].risk_category.value}")
        st.write(f"Score: {analysis['advanced_risk'].risk_score}")

        st.subheader("Legacy Baseline Risk")
        st.write(analysis["legacy_risk"])

        st.subheader("Knowledge Guidance")
        st.info(analysis["rag"]["answer"])
