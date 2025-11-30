"""
Forecasting Schemas

Data structures for medication demand forecasting.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import date
from enum import Enum


class ForecastMethod(str, Enum):
    """Method used for forecasting."""
    PROPHET = "prophet"
    PATIENT_BASED = "patient_based"
    HYBRID = "hybrid"
    SIMPLE_AVERAGE = "simple_average"


class DemandAlert(str, Enum):
    """Alert types for demand forecasting."""
    SPIKE = "spike"  # Unusual demand increase
    DROP = "drop"  # Unusual demand decrease
    SEASONAL_PEAK = "seasonal_peak"  # Expected seasonal high
    SHORTAGE_RISK = "shortage_risk"  # Risk of running out
    OVERSTOCK_RISK = "overstock_risk"  # Risk of excess inventory


class MedicationForecast(BaseModel):
    """
    Demand forecast for a single medication.
    """

    medication: str = Field(..., description="Medication name")
    category: Optional[str] = Field(None, description="Medication category")

    # Forecast data
    forecast_date: date = Field(..., description="Date of this forecast")
    predicted_demand: float = Field(..., description="Predicted daily demand (units)")
    lower_bound: float = Field(..., description="Lower 95% confidence bound")
    upper_bound: float = Field(..., description="Upper 95% confidence bound")

    # Components
    base_demand: float = Field(..., description="Base demand without adjustments")
    patient_based_demand: float = Field(..., description="Demand from patient predictions")
    external_multiplier: float = Field(1.0, description="External signals multiplier")

    # Metadata
    confidence: float = Field(..., ge=0, le=1, description="Forecast confidence (0-1)")
    method: ForecastMethod = Field(..., description="Forecasting method used")
    alerts: List[DemandAlert] = Field(default_factory=list, description="Any alerts for this forecast")


class CategoryForecast(BaseModel):
    """
    Aggregated forecast for a medication category.
    """

    category: str = Field(..., description="Medication category name")
    forecast_date: date = Field(..., description="Date of this forecast")

    # Aggregated metrics
    total_predicted_demand: float = Field(..., description="Total demand across all medications")
    medication_count: int = Field(..., description="Number of medications in category")

    # Confidence and trends
    average_confidence: float = Field(..., ge=0, le=1, description="Average forecast confidence")
    trend: str = Field(..., description="Overall trend (increasing, stable, decreasing)")

    # External factors
    flu_impact: bool = Field(False, description="Flu activity affecting this category")
    weather_impact: bool = Field(False, description="Weather affecting this category")
    event_impact: bool = Field(False, description="Events affecting this category")


class ForecastSummary(BaseModel):
    """
    High-level summary of forecast results.
    """

    forecast_date: date = Field(..., description="Date of this forecast")
    forecast_horizon_days: int = Field(..., description="Number of days forecasted")

    # Overall metrics
    total_medications: int = Field(..., description="Number of medications forecasted")
    total_predicted_demand: float = Field(..., description="Total demand across all medications")

    # Alerts
    high_priority_alerts: int = Field(0, description="Number of high-priority alerts")
    spike_alerts: int = Field(0, description="Number of demand spike alerts")
    shortage_risks: int = Field(0, description="Number of shortage risk alerts")

    # Data quality
    average_confidence: float = Field(..., ge=0, le=1, description="Average forecast confidence")
    data_completeness: str = Field(..., description="complete, partial, or degraded")


class ForecastingResult(BaseModel):
    """
    Complete forecasting result for all medications.

    This is the main output from the ForecastingAgent.
    """

    # Time range
    analysis_date: date = Field(..., description="When this forecast was generated")
    forecast_start_date: date = Field(..., description="First day of forecast period")
    forecast_end_date: date = Field(..., description="Last day of forecast period")

    # Forecasts
    medication_forecasts: List[MedicationForecast] = Field(
        ...,
        description="Daily forecasts for each medication"
    )
    category_forecasts: List[CategoryForecast] = Field(
        default_factory=list,
        description="Aggregated forecasts by category"
    )

    # Summary
    summary: ForecastSummary = Field(..., description="High-level summary")

    # Inputs used
    patient_profiles_count: int = Field(..., description="Number of patient profiles used")
    external_signals_available: bool = Field(..., description="Were external signals available")

    # Metadata
    method: ForecastMethod = Field(..., description="Primary forecasting method")
    notes: List[str] = Field(default_factory=list, description="Any notes or warnings")

    def get_forecast_for_medication(self, medication: str, forecast_date: date) -> Optional[MedicationForecast]:
        """Get forecast for specific medication and date."""
        for forecast in self.medication_forecasts:
            if forecast.medication == medication and forecast.forecast_date == forecast_date:
                return forecast
        return None

    def get_high_risk_medications(self) -> List[MedicationForecast]:
        """Get medications with shortage or spike alerts."""
        return [
            f for f in self.medication_forecasts
            if DemandAlert.SHORTAGE_RISK in f.alerts or DemandAlert.SPIKE in f.alerts
        ]

    def get_category_summary(self, category: str) -> Optional[CategoryForecast]:
        """Get summary for specific category."""
        for cat_forecast in self.category_forecasts:
            if cat_forecast.category == category:
                return cat_forecast
        return None


class ForecastingConfig(BaseModel):
    """
    Configuration for ForecastingAgent.
    """

    forecast_horizon_days: int = Field(30, description="Number of days to forecast")
    confidence_level: float = Field(0.95, description="Confidence level for intervals (0-1)")

    # Method settings
    use_prophet: bool = Field(True, description="Use Prophet for time series forecasting")
    use_patient_predictions: bool = Field(True, description="Incorporate patient refill predictions")
    use_external_signals: bool = Field(True, description="Apply external signal multipliers")

    # Alert thresholds
    spike_threshold: float = Field(1.5, description="Demand increase to trigger spike alert (multiplier)")
    shortage_risk_threshold: float = Field(0.8, description="Inventory level to trigger shortage alert")

    # Prophet parameters
    prophet_seasonality_mode: str = Field("multiplicative", description="Prophet seasonality mode")
    prophet_changepoint_prior_scale: float = Field(0.05, description="Prophet flexibility")
