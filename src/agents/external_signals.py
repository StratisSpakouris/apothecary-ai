"""
External Signals Agent

Monitors external factors that affect pharmacy demand:
- Flu activity (from manually uploaded EODY reports OR simulation)
- Weather conditions (OpenWeather API or simulation)
- Drug shortages (simulated)
- Local events (holidays, etc.)

This agent gathers environmental context that the Forecasting Agent
uses to adjust demand predictions beyond patient patterns.

Supports Greece with European country extensions.
Does NOT use LLM directly - relies on pre-processed report data.
"""

from src.utils.logging import setup_logger
from src.schemas.external_signals import (
    ExternalSignals,
    FluActivity,
    WeatherData,
    SupplyChainStatus,
    DrugShortage,
    LocalEvent,
    TrendDirection
)
from src.services.eody_reports import EODYReportsService
from src.services.weather_api import WeatherAPI

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import holidays


class ExternalSignalsAgent:
    """
    Agent responsible for gathering external signals affecting demand.
    
    Data Sources:
    - EODY reports (manually uploaded, processed with Gemini)
    - OpenWeather API (weather conditions)
    - Simulated sources (supply chain, events)
    
    Focuses on Greece with support for other European countries.
    """
    
    # Supported countries for holiday calendars
    HOLIDAY_COUNTRIES = {
        "greece": holidays.Greece,
        "GR": holidays.Greece,
        "germany": holidays.Germany,
        "DE": holidays.Germany,
        "france": holidays.France,
        "FR": holidays.France,
        "italy": holidays.Italy,
        "IT": holidays.Italy,
        "spain": holidays.Spain,
        "ES": holidays.Spain,
        "portugal": holidays.Portugal,
        "PT": holidays.Portugal,
        "netherlands": holidays.Netherlands,
        "NL": holidays.Netherlands,
        "belgium": holidays.Belgium,
        "BE": holidays.Belgium,
        "austria": holidays.Austria,
        "AT": holidays.Austria,
    }
    
    def __init__(
        self,
        config: Dict = None,
        country: str = "greece",
        location: str = "Athens,GR"
    ):
        """
        Initialize External Signals Agent.

        Args:
            config: Optional configuration dictionary
            country: Country for holidays and flu data (default: Greece)
            location: City for weather data (default: Athens, Greece)
        """
        self.name = "ExternalSignalsAgent"
        self.logger = setup_logger(self.name)
        self.config = config or {}
        self.country = country
        self.location = location
        
        # Initialize services
        self.eody_service = EODYReportsService()
        self.weather_api = WeatherAPI(location=location)
        
        # Initialize holiday calendar
        holiday_class = self.HOLIDAY_COUNTRIES.get(
            country.lower() if len(country) > 2 else country.upper(),
            holidays.Greece  # Default to Greece
        )
        self.country_holidays = holiday_class()
        
        self.logger.info(
            f"Configured for country: {country}, location: {location}"
        )
    
    def execute(self, target_date: date = None) -> ExternalSignals:
        """
        Gather all external signals for a target date.
        
        Args:
            target_date: Date to gather signals for (default: today)
            
        Returns:
            ExternalSignals with all collected data
        """
        if target_date is None:
            target_date = date.today()
        
        self.logger.info(f"Gathering external signals for {target_date}")
        
        # Track data quality
        data_quality = "complete"
        errors = []
        
        # 1. Get flu activity (from EODY reports or simulation)
        flu_activity = None
        try:
            flu_data = self._get_flu_data()
            flu_activity = self._parse_flu_data(flu_data, target_date)
            
            source = flu_data.get('source', 'unknown')
            self.logger.info(
                f"Flu activity: level {flu_activity.level}/10 "
                f"({flu_activity.trend.value}) [source: {source}]"
            )
        except Exception as e:
            self.logger.error(f"Failed to get flu data: {e}")
            errors.append("flu")
        
        # 2. Get weather data
        weather = None
        try:
            weather_data = self.weather_api.get_current_weather(target_date)
            weather = self._parse_weather_data(weather_data)
            self.logger.info(
                f"Weather: {weather.temperature_avg_f}°F, {weather.conditions}"
            )
        except Exception as e:
            self.logger.error(f"Failed to get weather data: {e}")
            errors.append("weather")
        
        # 3. Get supply chain status (simulated)
        supply_chain = self._get_supply_chain_status()
        if supply_chain.shortages_detected:
            self.logger.warning(
                f"Drug shortages: {len(supply_chain.shortages_detected)} detected"
            )
        
        # 4. Get upcoming events (holidays, seasonal patterns)
        events = self._get_upcoming_events(target_date, days_ahead=14)
        self.logger.info(f"Upcoming events: {len(events)}")
        
        # Determine overall data quality
        if len(errors) > 2:
            data_quality = "degraded"
        elif len(errors) > 0:
            data_quality = "partial"
        
        return ExternalSignals(
            flu_activity=flu_activity,
            weather=weather,
            supply_chain=supply_chain,
            events=events,
            fetch_timestamp=datetime.now(),
            data_quality=data_quality
        )
    
    # =========================================================================
    # FLU ACTIVITY METHODS
    # =========================================================================
    
    def _get_flu_data(self) -> Dict:
        """
        Get flu data from processed EODY reports or generate simulation.
        
        Priority:
        1. Processed EODY reports (if available)
        2. Simulation based on seasonal patterns
        
        Returns:
            Dict with flu data including 'source' field
        """
        # Try to load from processed EODY reports
        if self.eody_service.has_reports():
            report_data = self.eody_service.get_latest_report()
            if report_data:
                self.logger.info("Using data from processed EODY report")
                return {
                    **report_data,
                    'source': 'eody_report'
                }
        
        # Fall back to simulation
        self.logger.info("No EODY reports available, using simulation")
        return self._generate_simulated_flu_data()
    
    def _generate_simulated_flu_data(self) -> Dict:
        """
        Generate simulated flu data based on seasonal patterns.
        
        Uses realistic seasonal patterns for Greece/Mediterranean region.
        
        Returns:
            Dict with simulated flu data
        """
        import random
        
        current_month = date.today().month
        
        # Seasonal flu levels for Greece (Mediterranean pattern)
        # Peak: January-February
        # Low: May-September
        seasonal_levels = {
            1: 8,   # January - peak
            2: 7,   # February - high
            3: 5,   # March - declining
            4: 3,   # April - low
            5: 1,   # May - minimal
            6: 1,   # June - minimal
            7: 1,   # July - minimal
            8: 1,   # August - minimal
            9: 2,   # September - starting
            10: 3,  # October - increasing
            11: 5,  # November - moderate
            12: 7,  # December - high
        }
        
        # Get base level for current month
        base_level = seasonal_levels[current_month]
        
        # Add random daily variation (±1 level)
        variation = random.choice([-1, 0, 0, 0, 1])
        level = max(1, min(10, base_level + variation))
        
        # Determine trend based on seasonal progression
        next_month = (current_month % 12) + 1
        next_level = seasonal_levels[next_month]
        
        if next_level > base_level + 1:
            trend = "rapid_increase"
        elif next_level > base_level:
            trend = "increasing"
        elif next_level < base_level - 1:
            trend = "rapid_decrease"
        elif next_level < base_level:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # Calculate ILI rate (typical range: 20-200 per 100k during flu season)
        ili_rate = 20 + (level - 1) * 20 + random.uniform(-10, 10)
        
        # Calculate positivity rate (% of samples positive for flu)
        positivity = 5 + (level - 1) * 5 + random.uniform(-3, 3)
        positivity = max(0, min(50, positivity))
        
        return {
            'flu_level': level,
            'trend': trend,
            'ili_rate_per_100k': round(ili_rate, 1),
            'confirmed_cases': None,
            'dominant_strain': None,
            'positivity_rate': round(positivity, 1),
            'confidence': 0.5,
            'summary': f"Simulated flu data based on seasonal patterns (month {current_month})",
            'week_number': None,
            'report_period': None,
            'source': 'simulation'
        }
    
    def _parse_flu_data(self, flu_data: Dict, target_date: date) -> FluActivity:
        """
        Parse flu data dictionary into FluActivity model.
        
        Args:
            flu_data: Dictionary with flu data
            target_date: Date this data represents
            
        Returns:
            FluActivity model instance
        """
        # Map string trends to enum
        trend_map = {
            "rapid_increase": TrendDirection.RAPID_INCREASE,
            "increasing": TrendDirection.INCREASING,
            "stable": TrendDirection.STABLE,
            "decreasing": TrendDirection.DECREASING,
            "rapid_decrease": TrendDirection.RAPID_DECREASE
        }
        
        return FluActivity(
            level=flu_data['flu_level'],
            trend=trend_map.get(flu_data['trend'], TrendDirection.STABLE),
            week_over_week_change=0.0,  # Not always available
            region=self.country,
            ili_percentage=flu_data.get('ili_rate_per_100k'),
            data_date=target_date
        )
    
    # =========================================================================
    # WEATHER METHODS
    # =========================================================================
    
    def _parse_weather_data(self, raw_data: Dict) -> WeatherData:
        """
        Parse raw weather data into WeatherData model.
        
        Args:
            raw_data: Dictionary with weather data
            
        Returns:
            WeatherData model instance
        """
        return WeatherData(
            temperature_avg_f=raw_data["temperature_avg_f"],
            temperature_min_f=raw_data["temperature_min_f"],
            temperature_max_f=raw_data["temperature_max_f"],
            humidity_percent=raw_data["humidity_percent"],
            precipitation_probability=raw_data["precipitation_probability"],
            conditions=raw_data["conditions"],
            is_cold_snap=raw_data["is_cold_snap"],
            forecast_date=date.fromisoformat(raw_data["forecast_date"])
        )
    
    # =========================================================================
    # SUPPLY CHAIN METHODS
    # =========================================================================
    
    def _get_supply_chain_status(self) -> SupplyChainStatus:
        """
        Get supply chain status including drug shortages.
        
        Currently simulated. In production, this would query:
        - EMA (European Medicines Agency) shortage database
        - National shortage databases (e.g., Greek EOF)
        
        Returns:
            SupplyChainStatus with current shortage information
        """
        # Simulate realistic drug shortages for Greece/Europe
        current_shortages = [
            DrugShortage(
                medication="Amoxicillin 500mg",
                status="current",
                reason="Manufacturing capacity constraints",
                estimated_resolution=date.today() + timedelta(days=45),
                alternatives=["Amoxicillin/Clavulanate", "Azithromycin"]
            ),
            DrugShortage(
                medication="Salbutamol Inhaler",
                status="current",
                reason="Supply chain disruption",
                estimated_resolution=date.today() + timedelta(days=30),
                alternatives=["Terbutaline Inhaler"]
            ),
        ]
        
        potential_shortages = [
            "Metformin 850mg",
            "Omeprazole 20mg"
        ]
        
        return SupplyChainStatus(
            shortages_detected=current_shortages,
            potential_shortages=potential_shortages,
            last_updated=datetime.now()
        )
    
    # =========================================================================
    # EVENT METHODS
    # =========================================================================
    
    def _get_upcoming_events(
        self, 
        target_date: date, 
        days_ahead: int = 14
    ) -> List[LocalEvent]:
        """
        Get upcoming events that may affect pharmacy demand.
        
        Includes:
        - National holidays (country-specific)
        - Flu season warnings
        - Tourist season (for Greece)
        
        Args:
            target_date: Starting date
            days_ahead: Number of days to look ahead
            
        Returns:
            List of LocalEvent objects
        """
        events = []
        
        # Check for holidays in the upcoming period
        for day_offset in range(days_ahead + 1):
            check_date = target_date + timedelta(days=day_offset)
            
            if check_date in self.country_holidays:
                holiday_name = str(self.country_holidays.get(check_date))
                
                # Determine if this is a major holiday
                major_holiday_keywords = [
                    "Πάσχα", "Easter",           # Greek/English Easter
                    "Christmas", "Χριστούγεννα", # Christmas
                    "New Year", "Πρωτοχρονιά",   # New Year
                    "Assumption", "Κοίμηση",     # Assumption of Mary
                    "National Day", "Εθνική"     # National holidays
                ]
                
                is_major = any(
                    keyword in holiday_name 
                    for keyword in major_holiday_keywords
                )
                
                # Major holidays cause early refills
                # Minor holidays may reduce pharmacy traffic
                impact = "early_refills" if is_major else "decrease"
                affected = ["all"] if is_major else []
                
                events.append(LocalEvent(
                    event_name=holiday_name,
                    event_date=check_date,
                    event_type="holiday",
                    expected_impact=impact,
                    affected_categories=affected
                ))
        
        # Add flu season warning (November through February)
        if target_date.month in [11, 12, 1, 2]:
            events.append(LocalEvent(
                event_name="Flu Season Peak Period",
                event_date=target_date,
                event_type="health",
                expected_impact="increase",
                affected_categories=["antiviral", "cold_flu"]
            ))
        
        # Add tourist season for Greece (June-August)
        if target_date.month in [6, 7, 8] and self.country.lower() in ["greece", "gr"]:
            events.append(LocalEvent(
                event_name="Tourist Season",
                event_date=target_date,
                event_type="seasonal",
                expected_impact="increase",
                affected_categories=["gastrointestinal", "suncare", "first_aid"]
            ))
        
        return events
    
    # =========================================================================
    # DEMAND ADJUSTMENT METHODS
    # =========================================================================
    
    def get_demand_adjustments(
        self, 
        signals: ExternalSignals
    ) -> Dict[str, Dict]:
        """
        Calculate demand adjustments for different medication categories.
        
        Combines signals from flu activity, weather, and events to
        produce category-specific demand multipliers.
        
        Args:
            signals: ExternalSignals data
            
        Returns:
            Dict mapping category name to adjustment info:
            {
                "category": {
                    "multiplier": float,
                    "confidence": float,
                    "reason": str
                }
            }
        """
        adjustments = {}
        
        # 1. ANTIVIRAL MEDICATIONS (Tamiflu, Oseltamivir, etc.)
        if signals.flu_activity:
            flu_mult = signals.flu_activity.get_demand_multiplier()
            
            adjustments["antiviral"] = {
                "multiplier": flu_mult,
                "confidence": 0.85,
                "reason": (
                    f"Flu activity at level {signals.flu_activity.level}/10 "
                    f"({signals.flu_activity.trend.value})"
                )
            }
        
        # 2. COLD/FLU OTC MEDICATIONS (DayQuil, NyQuil, etc.)
        cold_mult = 1.0
        cold_reasons = []
        
        # Weather contribution
        if signals.weather:
            weather_mult = signals.weather.get_cold_flu_multiplier()
            if weather_mult > 1.0:
                cold_mult *= weather_mult
                temp_c = (signals.weather.temperature_avg_f - 32) * 5/9
                cold_reasons.append(f"Cold weather ({temp_c:.1f}°C)")
            
            if signals.weather.is_cold_snap:
                cold_mult *= 1.1
                cold_reasons.append("Sudden temperature drop")
        
        # Flu activity contribution
        if signals.flu_activity and signals.flu_activity.level > 5:
            flu_boost = (signals.flu_activity.level - 5) * 0.08
            cold_mult *= (1 + flu_boost)
            cold_reasons.append("Elevated flu activity")
        
        # Only add if there's an actual increase
        if cold_mult > 1.05:  # At least 5% increase
            adjustments["cold_flu"] = {
                "multiplier": round(cold_mult, 2),
                "confidence": 0.75,
                "reason": "; ".join(cold_reasons)
            }
        
        # 3. CHRONIC MEDICATIONS (early refills before holidays)
        for event in signals.events:
            if event.expected_impact == "early_refills":
                if "chronic" not in adjustments:
                    adjustments["chronic"] = {
                        "multiplier": 1.15,
                        "confidence": 0.70,
                        "reason": f"Early refills expected before {event.event_name}"
                    }
                break  # Only need one holiday to trigger this
        
        # 4. GASTROINTESTINAL MEDICATIONS (tourist season for Greece)
        for event in signals.events:
            if event.event_name == "Tourist Season":
                adjustments["gastrointestinal"] = {
                    "multiplier": 1.25,
                    "confidence": 0.65,
                    "reason": "Tourist season increases GI medication demand"
                }
                break
        
        return adjustments
