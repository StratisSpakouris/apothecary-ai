"""
Patient Profiling Agent

Analyzes patient prescription history to understand refill patterns,
predict future refills, and classify patient behavior.

This agent provides the foundation for demand forecasting by creating
detailed profiles of each patient's medication behavior.
"""

from src.utils.logging import setup_logger
from src.schemas.patient import (
    PatientProfile,
    PatientProfilingResult,
    RefillPattern,
    RefillPrediction,
    BehaviorType
)

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from pathlib import Path


class PatientProfilingAgent:
    """
    Agent responsible for analyzing patient medication behavior.
    
    Analyzes prescription history to:
    - Calculate refill patterns (average interval, consistency)
    - Classify patient behavior (regular, irregular, etc.)
    - Predict next refill dates with confidence intervals
    - Identify patients at risk of missing refills
    
    Does NOT use LLM - pure statistical analysis.
    """
    
    # Thresholds for behavior classification
    HIGHLY_REGULAR_STD_THRESHOLD = 3.0   # ±3 days
    REGULAR_STD_THRESHOLD = 7.0          # ±7 days
    MIN_REFILLS_FOR_PREDICTION = 3       # Need at least 3 data points
    DUE_SOON_DAYS = 7                    # "Due soon" threshold
    
    def __init__(self, config: Dict = None):
        """
        Initialize Patient Profiling Agent.

        Args:
            config: Optional configuration dictionary
        """
        self.name = "PatientProfilingAgent"
        self.logger = setup_logger(self.name)
        self.config = config or {}
        
        # Override thresholds from config if provided
        self.highly_regular_threshold = self.config.get(
            "highly_regular_std_threshold", 
            self.HIGHLY_REGULAR_STD_THRESHOLD
        )
        self.regular_threshold = self.config.get(
            "regular_std_threshold", 
            self.REGULAR_STD_THRESHOLD
        )
    
    def execute(
        self, 
        prescription_data: pd.DataFrame,
        analysis_date: date = None
    ) -> PatientProfilingResult:
        """
        Analyze all patients and generate profiles.
        
        Args:
            prescription_data: DataFrame with columns:
                - patient_id: str
                - medication: str  
                - fill_date: datetime
                - quantity: int
                - days_supply: int (optional)
            analysis_date: Date to use as "today" (default: actual today)
            
        Returns:
            PatientProfilingResult with all patient profiles
        """
        if analysis_date is None:
            analysis_date = date.today()
        
        self.logger.info(f"Starting patient analysis for {analysis_date}")
        self.logger.info(f"Input: {len(prescription_data)} prescription records")
        
        # Ensure fill_date is datetime
        prescription_data = prescription_data.copy()
        prescription_data["fill_date"] = pd.to_datetime(prescription_data["fill_date"])
        
        # Generate profiles for each patient-medication combination
        profiles = []
        
        grouped = prescription_data.groupby(["patient_id", "medication"])
        total_combinations = len(grouped)
        
        self.logger.info(f"Analyzing {total_combinations} patient-medication combinations")
        
        for (patient_id, medication), group in grouped:
            profile = self._analyze_patient_medication(
                patient_id=patient_id,
                medication=medication,
                history=group,
                analysis_date=analysis_date
            )
            profiles.append(profile)
        
        # Count summary stats
        patients_due_soon = sum(1 for p in profiles if p.is_due_soon)
        unique_patients = prescription_data["patient_id"].nunique()
        
        self.logger.info(f"Analysis complete: {len(profiles)} profiles generated")
        self.logger.info(f"Patients due soon (within {self.DUE_SOON_DAYS} days): {patients_due_soon}")
        
        return PatientProfilingResult(
            profiles=profiles,
            total_patients=unique_patients,
            total_patient_medications=len(profiles),
            patients_due_soon=patients_due_soon,
            analysis_date=analysis_date
        )
    
    def _analyze_patient_medication(
        self,
        patient_id: str,
        medication: str,
        history: pd.DataFrame,
        analysis_date: date
    ) -> PatientProfile:
        """
        Analyze a single patient's history for one medication.
        
        Args:
            patient_id: Patient identifier
            medication: Medication name
            history: DataFrame with this patient's fill history
            analysis_date: Date to use as "today"
            
        Returns:
            PatientProfile for this patient-medication
        """
        # Sort by date
        history = history.sort_values("fill_date")
        
        # Get last fill info
        last_fill = history.iloc[-1]
        last_fill_date = last_fill["fill_date"].date()
        last_quantity = int(last_fill["quantity"])
        
        # Calculate refill intervals
        pattern = self._calculate_pattern(history)
        
        # Classify behavior
        behavior_type = self._classify_behavior(pattern, len(history))
        
        # Generate prediction (if enough data)
        prediction = None
        if pattern.total_refills >= self.MIN_REFILLS_FOR_PREDICTION:
            prediction = self._predict_next_refill(
                last_fill_date=last_fill_date,
                pattern=pattern,
                analysis_date=analysis_date
            )
        
        # Determine if due soon
        is_due_soon = False
        days_until_expected = None
        if prediction:
            days_until_expected = prediction.days_until_expected
            is_due_soon = days_until_expected <= self.DUE_SOON_DAYS
        
        # Calculate lapse risk
        risk_of_lapse = self._calculate_lapse_risk(
            behavior_type=behavior_type,
            pattern=pattern,
            history=history
        )
        
        return PatientProfile(
            patient_id=patient_id,
            medication=medication,
            behavior_type=behavior_type,
            pattern=pattern,
            prediction=prediction,
            last_fill_date=last_fill_date,
            last_quantity=last_quantity,
            is_due_soon=is_due_soon,
            risk_of_lapse=risk_of_lapse
        )
    
    def _calculate_pattern(self, history: pd.DataFrame) -> RefillPattern:
        """
        Calculate statistical refill pattern from history.
        
        Args:
            history: DataFrame with fill history (sorted by date)
            
        Returns:
            RefillPattern with statistics
        """
        total_refills = len(history)
        
        if total_refills < 2:
            # Not enough data for interval calculation
            return RefillPattern(
                average_interval_days=30.0,  # Default assumption
                std_deviation_days=15.0,     # High uncertainty
                total_refills=total_refills,
                consistency_score=0.0
            )
        
        # Calculate intervals between refills
        history = history.sort_values("fill_date")
        intervals = history["fill_date"].diff().dt.days.dropna()
        
        avg_interval = float(intervals.mean())
        std_interval = float(intervals.std()) if len(intervals) > 1 else 15.0
        
        # Handle edge case where std is NaN or 0
        if pd.isna(std_interval) or std_interval == 0:
            std_interval = 1.0
        
        # Calculate consistency score (inverse of coefficient of variation)
        # Higher score = more consistent
        cv = std_interval / avg_interval if avg_interval > 0 else 1.0
        consistency_score = max(0.0, min(1.0, 1.0 - cv))
        
        return RefillPattern(
            average_interval_days=round(avg_interval, 1),
            std_deviation_days=round(std_interval, 1),
            total_refills=total_refills,
            consistency_score=round(consistency_score, 2)
        )
    
    def _classify_behavior(
        self, 
        pattern: RefillPattern, 
        num_refills: int
    ) -> BehaviorType:
        """
        Classify patient behavior based on refill pattern.
        
        Args:
            pattern: Calculated refill pattern
            num_refills: Number of refills in history
            
        Returns:
            BehaviorType classification
        """
        if num_refills < self.MIN_REFILLS_FOR_PREDICTION:
            if num_refills <= 1:
                return BehaviorType.NEW_PATIENT
            return BehaviorType.INSUFFICIENT_DATA
        
        std = pattern.std_deviation_days
        
        if std <= self.highly_regular_threshold:
            return BehaviorType.HIGHLY_REGULAR
        elif std <= self.regular_threshold:
            return BehaviorType.REGULAR
        else:
            return BehaviorType.IRREGULAR
    
    def _predict_next_refill(
        self,
        last_fill_date: date,
        pattern: RefillPattern,
        analysis_date: date
    ) -> RefillPrediction:
        """
        Predict when patient will need next refill.
        
        Args:
            last_fill_date: Date of most recent refill
            pattern: Calculated refill pattern
            analysis_date: Date to use as "today"
            
        Returns:
            RefillPrediction with expected date and confidence
        """
        avg_interval = pattern.average_interval_days
        std_interval = pattern.std_deviation_days
        
        # Expected date = last fill + average interval
        expected_date = last_fill_date + timedelta(days=int(avg_interval))
        
        # Confidence interval (roughly 95% = ±2 std deviations)
        margin = int(2 * std_interval)
        earliest_date = last_fill_date + timedelta(days=int(avg_interval - margin))
        latest_date = last_fill_date + timedelta(days=int(avg_interval + margin))
        
        # Ensure earliest isn't before today
        if earliest_date < analysis_date:
            earliest_date = analysis_date
        
        # Days until expected
        days_until = (expected_date - analysis_date).days
        
        # Confidence based on consistency
        # High consistency = high confidence
        confidence = pattern.consistency_score
        
        # Boost confidence if we have lots of data
        if pattern.total_refills >= 10:
            confidence = min(0.95, confidence + 0.1)
        elif pattern.total_refills >= 6:
            confidence = min(0.90, confidence + 0.05)
        
        return RefillPrediction(
            expected_date=expected_date,
            confidence=round(confidence, 2),
            earliest_date=earliest_date,
            latest_date=latest_date,
            days_until_expected=days_until
        )
    
    def _calculate_lapse_risk(
        self,
        behavior_type: BehaviorType,
        pattern: RefillPattern,
        history: pd.DataFrame
    ) -> float:
        """
        Calculate risk that patient will miss their next refill.
        
        Args:
            behavior_type: Patient's behavior classification
            pattern: Refill pattern statistics
            history: Fill history
            
        Returns:
            Risk score between 0 and 1
        """
        # Base risk by behavior type
        base_risk = {
            BehaviorType.HIGHLY_REGULAR: 0.02,
            BehaviorType.REGULAR: 0.08,
            BehaviorType.IRREGULAR: 0.20,
            BehaviorType.NEW_PATIENT: 0.35,
            BehaviorType.INSUFFICIENT_DATA: 0.25
        }
        
        risk = base_risk.get(behavior_type, 0.15)
        
        # Adjust based on consistency score
        # Low consistency = higher risk
        risk += (1 - pattern.consistency_score) * 0.1
        
        # Adjust based on history length
        # More history = more reliable, lower risk
        if pattern.total_refills >= 10:
            risk *= 0.8
        elif pattern.total_refills >= 6:
            risk *= 0.9
        elif pattern.total_refills <= 2:
            risk *= 1.2
        
        # Clamp to valid range
        return round(min(1.0, max(0.0, risk)), 2)
    
    def get_patients_due_in_window(
        self,
        result: PatientProfilingResult,
        days: int = 7
    ) -> List[PatientProfile]:
        """
        Get patients expected to refill within a time window.
        
        Args:
            result: Profiling result to filter
            days: Number of days to look ahead
            
        Returns:
            List of profiles for patients due within window
        """
        due_patients = []
        
        for profile in result.profiles:
            if profile.prediction:
                if 0 <= profile.prediction.days_until_expected <= days:
                    due_patients.append(profile)
        
        # Sort by expected date
        due_patients.sort(key=lambda p: p.prediction.expected_date)
        
        return due_patients
    
    def summarize_by_medication(
        self,
        result: PatientProfilingResult
    ) -> Dict[str, Dict]:
        """
        Summarize profiles grouped by medication.
        
        Args:
            result: Profiling result to summarize
            
        Returns:
            Dictionary with medication summaries
        """
        summaries = {}
        
        # Group profiles by medication
        by_medication = {}
        for profile in result.profiles:
            if profile.medication not in by_medication:
                by_medication[profile.medication] = []
            by_medication[profile.medication].append(profile)
        
        # Calculate summaries
        for medication, profiles in by_medication.items():
            due_soon = [p for p in profiles if p.is_due_soon]
            high_risk = [p for p in profiles if p.risk_of_lapse >= 0.2]
            
            # Expected refills in next 7 days
            expected_refills_7d = len(due_soon)
            
            # Expected quantity in next 7 days
            expected_quantity_7d = sum(
                p.last_quantity for p in due_soon
            )
            
            summaries[medication] = {
                "total_patients": len(profiles),
                "patients_due_7d": expected_refills_7d,
                "expected_quantity_7d": expected_quantity_7d,
                "high_risk_patients": len(high_risk),
                "avg_refill_interval": round(
                    np.mean([p.pattern.average_interval_days for p in profiles]), 
                    1
                )
            }
        
        return summaries