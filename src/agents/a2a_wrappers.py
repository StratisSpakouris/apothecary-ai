"""
A2A Wrapper Agents

Wraps existing deterministic agents as Google ADK LlmAgents
to enable Agent-to-Agent (A2A) protocol communication.
"""

import os
import json
import asyncio
from datetime import date
from pathlib import Path
from typing import Optional
import pandas as pd

from google.adk import LlmAgent
from google.adk.runners import InMemoryRunner
from dotenv import load_dotenv

from src.agents import (
    PatientProfilingAgent,
    ExternalSignalsAgent,
    ForecastingAgent,
    OptimizationAgent
)
from src.schemas.forecasting import ForecastingConfig
from src.schemas.optimization import OptimizationConfig
from src.utils.logging import setup_logger

load_dotenv()


# ============================================================================
# PATIENT ANALYSIS A2A AGENT
# ============================================================================

class PatientAnalysisA2AAgent:
    """
    A2A wrapper for PatientProfilingAgent.
    Exposes patient profiling capabilities via Agent-to-Agent protocol.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.logger = setup_logger("PatientAnalysisA2AAgent")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        # Load data
        self.prescription_data = pd.read_csv("data/raw/patients/prescription_history.csv")

        # Initialize underlying agent
        self.profiling_agent = PatientProfilingAgent()

        # Create ADK agent
        self.agent = self._build_agent()
        self.runner = InMemoryRunner(agent=self.agent)

    def _build_agent(self) -> LlmAgent:
        """Build ADK LlmAgent for patient analysis"""

        instruction = """You are the Patient Analysis Agent.

Your role is to analyze patient prescription refill patterns and predict future refills.

**Capabilities:**
- Analyze refill intervals and consistency
- Classify patient behavior (highly_regular, regular, irregular, new_patient)
- Predict next refill dates with 95% confidence intervals
- Identify patients at risk of medication lapse
- Calculate refill pattern statistics

**When to use this agent:**
- User asks about patient refill patterns
- User wants to know which patients need refills soon
- User asks for patient behavior analysis
- User wants to identify high-risk patients

**Input:** Analysis date (defaults to today)
**Output:** Patient profiles with refill predictions and risk scores

You will execute the analysis by calling the underlying PatientProfilingAgent and returning structured results.
"""

        return LlmAgent(
            name="PatientAnalysisAgent",
            model="gemini-2.0-flash-exp",
            instruction=instruction,
            description="Analyzes patient prescription refill patterns and predicts future refills"
        )

    async def execute_async(self, analysis_date: Optional[date] = None) -> str:
        """Execute patient analysis asynchronously"""
        analysis_date = analysis_date or date.today()

        self.logger.info(f"Running patient analysis for {analysis_date}")

        # Run underlying agent
        result = self.profiling_agent.execute(
            self.prescription_data,
            analysis_date=analysis_date
        )

        # Format results
        summary = {
            "analysis_date": str(analysis_date),
            "total_profiles": result.total_patient_medications,
            "unique_patients": result.unique_patients,
            "due_soon_7_days": result.patients_due_soon,
            "high_risk_patients": sum(1 for p in result.profiles if p.risk_of_lapse >= 0.2),
            "behavior_breakdown": {
                "highly_regular": sum(1 for p in result.profiles if p.refill_pattern.behavior_classification == "highly_regular"),
                "regular": sum(1 for p in result.profiles if p.refill_pattern.behavior_classification == "regular"),
                "irregular": sum(1 for p in result.profiles if p.refill_pattern.behavior_classification == "irregular"),
                "new_patient": sum(1 for p in result.profiles if p.refill_pattern.behavior_classification == "new_patient")
            }
        }

        return json.dumps(summary, indent=2)

    def execute(self, analysis_date: Optional[date] = None) -> str:
        """Synchronous execution wrapper"""
        return asyncio.run(self.execute_async(analysis_date))


# ============================================================================
# FORECASTING A2A AGENT
# ============================================================================

class ForecastingA2AAgent:
    """
    A2A wrapper for ForecastingAgent.
    Exposes demand forecasting capabilities via Agent-to-Agent protocol.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.logger = setup_logger("ForecastingA2AAgent")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        # Load data
        self.prescription_data = pd.read_csv("data/raw/patients/prescription_history.csv")

        # Initialize underlying agents
        self.profiling_agent = PatientProfilingAgent()
        self.external_agent = ExternalSignalsAgent(country="greece", location="Athens,GR")

        # Create ADK agent
        self.agent = self._build_agent()
        self.runner = InMemoryRunner(agent=self.agent)

    def _build_agent(self) -> LlmAgent:
        """Build ADK LlmAgent for forecasting"""

        instruction = """You are the Forecasting Agent.

Your role is to predict medication demand for upcoming periods.

**Capabilities:**
- Aggregate patient refill predictions by medication and date
- Apply external signal multipliers (flu activity, weather, events)
- Generate daily forecasts with confidence intervals
- Detect demand spikes and anomalies
- Support 7-90 day forecast horizons

**Inputs:**
- Patient profiling data (from PatientAnalysisAgent)
- External signals (flu, weather, events)
- Historical prescription data
- Forecast horizon (default: 30 days)

**Output:** Daily demand forecasts per medication with confidence scores

You will execute forecasting by coordinating with PatientAnalysisAgent and ExternalSignalsAgent, then running the ForecastingAgent.
"""

        return LlmAgent(
            name="ForecastingAgent",
            model="gemini-2.0-flash-exp",
            instruction=instruction,
            description="Forecasts medication demand based on patient patterns and external signals"
        )

    async def execute_async(self, forecast_days: int = 30,
                          target_date: Optional[date] = None,
                          category_filter: Optional[str] = None) -> str:
        """Execute forecasting asynchronously"""
        target_date = target_date or date.today()

        self.logger.info(f"Running forecast for {forecast_days} days from {target_date}")

        # Stage 1: Patient profiling
        patient_result = self.profiling_agent.execute(
            self.prescription_data,
            analysis_date=target_date
        )

        # Stage 2: External signals
        external_signals = self.external_agent.execute(target_date=target_date)

        # Stage 3: Forecasting
        forecast_config = ForecastingConfig(
            forecast_horizon_days=forecast_days,
            use_patient_predictions=True,
            use_external_signals=True
        )

        forecasting_agent = ForecastingAgent(config=forecast_config)
        forecast_result = forecasting_agent.execute(
            patient_profiles=patient_result,
            external_signals=external_signals,
            historical_data=self.prescription_data
        )

        # Filter by category if requested
        if category_filter:
            # Get medications in category
            medication_db = pd.read_csv("data/raw/medications/medication_database.csv")
            category_meds = medication_db[
                medication_db['category'] == category_filter
            ]['medication'].tolist()

            # Filter forecasts
            filtered_forecasts = [
                f for f in forecast_result.medication_forecasts
                if f.medication in category_meds
            ]

            total_demand = sum(f.total_predicted_demand for f in filtered_forecasts)
            avg_confidence = sum(f.average_confidence for f in filtered_forecasts) / len(filtered_forecasts) if filtered_forecasts else 0

            summary = {
                "forecast_period": f"{forecast_result.forecast_start_date} to {forecast_result.forecast_end_date}",
                "category": category_filter,
                "medications": len(filtered_forecasts),
                "total_demand": total_demand,
                "average_confidence": avg_confidence,
                "flu_multiplier": external_signals.flu_activity.get_demand_multiplier() if external_signals.flu_activity else 1.0
            }
        else:
            summary = {
                "forecast_period": f"{forecast_result.forecast_start_date} to {forecast_result.forecast_end_date}",
                "total_medications": forecast_result.summary.total_medications,
                "total_demand": forecast_result.summary.total_predicted_demand,
                "average_confidence": forecast_result.summary.average_confidence,
                "high_priority_alerts": forecast_result.summary.high_priority_alerts,
                "flu_multiplier": external_signals.flu_activity.get_demand_multiplier() if external_signals.flu_activity else 1.0
            }

        return json.dumps(summary, indent=2)

    def execute(self, forecast_days: int = 30,
               target_date: Optional[date] = None,
               category_filter: Optional[str] = None) -> str:
        """Synchronous execution wrapper"""
        return asyncio.run(self.execute_async(forecast_days, target_date, category_filter))


# ============================================================================
# COMPLETE ANALYSIS A2A AGENT
# ============================================================================

class CompleteAnalysisA2AAgent:
    """
    A2A wrapper for full pipeline execution.
    Runs patient profiling → external signals → forecasting → optimization.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.logger = setup_logger("CompleteAnalysisA2AAgent")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        # Load data
        self.prescription_data = pd.read_csv("data/raw/patients/prescription_history.csv")
        self.inventory_data = pd.read_csv("data/raw/inventory/current_stock.csv")
        self.medication_db = pd.read_csv("data/raw/medications/medication_database.csv")

        # Initialize underlying agents
        self.profiling_agent = PatientProfilingAgent()
        self.external_agent = ExternalSignalsAgent(country="greece", location="Athens,GR")

        # Create ADK agent
        self.agent = self._build_agent()
        self.runner = InMemoryRunner(agent=self.agent)

    def _build_agent(self) -> LlmAgent:
        """Build ADK LlmAgent for complete analysis"""

        instruction = """You are the Complete Analysis Agent.

Your role is to run the full Apothecary-AI pipeline and generate optimal inventory order recommendations.

**Pipeline Stages:**
1. Patient Profiling - Analyze refill patterns
2. External Signals - Gather flu, weather, event data
3. Forecasting - Predict medication demand
4. Optimization - Calculate optimal orders using EOQ

**Capabilities:**
- Complete end-to-end inventory analysis
- Economic Order Quantity (EOQ) optimization
- Safety stock calculations
- Priority-based order recommendations (critical, high, medium, low)
- Stockout and overstock risk assessment

**Output:** Order recommendations with quantities, costs, and priorities

This is the most comprehensive analysis - use when user wants order recommendations or complete inventory analysis.
"""

        return LlmAgent(
            name="CompleteAnalysisAgent",
            model="gemini-2.0-flash-exp",
            instruction=instruction,
            description="Runs full pipeline and generates optimal inventory order recommendations"
        )

    async def execute_async(self, analysis_date: Optional[date] = None) -> str:
        """Execute complete pipeline asynchronously"""
        analysis_date = analysis_date or date.today()

        self.logger.info(f"Running complete pipeline for {analysis_date}")

        # Stage 1: Patient Profiling
        patient_result = self.profiling_agent.execute(
            self.prescription_data,
            analysis_date=analysis_date
        )

        # Stage 2: External Signals
        external_signals = self.external_agent.execute(target_date=analysis_date)

        # Stage 3: Forecasting
        forecast_config = ForecastingConfig(
            forecast_horizon_days=30,
            use_patient_predictions=True,
            use_external_signals=True
        )

        forecasting_agent = ForecastingAgent(config=forecast_config)
        forecast_result = forecasting_agent.execute(
            patient_profiles=patient_result,
            external_signals=external_signals,
            historical_data=self.prescription_data
        )

        # Stage 4: Optimization
        optimization_config = OptimizationConfig(
            target_service_level=0.95,
            safety_stock_days=7,
            use_eoq=True,
            round_to_case_size=True
        )

        optimization_agent = OptimizationAgent(config=optimization_config)
        optimization_result = optimization_agent.execute(
            forecast=forecast_result,
            inventory_data=self.inventory_data,
            medication_db=self.medication_db
        )

        # Format summary
        critical_orders = optimization_result.get_critical_orders()

        summary = {
            "analysis_date": str(analysis_date),
            "patient_analysis": {
                "total_profiles": patient_result.total_patient_medications,
                "due_soon": patient_result.patients_due_soon
            },
            "external_signals": {
                "flu_level": external_signals.flu_activity.level if external_signals.flu_activity else None,
                "flu_multiplier": external_signals.flu_activity.get_demand_multiplier() if external_signals.flu_activity else 1.0
            },
            "forecast": {
                "period": f"{forecast_result.forecast_start_date} to {forecast_result.forecast_end_date}",
                "total_demand": forecast_result.summary.total_predicted_demand,
                "confidence": forecast_result.summary.average_confidence
            },
            "optimization": {
                "total_recommendations": optimization_result.summary.total_recommendations,
                "critical_orders": optimization_result.summary.critical_orders,
                "high_priority_orders": optimization_result.summary.high_priority_orders,
                "total_order_cost": optimization_result.summary.total_order_cost,
                "current_inventory_value": optimization_result.summary.total_current_value,
                "critical_medications": [
                    {
                        "medication": order.medication,
                        "order_quantity": order.recommended_order_quantity,
                        "order_cost": order.order_cost,
                        "stockout_risk": order.stockout_risk
                    }
                    for order in critical_orders[:5]
                ] if critical_orders else []
            }
        }

        return json.dumps(summary, indent=2)

    def execute(self, analysis_date: Optional[date] = None) -> str:
        """Synchronous execution wrapper"""
        return asyncio.run(self.execute_async(analysis_date))
