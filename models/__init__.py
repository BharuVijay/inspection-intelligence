from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List


class SeverityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    LOW_RISK = "Low Risk"
    MEDIUM_RISK = "Medium Risk"
    HIGH_RISK = "High Risk"
    CRITICAL_RISK = "Critical Risk"


@dataclass
class Defect:
    type: str
    severity: SeverityLevel
    location: str
    description: str = ""
    confidence: float = 1.0


@dataclass
class ExtractionResult:
    project_name: str
    defects: List[Defect]
    summary: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskScore:
    project_name: str
    total_defects: int
    risk_category: RiskCategory
    risk_score: float
    severity_breakdown: Dict[str, int]
    recommendations: List[str]


@dataclass
class RAGQuery:
    question: str

