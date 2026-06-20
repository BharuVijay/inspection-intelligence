"""
LLM-based defect extraction module
Uses language models to parse and structure defect information
"""
import json
from typing import List, Optional
import os
from models import Defect, SeverityLevel, ExtractionResult
from datetime import datetime


class DefectExtractor:
    """Extracts defects from unstructured inspection text using LLM"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize defect extractor
        
        Args:
            api_key: OpenAI API key (uses env variable if not provided)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = "gpt-3.5-turbo"
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        except ImportError:
            self.client = None
    
    def extract_defects(self, text: str, project_name: str = "Unknown") -> ExtractionResult:
        """
        Extract defects from inspection text
        
        Args:
            text: Unstructured inspection text
            project_name: Name of the building/project
            
        Returns:
            ExtractionResult with structured defects
        """
        if not self.client:
            return self._extract_defects_fallback(text, project_name)
        
        try:
            defects = self._call_llm_for_extraction(text)
            
            # Parse LLM response
            if isinstance(defects, str):
                defects = json.loads(defects)
            
            parsed_defects = [
                Defect(
                    type=d.get("type", "unknown"),
                    severity=SeverityLevel(d.get("severity", "medium").lower()),
                    location=d.get("location", "unknown"),
                    description=d.get("description", ""),
                    confidence=float(d.get("confidence", 0.95))
                )
                for d in defects
            ]
            
            return ExtractionResult(
                project_name=project_name,
                defects=parsed_defects,
                summary=self._generate_summary(parsed_defects),
                timestamp=datetime.now()
            )
        
        except Exception as e:
            print(f"LLM extraction failed: {e}. Falling back to heuristic method.")
            return self._extract_defects_fallback(text, project_name)
    
    def _call_llm_for_extraction(self, text: str) -> List[dict]:
        """
        Call LLM API for defect extraction
        
        Args:
            text: Inspection text
            
        Returns:
            List of extracted defects
        """
        prompt = self._build_extraction_prompt(text)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert building inspector assistant. Extract defects from inspection reports in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON from response
        try:
            # Look for JSON array in response
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        return []
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build prompt for LLM extraction"""
        return f"""
Analyze the following building inspection report and extract all defects mentioned.
For each defect, provide:
1. type: category of defect (e.g., crack, corrosion, water damage, mold, structural issue, electrical hazard, etc.)
2. severity: one of ['low', 'medium', 'high', 'critical']
3. location: where in the building the defect is located
4. description: brief description of the defect
5. confidence: your confidence level (0.0-1.0)

Return ONLY a valid JSON array with these fields, nothing else.

Inspection Report:
{text}

JSON Response:
"""
    
    def _extract_defects_fallback(self, text: str, project_name: str) -> ExtractionResult:
        """
        Fallback heuristic-based extraction when LLM is unavailable
        
        Args:
            text: Inspection text
            project_name: Project name
            
        Returns:
            ExtractionResult
        """
        defects = []
        
        # Simple keyword-based extraction
        severity_keywords = {
            "critical": ["critical", "severe", "dangerous", "hazardous", "fatal"],
            "high": ["major", "significant", "broken", "structural", "failed"],
            "medium": ["moderate", "noticeable", "damaged", "deteriorated"],
            "low": ["minor", "slight", "small", "cosmetic"]
        }
        
        defect_keywords = {
            "crack": ["crack", "fracture", "split"],
            "corrosion": ["rust", "corrosion", "oxidation"],
            "water_damage": ["water", "leak", "moisture", "damp"],
            "mold": ["mold", "mildew", "fungal"],
            "structural": ["beam", "column", "foundation", "load-bearing"],
            "electrical": ["electrical", "wire", "short", "hazard"]
        }
        
        text_lower = text.lower()
        
        # Extract defects based on keywords
        for defect_type, keywords in defect_keywords.items():
            if any(kw in text_lower for kw in keywords):
                # Determine severity
                severity = "medium"
                for sev, sev_kws in severity_keywords.items():
                    if any(kw in text_lower for kw in sev_kws):
                        severity = sev
                        break
                
                defects.append(
                    Defect(
                        type=defect_type.replace("_", " "),
                        severity=SeverityLevel(severity),
                        location="General",
                        description=f"Detected {defect_type} in inspection",
                        confidence=0.6
                    )
                )
        
        return ExtractionResult(
            project_name=project_name,
            defects=defects if defects else [
                Defect(
                    type="General Inspection",
                    severity=SeverityLevel.MEDIUM,
                    location="Site",
                    description="Site inspected - no major defects detected",
                    confidence=0.5
                )
            ],
            summary="Heuristic-based extraction (LLM unavailable)",
            timestamp=datetime.now()
        )
    
    def _generate_summary(self, defects: List[Defect]) -> str:
        """Generate summary of defects"""
        if not defects:
            return "No defects detected."
        
        count_by_severity = {}
        for defect in defects:
            severity = defect.severity.value
            count_by_severity[severity] = count_by_severity.get(severity, 0) + 1
        
        summary = f"Found {len(defects)} defect(s): "
        summary += ", ".join([f"{count} {sev}" for sev, count in sorted(count_by_severity.items())])
        
        return summary

