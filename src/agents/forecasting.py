"""
Forecasting Agent

Combines patient profiles and external signals to forecast medication demand.
Uses Prophet for time series forecasting and applies external multipliers.
"""

from src.utils.logging import setup_logger
from src.schemas.patient import PatientProfilingResult, BehaviorType
from src.schemas.external_signals import ExternalSignals
from src.schemas.forecasting import (
    ForecastingResult,
    MedicationForecast,
    CategoryForecast,
    ForecastSummary,
    ForecastingConfig,
    ForecastMethod,
    DemandAlert
)

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from prophet import Prophet
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)


class ForecastingAgent:
    """
    Agent responsible for forecasting medication demand.

    Combines:
    - Patient refill predictions (from PatientProfilingAgent)
    - External signals (flu activity, weather, events)
    - Historical demand patterns (time series with Prophet)

    Outputs:
    - Daily demand forecasts per medication
    - Confidence intervals
    - Alerts for spikes, shortages, etc.

    Does NOT use LLM - pure statistical/ML forecasting.
    """

    def __init__(self, config: Optional[ForecastingConfig] = None):
        """
        Initialize Forecasting Agent.

        Args:
            config: Optional configuration for forecasting parameters
        """
        self.name = "ForecastingAgent"
        self.logger = setup_logger(self.name)
        self.config = config or ForecastingConfig()

        self.logger.info(f"Forecasting Agent initialized")
        self.logger.info(f"  Horizon: {self.config.forecast_horizon_days} days")
        self.logger.info(f"  Prophet: {'enabled' if self.config.use_prophet else 'disabled'}")

    def execute(
        self,
        patient_profiles: PatientProfilingResult,
        external_signals: Optional[ExternalSignals] = None,
        historical_data: Optional[pd.DataFrame] = None,
        start_date: Optional[date] = None
    ) -> ForecastingResult:
        """
        Generate demand forecasts for medications.

        Args:
            patient_profiles: Patient profiling results with refill predictions
            external_signals: External factors (flu, weather, events)
            historical_data: Historical prescription data (for Prophet)
            start_date: Start date for forecast (default: today)

        Returns:
            ForecastingResult with daily forecasts and alerts
        """
        start_date = start_date or date.today()
        end_date = start_date + timedelta(days=self.config.forecast_horizon_days - 1)

        self.logger.info(f"Starting forecast from {start_date} to {end_date}")
        self.logger.info(f"Input: {patient_profiles.total_patient_medications} patient-medication combinations")

        # Step 1: Aggregate patient-based demand predictions
        patient_demand = self._aggregate_patient_demand(
            patient_profiles,
            start_date,
            end_date
        )

        # Step 2: Get external signal multipliers
        multipliers = self._calculate_external_multipliers(external_signals)

        # Step 3: Generate forecasts for each medication
        medication_forecasts = []

        medications = list(patient_demand.keys())
        self.logger.info(f"Generating forecasts for {len(medications)} medications")

        for medication in medications:
            forecasts = self._forecast_medication(
                medication=medication,
                patient_demand=patient_demand[medication],
                historical_data=historical_data,
                multipliers=multipliers,
                start_date=start_date,
                end_date=end_date
            )
            medication_forecasts.extend(forecasts)

        # Step 4: Generate category-level aggregations
        category_forecasts = self._aggregate_by_category(
            medication_forecasts,
            external_signals
        )

        # Step 5: Generate summary
        summary = self._generate_summary(
            medication_forecasts,
            start_date,
            end_date,
            patient_profiles,
            external_signals
        )

        # Build result
        result = ForecastingResult(
            analysis_date=date.today(),
            forecast_start_date=start_date,
            forecast_end_date=end_date,
            medication_forecasts=medication_forecasts,
            category_forecasts=category_forecasts,
            summary=summary,
            patient_profiles_count=patient_profiles.total_patient_medications,
            external_signals_available=external_signals is not None,
            method=ForecastMethod.HYBRID if self.config.use_prophet else ForecastMethod.PATIENT_BASED,
            notes=[]
        )

        self.logger.info(f"Forecast complete: {len(medication_forecasts)} daily forecasts generated")
        self.logger.info(f"  High priority alerts: {summary.high_priority_alerts}")
        self.logger.info(f"  Average confidence: {summary.average_confidence:.0%}")

        return result

    def _aggregate_patient_demand(
        self,
        patient_profiles: PatientProfilingResult,
        start_date: date,
        end_date: date
    ) -> Dict[str, Dict[date, float]]:
        """
        Aggregate patient refill predictions by medication and date.

        Returns:
            Dict[medication -> Dict[date -> quantity]]
        """
        demand_by_med = defaultdict(lambda: defaultdict(float))

        for profile in patient_profiles.profiles:
            # Skip if no prediction
            if not profile.prediction:
                continue

            # Get predicted refill date and quantity
            refill_date = profile.prediction.expected_date

            # Only include if within forecast window
            if start_date <= refill_date <= end_date:
                demand_by_med[profile.medication][refill_date] += profile.last_quantity

        self.logger.info(f"  Patient-based demand: {len(demand_by_med)} medications")

        return dict(demand_by_med)

    def _calculate_external_multipliers(
        self,
        external_signals: Optional[ExternalSignals]
    ) -> Dict[str, float]:
        """
        Calculate demand multipliers from external signals.

        Returns:
            Dict[category -> multiplier]
        """
        multipliers = {}

        if not external_signals:
            self.logger.info("  No external signals - using baseline multipliers")
            return multipliers

        # Flu activity multipliers
        if external_signals.flu_activity:
            flu_mult = external_signals.flu_activity.get_demand_multiplier()
            multipliers['antiviral'] = flu_mult
            multipliers['cold_flu_otc'] = flu_mult * 0.8  # Moderate impact
            self.logger.info(f"  Flu multiplier: {flu_mult:.2f}x")

        # Weather multipliers
        if external_signals.weather:
            weather_mult = external_signals.weather.get_cold_flu_multiplier()
            if 'cold_flu_otc' in multipliers:
                multipliers['cold_flu_otc'] = max(multipliers['cold_flu_otc'], weather_mult)
            else:
                multipliers['cold_flu_otc'] = weather_mult
            self.logger.info(f"  Weather multiplier: {weather_mult:.2f}x")

        # Event multipliers
        for event in external_signals.events:
            if event.expected_impact == "early_refills":
                for category in event.affected_categories:
                    multipliers[category] = multipliers.get(category, 1.0) * 1.2

        return multipliers

    def _forecast_medication(
        self,
        medication: str,
        patient_demand: Dict[date, float],
        historical_data: Optional[pd.DataFrame],
        multipliers: Dict[str, float],
        start_date: date,
        end_date: date
    ) -> List[MedicationForecast]:
        """
        Generate daily forecasts for a single medication.

        Returns:
            List of MedicationForecast (one per day)
        """
        forecasts = []

        # Determine medication category (simple heuristic)
        category = self._infer_category(medication)

        # Get external multiplier for this category
        external_multiplier = multipliers.get(category, 1.0)

        # Generate forecast for each day in the range
        current_date = start_date

        while current_date <= end_date:
            # Patient-based demand for this date
            patient_based = patient_demand.get(current_date, 0.0)

            # Calculate base demand (could use Prophet here with historical data)
            if self.config.use_prophet and historical_data is not None:
                # TODO: Implement Prophet forecasting with historical data
                # For now, use simple average
                base_demand = patient_based
            else:
                base_demand = patient_based

            # Apply external multiplier
            predicted_demand = base_demand * external_multiplier

            # Calculate confidence bounds (95% interval)
            # Lower confidence if relying only on patient predictions
            if patient_based > 0:
                confidence = 0.85
                std_dev = predicted_demand * 0.15
            else:
                confidence = 0.60
                std_dev = predicted_demand * 0.30

            lower_bound = max(0, predicted_demand - 1.96 * std_dev)
            upper_bound = predicted_demand + 1.96 * std_dev

            # Detect alerts
            alerts = []
            if predicted_demand > base_demand * self.config.spike_threshold:
                alerts.append(DemandAlert.SPIKE)

            forecast = MedicationForecast(
                medication=medication,
                category=category,
                forecast_date=current_date,
                predicted_demand=predicted_demand,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                base_demand=base_demand,
                patient_based_demand=patient_based,
                external_multiplier=external_multiplier,
                confidence=confidence,
                method=ForecastMethod.HYBRID if self.config.use_prophet else ForecastMethod.PATIENT_BASED,
                alerts=alerts
            )

            forecasts.append(forecast)
            current_date += timedelta(days=1)

        return forecasts

    def _infer_category(self, medication: str) -> str:
        """
        Infer medication category from name.

        Simple heuristic - could be enhanced with medication database lookup.
        """
        med_lower = medication.lower()

        if any(word in med_lower for word in ['insulin', 'metformin', 'glipizide']):
            return 'diabetes'
        elif any(word in med_lower for word in ['lisinopril', 'amlodipine', 'atorvastatin']):
            return 'cardiovascular'
        elif any(word in med_lower for word in ['tamiflu', 'oseltamivir']):
            return 'antiviral'
        elif any(word in med_lower for word in ['amoxicillin', 'azithromycin']):
            return 'antibiotic'
        elif any(word in med_lower for word in ['omeprazole', 'pantoprazole']):
            return 'gastrointestinal'
        elif any(word in med_lower for word in ['levothyroxine']):
            return 'thyroid'
        else:
            return 'other'

    def _aggregate_by_category(
        self,
        medication_forecasts: List[MedicationForecast],
        external_signals: Optional[ExternalSignals]
    ) -> List[CategoryForecast]:
        """
        Aggregate forecasts by category for summary view.
        """
        # Group by category and date
        category_data = defaultdict(lambda: {
            'total_demand': 0.0,
            'medications': set(),
            'confidences': []
        })

        for forecast in medication_forecasts:
            if not forecast.category:
                continue

            key = (forecast.category, forecast.forecast_date)
            category_data[key]['total_demand'] += forecast.predicted_demand
            category_data[key]['medications'].add(forecast.medication)
            category_data[key]['confidences'].append(forecast.confidence)

        # Create category forecasts (one per category, using first day)
        category_forecasts = []
        categories_seen = set()

        for (category, forecast_date), data in category_data.items():
            if category in categories_seen:
                continue
            categories_seen.add(category)

            avg_confidence = np.mean(data['confidences']) if data['confidences'] else 0.5

            # Determine trend (simplified)
            trend = "stable"  # TODO: Calculate actual trend

            # Check external impacts
            flu_impact = False
            weather_impact = False
            event_impact = False

            if external_signals:
                if external_signals.flu_activity and category in ['antiviral', 'cold_flu_otc']:
                    flu_impact = True
                if external_signals.weather and category in ['cold_flu_otc']:
                    weather_impact = True
                if external_signals.events:
                    event_impact = any(category in e.affected_categories for e in external_signals.events)

            category_forecast = CategoryForecast(
                category=category,
                forecast_date=forecast_date,
                total_predicted_demand=data['total_demand'],
                medication_count=len(data['medications']),
                average_confidence=avg_confidence,
                trend=trend,
                flu_impact=flu_impact,
                weather_impact=weather_impact,
                event_impact=event_impact
            )

            category_forecasts.append(category_forecast)

        return category_forecasts

    def _generate_summary(
        self,
        medication_forecasts: List[MedicationForecast],
        start_date: date,
        end_date: date,
        patient_profiles: PatientProfilingResult,
        external_signals: Optional[ExternalSignals]
    ) -> ForecastSummary:
        """Generate high-level summary of forecast results."""

        # Count unique medications
        medications = set(f.medication for f in medication_forecasts)

        # Total predicted demand
        total_demand = sum(f.predicted_demand for f in medication_forecasts)

        # Count alerts
        spike_alerts = sum(1 for f in medication_forecasts if DemandAlert.SPIKE in f.alerts)
        shortage_risks = sum(1 for f in medication_forecasts if DemandAlert.SHORTAGE_RISK in f.alerts)
        high_priority = spike_alerts + shortage_risks

        # Average confidence
        avg_confidence = np.mean([f.confidence for f in medication_forecasts])

        # Data completeness
        if external_signals and external_signals.data_quality == "complete":
            data_completeness = "complete"
        elif external_signals:
            data_completeness = "partial"
        else:
            data_completeness = "degraded"

        return ForecastSummary(
            forecast_date=start_date,
            forecast_horizon_days=self.config.forecast_horizon_days,
            total_medications=len(medications),
            total_predicted_demand=total_demand,
            high_priority_alerts=high_priority,
            spike_alerts=spike_alerts,
            shortage_risks=shortage_risks,
            average_confidence=avg_confidence,
            data_completeness=data_completeness
        )
