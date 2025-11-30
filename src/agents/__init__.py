"""
Apothecary-AI Agent Module

This module contains all agents used in the Apothecary-AI system.

Agent Types:
- Deterministic Agents: Simple Python classes (no LLM, no framework)
- LLM-Powered Agents: Use ADKAgent (Google ADK + Gemini)
"""

# ADK base class for LLM agents
from src.agents.adk_base_agent import ADKAgent

# Deterministic agents (statistical/rule-based, no framework)
from src.agents.patient_profiling import PatientProfilingAgent
from src.agents.external_signals import ExternalSignalsAgent
from src.agents.document_parser import DocumentParserAgent
from src.agents.forecasting import ForecastingAgent
from src.agents.optimization import OptimizationAgent

# LLM-powered agents (use ADK + Gemini)
from src.agents.report_analyst import ReportAnalystAgent

# A2A wrapper agents (for orchestrator)
from src.agents.a2a_wrappers import (
    PatientAnalysisA2AAgent,
    ForecastingA2AAgent,
    CompleteAnalysisA2AAgent
)


__all__ = [
    # ADK base class
    "ADKAgent",

    # Deterministic agents
    "PatientProfilingAgent",
    "ExternalSignalsAgent",
    "DocumentParserAgent",
    "ForecastingAgent",
    "OptimizationAgent",

    # LLM-powered agents
    "ReportAnalystAgent",

    # A2A wrapper agents
    "PatientAnalysisA2AAgent",
    "ForecastingA2AAgent",
    "CompleteAnalysisA2AAgent",
]
