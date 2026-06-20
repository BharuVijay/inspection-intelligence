"""
Risk scoring engine
Calculates building risk based on extracted defects
"""
from typing import List, Tuple
from models import Defect, RiskScore, RiskCategory, SeverityLevel, ExtractionResult


class RiskScoringEngine:
    """
    Rule-based risk scoring model for MVP
    Weights severity and defect combinations to output risk category
    """
    
    # Severity weights (0-100)
    SEVERITY_WEIGHTS = {
        SeverityLevel.LOW: 10,
        SeverityLevel.MEDIUM: 30,
        SeverityLevel.HIGH: 60,
        SeverityLevel.CRITICAL: 100
    }
    
    # Defect type amplification factors
    DEFECT_AMPLIFIERS = {
        "structural": 1.5,
        "electrical": 1.3,
        "load-bearing": 1.5,
        "foundation": 1.6,
        "critical system": 1.4,
        "water damage": 1.2,
        "mold": 1.1,
        "crack": 1.2,
        "corrosion": 1.1
    }
    
    # Risk thresholds
    RISK_THRESHOLDS = {
        (0, 20): RiskCategory.LOW_RISK,
        (20, 40): RiskCategory.MEDIUM_RISK,
        (40, 70): RiskCategory.HIGH_RISK,
        (70, 101): RiskCategory.CRITICAL_RISK
    }
    
    # Recommendations by risk level
    RECOMMENDATIONS = {
        RiskCategory.LOW_RISK: [
            "Continue regular maintenance schedule",
            "Monitor defects for any changes"
        ],
        RiskCategory.MEDIUM_RISK: [
            "Schedule repair within 3-6 months",
            "Assign dedicated maintenance resources",
            "Increase inspection frequency"
        ],
        RiskCategory.HIGH_RISK: [
            "Prioritize repairs immediately",
            "Engage structural engineers for assessment",
            "Consider occupancy restrictions if necessary",
            "Develop urgent remediation plan"
        ],
        RiskCategory.CRITICAL_RISK: [
            "URGENT: Consult with structural engineers",
            "May require immediate evacuation or area closure",
            "Implement emergency safety measures",
            "Prioritize repairs above all other projects",
            "Document all findings for insurance/liability"
        ]
    }
    
    def calculate_risk(self, extraction_result: ExtractionResult) -> RiskScore:
        """
        Calculate risk score for a project based on defects
        
        Args:
            extraction_result: ExtractionResult containing defects
            
        Returns:
            RiskScore with category, score, and recommendations
        """
        defects = extraction_result.defects
        
        if not defects:
            return self._create_risk_score(
                extraction_result.project_name,
                defects,
                0,
                RiskCategory.LOW_RISK
            )
        
        # Calculate base score from severities
        base_score = self._calculate_base_score(defects)
        
        # Apply defect type amplifiers
        amplified_score = self._apply_amplifiers(defects, base_score)
        
        # Apply confidence weighting
        final_score = self._apply_confidence_weighting(defects, amplified_score)
        
        # Ensure score is within bounds
        final_score = min(100, max(0, final_score))
        
        # Determine risk category
        risk_category = self._get_risk_category(final_score)
        
        return self._create_risk_score(
            extraction_result.project_name,
            defects,
            final_score,
            risk_category
        )
    
    def _calculate_base_score(self, defects: List[Defect]) -> float:
        """
        Calculate base risk score from defect severities
        
        Args:
            defects: List of defects
            
        Returns:
            Base score (0-100)
        """
        if not defects:
            return 0
        
        total_weight = sum(
            self.SEVERITY_WEIGHTS.get(d.severity, 30)
            for d in defects
        )
        
        # Average weight with count factor
        count_factor = min(len(defects) / 5, 1.5)  # More defects increase score
        base_score = (total_weight / len(defects)) * count_factor
        
        return base_score
    
    def _apply_amplifiers(self, defects: List[Defect], base_score: float) -> float:
        """
        Apply defect type amplifiers to increase score for critical defect types
        
        Args:
            defects: List of defects
            base_score: Base score
            
        Returns:
            Amplified score
        """
        max_amplifier = 1.0
        
        for defect in defects:
            defect_type_lower = defect.type.lower()
            for key, amplifier in self.DEFECT_AMPLIFIERS.items():
                if key in defect_type_lower:
                    max_amplifier = max(max_amplifier, amplifier)
        
        amplified_score = base_score * max_amplifier
        return amplified_score
    
    def _apply_confidence_weighting(self, defects: List[Defect], score: float) -> float:
        """
        Weight score by average confidence of detections
        
        Args:
            defects: List of defects
            score: Current score
            
        Returns:
            Confidence-weighted score
        """
        avg_confidence = sum(d.confidence for d in defects) / len(defects)
        
        # Low confidence reduces score impact
        confidence_factor = 0.5 + (avg_confidence * 0.5)
        
        return score * confidence_factor
    
    def _get_risk_category(self, score: float) -> RiskCategory:
        """
        Get risk category based on score
        
        Args:
            score: Risk score (0-100)
            
        Returns:
            RiskCategory
        """
        for (min_score, max_score), category in self.RISK_THRESHOLDS.items():
            if min_score <= score < max_score:
                return category
        
        return RiskCategory.CRITICAL_RISK
    
    def _create_risk_score(
        self,
        project_name: str,
        defects: List[Defect],
        score: float,
        category: RiskCategory
    ) -> RiskScore:
        """
        Create RiskScore object
        
        Args:
            project_name: Project name
            defects: List of defects
            score: Risk score
            category: Risk category
            
        Returns:
            RiskScore
        """
        severity_breakdown = {}
        for defect in defects:
            severity = defect.severity.value
            severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
        
        recommendations = self.RECOMMENDATIONS.get(
            category,
            ["Continue monitoring"]
        ).copy()
        
        # Add specific recommendations for critical defects
        for defect in defects:
            if defect.severity == SeverityLevel.CRITICAL:
                recommendations.append(
                    f"Urgent attention needed: {defect.type} at {defect.location}"
                )
        
        return RiskScore(
            project_name=project_name,
            total_defects=len(defects),
            risk_category=category,
            risk_score=round(score, 2),
            severity_breakdown=severity_breakdown,
            recommendations=list(set(recommendations))  # Remove duplicates
        )


def calculate_project_risk(extraction_result: ExtractionResult) -> RiskScore:
    """
    Convenience function to calculate risk for a project
    
    Args:
        extraction_result: Extraction result
        
    Returns:
        Risk score
    """
    engine = RiskScoringEngine()
    return engine.calculate_risk(extraction_result)

