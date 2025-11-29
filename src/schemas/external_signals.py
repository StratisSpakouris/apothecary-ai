"""
External Signals Data Schemas

Defines data structures for external factors affecting pharmacy demand.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date, datetime
from enum import Enum


class TrendDirection(str, Enum):
    """Direction of a trend."""
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"
    RAPID_INCREASE = "rapid_increase"
    RAPID_DECREASE = "rapid_decrease"


class FluActivity(BaseModel):
    """Influenza activity data from EODY reports."""
    
    level: int = Field(
        ...,
        ge=1,
        le=10,
        description="Flu activity level (1=minimal, 10=very high)"
    )
    trend: TrendDirection = Field(
        ...,
        description="Direction of flu activity trend"
    )
    week_over_week_change: float = Field(
        ...,
        description="Percentage change from previous week"
    )
    region: str = Field(
        ...,
        description="Geographic region for this data"
    )
    ili_percentage: Optional[float] = Field(
        None,
        description="Percentage of visits for influenza-like illness or ILI rate per 100k"
    )
    data_date: date = Field(
        ...,
        description="Date this data represents"
    )
    
    def get_demand_multiplier(self) -> float:
        """
        Calculate demand multiplier for antiviral medications.
        
        Returns:
            Multiplier (1.0 = normal, 2.0 = double demand, etc.)
        """
        # Base multiplier from level
        # Level 1-3: normal demand
        # Level 4-6: moderate increase
        # Level 7-10: significant increase
        if self.level <= 3:
            base = 1.0
        elif self.level <= 6:
            base = 1.0 + (self.level - 3) * 0.15  # 1.15 to 1.45
        else:
            base = 1.45 + (self.level - 6) * 0.20  # 1.65 to 2.25
        
        # Adjust for trend
        trend_adjustment = {
            TrendDirection.RAPID_INCREASE: 1.2,
            TrendDirection.INCREASING: 1.1,
            TrendDirection.STABLE: 1.0,
            TrendDirection.DECREASING: 0.95,
            TrendDirection.RAPID_DECREASE: 0.9
        }
        
        return round(base * trend_adjustment[self.trend], 2)


class WeatherData(BaseModel):
    """Weather data affecting pharmacy demand."""
    
    temperature_avg_f: float = Field(
        ...,
        description="Average temperature in Fahrenheit"
    )
    temperature_min_f: float = Field(
        ...,
        description="Minimum temperature in Fahrenheit"
    )
    temperature_max_f: float = Field(
        ...,
        description="Maximum temperature in Fahrenheit"
    )
    humidity_percent: float = Field(
        ...,
        ge=0,
        le=100,
        description="Humidity percentage"
    )
    precipitation_probability: float = Field(
        ...,
        ge=0,
        le=1,
        description="Probability of precipitation"
    )
    conditions: str = Field(
        ...,
        description="Weather conditions description"
    )
    is_cold_snap: bool = Field(
        False,
        description="True if sudden temperature drop detected"
    )
    forecast_date: date = Field(
        ...,
        description="Date this forecast is for"
    )
    
    def get_cold_flu_multiplier(self) -> float:
        """
        Calculate demand multiplier for cold/flu medications.
        
        Cold weather increases cold/flu medication demand.
        """
        multiplier = 1.0
        
        # Cold temperature effect
        if self.temperature_avg_f < 32:
            multiplier += 0.3
        elif self.temperature_avg_f < 45:
            multiplier += 0.15
        
        # Cold snap effect (sudden drop)
        if self.is_cold_snap:
            multiplier += 0.2
        
        # High humidity can increase respiratory issues
        if self.humidity_percent > 80:
            multiplier += 0.05
        
        return round(multiplier, 2)


class DrugShortage(BaseModel):
    """Information about a drug shortage."""
    
    medication: str = Field(
        ...,
        description="Medication name"
    )
    status: str = Field(
        ...,
        description="Shortage status: current, resolved, discontinuation"
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for shortage"
    )
    estimated_resolution: Optional[date] = Field(
        None,
        description="Estimated date shortage will be resolved"
    )
    alternatives: List[str] = Field(
        default_factory=list,
        description="Alternative medications"
    )


class SupplyChainStatus(BaseModel):
    """Overall supply chain status."""
    
    shortages_detected: List[DrugShortage] = Field(
        default_factory=list,
        description="List of current drug shortages"
    )
    potential_shortages: List[str] = Field(
        default_factory=list,
        description="Medications at risk of shortage"
    )
    last_updated: datetime = Field(
        ...,
        description="When this data was last updated"
    )


class LocalEvent(BaseModel):
    """Local event that may affect pharmacy demand."""
    
    event_name: str = Field(
        ...,
        description="Name of the event"
    )
    event_date: date = Field(
        ...,
        description="Date of the event"
    )
    event_type: str = Field(
        ...,
        description="Type: holiday, festival, school, sports, health, seasonal, other"
    )
    expected_impact: str = Field(
        ...,
        description="Expected impact on demand: increase, decrease, early_refills"
    )
    affected_categories: List[str] = Field(
        default_factory=list,
        description="Medication categories affected"
    )


class ExternalSignals(BaseModel):
    """
    Complete external signals data.
    
    Aggregates all external factors that affect pharmacy demand.
    Used by Forecasting Agent to adjust predictions.
    """
    
    flu_activity: Optional[FluActivity] = Field(
        None,
        description="Current flu activity data"
    )
    weather: Optional[WeatherData] = Field(
        None,
        description="Weather data and forecast"
    )
    supply_chain: Optional[SupplyChainStatus] = Field(
        None,
        description="Supply chain and shortage status"
    )
    events: List[LocalEvent] = Field(
        default_factory=list,
        description="Upcoming local events"
    )
    fetch_timestamp: datetime = Field(
        ...,
        description="When this data was fetched"
    )
    data_quality: str = Field(
        "complete",
        description="Data quality: complete, partial, degraded"
    )
    
    def get_medication_multipliers(self) -> Dict[str, float]:
        """
        Get demand multipliers for different medication categories.
        
        Returns:
            Dict mapping category to demand multiplier
        """
        multipliers = {}
        
        # Antiviral multiplier (from flu data)
        if self.flu_activity:
            multipliers["antiviral"] = self.flu_activity.get_demand_multiplier()
        
        # Cold/flu OTC multiplier (from weather + flu)
        cold_flu_mult = 1.0
        if self.weather:
            cold_flu_mult *= self.weather.get_cold_flu_multiplier()
        if self.flu_activity:
            cold_flu_mult *= (1 + (self.flu_activity.level - 5) * 0.05)
        multipliers["cold_flu"] = round(cold_flu_mult, 2)
        
        return multipliers

    class Config:
        json_schema_extra = {
            "example": {
                "flu_activity": {
                    "level": 7,
                    "trend": "increasing",
                    "week_over_week_change": 15.5,
                    "region": "Greece",
                    "data_date": "2024-11-15"
                },
                "weather": {
                    "temperature_avg_f": 38,
                    "temperature_min_f": 28,
                    "temperature_max_f": 45,
                    "humidity_percent": 65,
                    "precipitation_probability": 0.3,
                    "conditions": "Partly cloudy",
                    "is_cold_snap": True,
                    "forecast_date": "2024-11-20"
                },
                "fetch_timestamp": "2024-11-20T10:30:00",
                "data_quality": "complete"
            }
        }
