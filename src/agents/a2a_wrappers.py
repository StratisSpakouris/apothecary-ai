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

# Apply nest_asyncio to allow nested event loops (required for Streamlit)
import nest_asyncio
nest_asyncio.apply()

from google.adk.agents import LlmAgent
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

        # Format results as natural language
        high_risk = sum(1 for p in result.profiles if p.risk_of_lapse >= 0.2)
        behavior = {
            "highly_regular": sum(1 for p in result.profiles if p.behavior_type.value == "highly_regular"),
            "regular": sum(1 for p in result.profiles if p.behavior_type.value == "regular"),
            "irregular": sum(1 for p in result.profiles if p.behavior_type.value == "irregular"),
            "new_patient": sum(1 for p in result.profiles if p.behavior_type.value == "new_patient")
        }

        response = f"## 👥 Patient Refill Pattern Analysis\n\n"
        response += f"**Analysis Date:** {analysis_date}\n\n"

        # Overview
        response += f"### 📊 Overview\n"
        response += f"- **Total patient-medication profiles:** {result.total_patient_medications}\n"
        response += f"- **Unique patients:** {result.total_patients}\n"
        response += f"- **Patients due for refill soon (7 days):** {result.patients_due_soon}\n"
        response += f"- **High-risk patients (≥20% lapse risk):** {high_risk}\n\n"

        # Behavior Breakdown
        response += f"### 🎯 Behavior Classification\n\n"
        total = sum(behavior.values())
        for behavior_type, count in behavior.items():
            percentage = (count / total * 100) if total > 0 else 0
            label = behavior_type.replace('_', ' ').title()
            response += f"**{label}:** {count} patients ({percentage:.1f}%)\n"
            if behavior_type == "highly_regular":
                response += f"  - Very consistent refill patterns, low risk\n"
            elif behavior_type == "regular":
                response += f"  - Consistent patterns with minor variations\n"
            elif behavior_type == "irregular":
                response += f"  - Inconsistent patterns, higher monitoring needed\n"
            elif behavior_type == "new_patient":
                response += f"  - Insufficient history for pattern analysis\n"
            response += "\n"

        # Insights
        response += f"### 💡 Key Insights\n\n"
        if result.patients_due_soon > 0:
            response += f"- ⚠️ **{result.patients_due_soon} patients** need refills within the next 7 days\n"

        if high_risk > 0:
            response += f"- 🚨 **{high_risk} patients** at high risk of medication lapse (≥20% risk)\n"

        irregular_pct = (behavior['irregular'] / total * 100) if total > 0 else 0
        if irregular_pct > 30:
            response += f"- 📈 **{irregular_pct:.1f}%** of patients have irregular refill patterns\n"

        if not result.patients_due_soon and not high_risk:
            response += f"- ✅ No immediate concerns - patients are on track with refills\n"

        return response

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
            historical_data=self.prescription_data,
            start_date=target_date
        )

        # Filter by category if requested
        if category_filter:
            # Get medications in category
            medication_db = pd.read_csv("data/raw/medications/medication_database.csv")
            category_meds = medication_db[
                medication_db['category'] == category_filter
            ]['medication'].tolist()

            # Filter forecasts (daily forecasts)
            filtered_forecasts = [
                f for f in forecast_result.medication_forecasts
                if f.medication in category_meds
            ]

            # Aggregate by medication (sum daily forecasts)
            medication_totals = {}
            medication_confidence = {}
            for forecast in filtered_forecasts:
                if forecast.medication not in medication_totals:
                    medication_totals[forecast.medication] = 0
                    medication_confidence[forecast.medication] = []
                medication_totals[forecast.medication] += forecast.predicted_demand
                medication_confidence[forecast.medication].append(forecast.confidence)

            total_demand = sum(medication_totals.values())
            avg_confidence = sum(
                sum(conf_list) / len(conf_list) for conf_list in medication_confidence.values()
            ) / len(medication_confidence) if medication_confidence else 0

            # Format as natural language
            response = f"## 📈 Medication Demand Forecast - {category_filter.title()}\n\n"
            response += f"**Forecast Period:** {forecast_result.forecast_start_date} to {forecast_result.forecast_end_date}\n\n"

            response += f"### 📊 Category Overview\n"
            response += f"- **Category:** {category_filter.title()}\n"
            response += f"- **Medications forecasted:** {len(medication_totals)}\n"
            response += f"- **Total predicted demand:** {total_demand:,.0f} units\n"
            response += f"- **Average confidence:** {avg_confidence:.1%}\n\n"

            # External factors
            if external_signals.flu_activity:
                flu_multiplier = external_signals.flu_activity.get_demand_multiplier()
                response += f"### 🌡️ External Factors\n"
                response += f"- **Flu activity level:** {external_signals.flu_activity.level}/10 ({external_signals.flu_activity.trend})\n"
                response += f"- **Demand multiplier:** {flu_multiplier:.2f}x\n\n"

            # Top medications in category
            if medication_totals:
                response += f"### 💊 Top Medications by Demand\n\n"
                sorted_meds = sorted(medication_totals.items(), key=lambda x: x[1], reverse=True)
                for i, (med, total_demand_med) in enumerate(sorted_meds[:5], 1):
                    avg_conf = sum(medication_confidence[med]) / len(medication_confidence[med])
                    response += f"**{i}. {med}**\n"
                    response += f"   - Predicted demand: {total_demand_med:,.0f} units\n"
                    response += f"   - Daily average: {total_demand_med / forecast_days:.1f} units/day\n"
                    response += f"   - Confidence: {avg_conf:.1%}\n\n"

            return response
        else:
            # Aggregate by medication (sum daily forecasts)
            medication_totals = {}
            medication_confidence = {}
            for forecast in forecast_result.medication_forecasts:
                if forecast.medication not in medication_totals:
                    medication_totals[forecast.medication] = 0
                    medication_confidence[forecast.medication] = []
                medication_totals[forecast.medication] += forecast.predicted_demand
                medication_confidence[forecast.medication].append(forecast.confidence)

            # Format as natural language
            response = f"## 📈 Medication Demand Forecast\n\n"
            response += f"**Forecast Period:** {forecast_result.forecast_start_date} to {forecast_result.forecast_end_date}\n\n"

            response += f"### 📊 Forecast Overview\n"
            response += f"- **Medications forecasted:** {forecast_result.summary.total_medications}\n"
            response += f"- **Total predicted demand:** {forecast_result.summary.total_predicted_demand:,.0f} units\n"
            response += f"- **Average confidence:** {forecast_result.summary.average_confidence:.1%}\n"
            response += f"- **High-priority alerts:** {forecast_result.summary.high_priority_alerts}\n\n"

            # External factors
            if external_signals.flu_activity:
                flu_multiplier = external_signals.flu_activity.get_demand_multiplier()
                response += f"### 🌡️ External Factors\n"
                response += f"- **Flu activity level:** {external_signals.flu_activity.level}/10 ({external_signals.flu_activity.trend})\n"
                response += f"- **Demand multiplier:** {flu_multiplier:.2f}x\n\n"

            # Top medications by demand
            if medication_totals:
                response += f"### 💊 Top Medications by Demand\n\n"
                sorted_meds = sorted(medication_totals.items(), key=lambda x: x[1], reverse=True)
                for i, (med, total_demand_med) in enumerate(sorted_meds[:10], 1):
                    avg_conf = sum(medication_confidence[med]) / len(medication_confidence[med])
                    response += f"**{i}. {med}**\n"
                    response += f"   - Predicted demand: {total_demand_med:,.0f} units\n"
                    response += f"   - Daily average: {total_demand_med / forecast_days:.1f} units/day\n"
                    response += f"   - Confidence: {avg_conf:.1%}\n\n"

            # Insights
            response += f"### 💡 Key Insights\n\n"
            if forecast_result.summary.high_priority_alerts > 0:
                response += f"- ⚠️ **{forecast_result.summary.high_priority_alerts} high-priority alerts** detected - potential demand spikes expected\n"

            if external_signals.flu_activity and external_signals.flu_activity.level >= 6:
                response += f"- 🚨 **High flu activity** detected - increased demand expected for antivirals and respiratory medications\n"

            if forecast_result.summary.high_priority_alerts == 0:
                response += f"- ✅ No significant demand spikes expected - steady demand forecasted\n"

            return response

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
            historical_data=self.prescription_data,
            start_date=target_date
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

        # Format summary as natural language
        critical_orders = optimization_result.get_critical_orders()

        response = f"## 📊 Complete Inventory Analysis\n\n"
        response += f"**Analysis Date:** {analysis_date}\n\n"

        # Patient Analysis
        response += f"### 👥 Patient Analysis\n"
        response += f"- Total patient-medication profiles: {patient_result.total_patient_medications}\n"
        response += f"- Patients due for refill soon: {patient_result.patients_due_soon}\n\n"

        # External Signals
        if external_signals.flu_activity:
            response += f"### 🌡️ External Signals\n"
            response += f"- Flu activity level: {external_signals.flu_activity.level}/10 ({external_signals.flu_activity.trend})\n"
            response += f"- Demand multiplier: {external_signals.flu_activity.get_demand_multiplier():.2f}x\n\n"

        # Forecast
        response += f"### 📈 Demand Forecast\n"
        response += f"- Forecast period: {forecast_result.forecast_start_date} to {forecast_result.forecast_end_date}\n"
        response += f"- Total predicted demand: {forecast_result.summary.total_predicted_demand:,} units\n"
        response += f"- Average confidence: {forecast_result.summary.average_confidence:.1%}\n"
        response += f"- Medications forecasted: {forecast_result.summary.total_medications}\n\n"

        # Optimization
        response += f"### 🎯 Optimization Results\n"
        response += f"- Current inventory value: ${optimization_result.summary.total_current_value:,.2f}\n"
        response += f"- Total order recommendations: {optimization_result.summary.total_recommendations}\n"
        response += f"- Critical orders (immediate): {optimization_result.summary.critical_orders}\n"
        response += f"- High priority orders: {optimization_result.summary.high_priority_orders}\n"
        response += f"- Total recommended order cost: ${optimization_result.summary.total_order_cost:,.2f}\n\n"

        # Critical medications
        if critical_orders:
            response += f"### 🚨 Critical Orders (Immediate Action Required)\n\n"
            for i, order in enumerate(critical_orders[:5], 1):
                response += f"**{i}. {order.medication}**\n"
                response += f"   - Recommended order: {order.recommended_order_quantity} units\n"
                response += f"   - Order cost: ${order.order_cost:,.2f}\n"
                response += f"   - Stockout risk: {order.stockout_risk:.1%}\n\n"
        else:
            response += f"✅ **No critical orders needed.** Current inventory levels are sufficient.\n\n"

        return response

    def execute(self, analysis_date: Optional[date] = None) -> str:
        """Synchronous execution wrapper"""
        return asyncio.run(self.execute_async(analysis_date))
