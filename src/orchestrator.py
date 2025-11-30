"""
Apothecary-AI A2A Orchestrator

Agent-to-Agent (A2A) protocol-based orchestrator using Google ADK.
Routes user requests to appropriate agents via A2A messaging.
"""

import os
import asyncio
from pathlib import Path
from datetime import date
from typing import Optional, Dict, Any
import pandas as pd
import json

from google.adk import LlmAgent
from google.adk.runners import InMemoryRunner
from dotenv import load_dotenv

from src.utils.logging import setup_logger
from src.agents.a2a_wrappers import (
    PatientAnalysisA2AAgent,
    ForecastingA2AAgent,
    CompleteAnalysisA2AAgent
)

# Load environment variables
load_dotenv()


# ============================================================================
# DATA QUERY TOOLS - For orchestrator to use directly
# ============================================================================

class DataQueryTools:
    """Tools for querying data without running agents"""

    def __init__(self, data_dir: Path = Path("data/raw")):
        self.logger = setup_logger("DataQueryTools")
        self.data_dir = data_dir
        self._load_data()

    def _load_data(self):
        """Load all data files into memory"""
        self.logger.info("Loading data files...")

        self.prescription_data = pd.read_csv(self.data_dir / "patients/prescription_history.csv")
        self.inventory_data = pd.read_csv(self.data_dir / "inventory/current_stock.csv")
        self.medication_db = pd.read_csv(self.data_dir / "medications/medication_database.csv")

        self.logger.info(f"  ✓ Prescriptions: {len(self.prescription_data):,} records")
        self.logger.info(f"  ✓ Inventory: {len(self.inventory_data):,} lot entries")
        self.logger.info(f"  ✓ Medication DB: {len(self.medication_db):,} medications")

    def query_patient_history(self, patient_id: str) -> str:
        """
        Query prescription history for a specific patient.
        Returns JSON string with patient's prescription records.
        """
        self.logger.info(f"Querying history for patient: {patient_id}")

        patient_records = self.prescription_data[
            self.prescription_data['patient_id'] == patient_id
        ].sort_values('fill_date', ascending=False)

        if patient_records.empty:
            return json.dumps({
                "patient_id": patient_id,
                "found": False,
                "message": f"No records found for patient {patient_id}"
            })

        total_prescriptions = len(patient_records)
        unique_medications = patient_records['medication'].nunique()
        date_range = (
            patient_records['fill_date'].min(),
            patient_records['fill_date'].max()
        )

        return json.dumps({
            "patient_id": patient_id,
            "found": True,
            "total_prescriptions": total_prescriptions,
            "unique_medications": unique_medications,
            "date_range": list(date_range),
            "medications": patient_records['medication'].unique().tolist(),
            "recent_fills": patient_records.head(10).to_dict('records')
        }, indent=2)

    def query_inventory(self, medication: Optional[str] = None,
                       category: Optional[str] = None) -> str:
        """
        Query current inventory for specific medication or category.
        Returns JSON string with inventory details.
        """
        if medication:
            self.logger.info(f"Querying inventory for medication: {medication}")

            med_inventory = self.inventory_data[
                self.inventory_data['medication'] == medication
            ]

            if med_inventory.empty:
                return json.dumps({
                    "medication": medication,
                    "found": False,
                    "message": f"No inventory found for {medication}"
                })

            med_info = self.medication_db[
                self.medication_db['medication'] == medication
            ]

            total_quantity = int(med_inventory['quantity'].sum())
            total_value = float((med_inventory['quantity'] * med_inventory['unit_cost']).sum())
            lot_count = len(med_inventory)

            return json.dumps({
                "medication": medication,
                "found": True,
                "category": med_info['category'].iloc[0] if not med_info.empty else "Unknown",
                "total_quantity": total_quantity,
                "total_value": total_value,
                "lot_count": lot_count,
                "lots": med_inventory.to_dict('records')
            }, indent=2)

        elif category:
            self.logger.info(f"Querying inventory for category: {category}")

            category_meds = self.medication_db[
                self.medication_db['category'] == category
            ]['medication'].tolist()

            if not category_meds:
                return json.dumps({
                    "category": category,
                    "found": False,
                    "message": f"No medications found in category {category}"
                })

            category_inventory = self.inventory_data[
                self.inventory_data['medication'].isin(category_meds)
            ]

            inventory_summary = category_inventory.groupby('medication').agg({
                'quantity': 'sum',
                'unit_cost': 'mean'
            }).reset_index()

            inventory_summary['total_value'] = (
                inventory_summary['quantity'] * inventory_summary['unit_cost']
            )

            total_value = float(inventory_summary['total_value'].sum())
            total_quantity = int(inventory_summary['quantity'].sum())

            return json.dumps({
                "category": category,
                "found": True,
                "medication_count": len(inventory_summary),
                "total_quantity": total_quantity,
                "total_value": total_value,
                "medications": inventory_summary.to_dict('records')
            }, indent=2)

        else:
            self.logger.info("Querying all inventory")

            total_value = float((self.inventory_data['quantity'] * self.inventory_data['unit_cost']).sum())
            total_quantity = int(self.inventory_data['quantity'].sum())

            category_summary = self.inventory_data.merge(
                self.medication_db[['medication', 'category']],
                on='medication',
                how='left'
            ).groupby('category').agg({
                'quantity': 'sum',
                'unit_cost': 'mean'
            }).reset_index()

            category_summary['total_value'] = (
                category_summary['quantity'] * category_summary['unit_cost']
            )

            return json.dumps({
                "found": True,
                "total_medications": int(self.inventory_data['medication'].nunique()),
                "total_quantity": total_quantity,
                "total_value": total_value,
                "categories": category_summary.to_dict('records')
            }, indent=2)

    def query_medication_info(self, medication: str) -> str:
        """
        Get detailed information about a medication.
        Returns JSON string with medication details.
        """
        self.logger.info(f"Querying medication info: {medication}")

        med_info = self.medication_db[
            self.medication_db['medication'] == medication
        ]

        if med_info.empty:
            return json.dumps({
                "medication": medication,
                "found": False,
                "message": f"Medication {medication} not found in database"
            })

        prescription_history = self.prescription_data[
            self.prescription_data['medication'] == medication
        ]

        current_inventory = self.inventory_data[
            self.inventory_data['medication'] == medication
        ]

        return json.dumps({
            "medication": medication,
            "found": True,
            "info": med_info.to_dict('records')[0],
            "total_patients": int(prescription_history['patient_id'].nunique()),
            "total_prescriptions": len(prescription_history),
            "current_stock": int(current_inventory['quantity'].sum()) if not current_inventory.empty else 0
        }, indent=2)

    def list_categories(self) -> str:
        """
        List all medication categories in the database.
        Returns JSON string with category list.
        """
        categories = self.medication_db['category'].unique().tolist()
        return json.dumps({
            "categories": categories,
            "total_categories": len(categories)
        }, indent=2)


# ============================================================================
# A2A ORCHESTRATOR - Main agent coordinator
# ============================================================================

class ApothecaryOrchestrator:
    """
    A2A-based orchestrator using Google ADK.
    Routes user requests to appropriate agents via Agent-to-Agent protocol.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.logger = setup_logger("ApothecaryOrchestrator")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment or parameters")

        # Initialize data query tools
        self.data_tools = DataQueryTools()

        # Initialize A2A wrapper agents
        self.logger.info("Initializing A2A sub-agents...")
        self.patient_agent = PatientAnalysisA2AAgent(api_key=self.api_key)
        self.forecasting_agent = ForecastingA2AAgent(api_key=self.api_key)
        self.complete_agent = CompleteAnalysisA2AAgent(api_key=self.api_key)

        # Build orchestrator agent with sub-agents
        self.agent = self._build_orchestrator_agent()
        self.runner = InMemoryRunner(agent=self.agent)

        self.logger.info("A2A Orchestrator initialized with sub-agents")

    def _build_orchestrator_agent(self) -> LlmAgent:
        """
        Build the orchestrator LlmAgent with sub-agents and tools.
        """
        orchestrator_instruction = """You are the Apothecary-AI Orchestrator.

Your role is to understand user requests about pharmacy inventory management and route them to the appropriate agents or tools.

**Available Capabilities:**

1. **Direct Data Queries** (use tools - fast, no agent needed):
   - Query patient prescription history
   - Check medication inventory levels
   - Get medication information
   - List medication categories

2. **Agent-Based Analysis** (delegate to sub-agents via A2A - for complex tasks):
   - PatientAnalysisAgent: Analyze patient refill patterns and predict future refills
   - ForecastingAgent: Forecast medication demand for upcoming period
   - OptimizationAgent: Generate optimal inventory order recommendations
   - CompleteAnalysisAgent: Run full pipeline (profiling → forecasting → optimization)

**Decision Logic:**

- If user asks for simple data lookup (patient history, inventory level) → Use tools directly
- If user asks for analysis, patterns, or predictions → Delegate to appropriate agent
- If user asks for forecasts or demand estimation → Use ForecastingAgent
- If user asks for order recommendations → Use CompleteAnalysisAgent (full pipeline)

**Response Format:**
- Provide clear, concise answers
- Include relevant numbers and statistics
- Explain what analysis was performed
- Suggest next steps if appropriate

Always choose the most efficient path: use tools for simple queries, use agents for complex analysis.
"""

        # Create orchestrator agent with sub-agents
        orchestrator = LlmAgent(
            name="ApothecaryOrchestrator",
            model="gemini-2.0-flash-exp",
            instruction=orchestrator_instruction,
            description="Main orchestrator for Apothecary-AI pharmacy inventory management system",
            tools=[],  # Direct data queries handled via _try_direct_query
            sub_agents=[
                self.patient_agent.agent,
                self.forecasting_agent.agent,
                self.complete_agent.agent
            ]
        )

        return orchestrator

    async def process_request(self, user_prompt: str) -> str:
        """
        Process user request via A2A protocol.

        Args:
            user_prompt: Natural language user request

        Returns:
            Agent response as string
        """
        self.logger.info(f"Processing request: {user_prompt}")

        # First, check if this is a simple data query
        response = await self._try_direct_query(user_prompt)

        if response:
            return response

        # If not a direct query, delegate to orchestrator agent
        self.logger.info("Delegating to orchestrator agent via A2A...")

        try:
            result = await self.runner.run_debug(user_prompt)
            response_text = self._extract_response_text(result)
            return response_text

        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return f"Error processing request: {str(e)}"

    async def _try_direct_query(self, prompt: str) -> Optional[str]:
        """
        Try to handle simple data queries directly without agent.
        Returns None if this requires agent processing.
        """
        prompt_lower = prompt.lower()

        # Patient history queries
        if "patient history" in prompt_lower or "prescription history" in prompt_lower:
            # Extract patient ID
            if "patient" in prompt_lower:
                words = prompt.split()
                for i, word in enumerate(words):
                    if word.lower() == "patient" and i + 1 < len(words):
                        patient_id = words[i + 1].strip('.,!?')
                        result = self.data_tools.query_patient_history(patient_id)
                        return f"Patient History Results:\n{result}"

        # Inventory queries
        if "inventory" in prompt_lower and "forecast" not in prompt_lower:
            # Check for medication name
            for med in self.data_tools.medication_db['medication'].unique():
                if med.lower() in prompt_lower:
                    result = self.data_tools.query_inventory(medication=med)
                    return f"Inventory Results:\n{result}"

            # Check for category
            for cat in self.data_tools.medication_db['category'].unique():
                if cat.lower() in prompt_lower:
                    result = self.data_tools.query_inventory(category=cat)
                    return f"Inventory Results:\n{result}"

        # Medication info queries
        if "tell me about" in prompt_lower or "information about" in prompt_lower:
            for med in self.data_tools.medication_db['medication'].unique():
                if med.lower() in prompt_lower:
                    result = self.data_tools.query_medication_info(med)
                    return f"Medication Information:\n{result}"

        # List categories
        if "list categories" in prompt_lower or "what categories" in prompt_lower:
            result = self.data_tools.list_categories()
            return f"Medication Categories:\n{result}"

        return None

    def _extract_response_text(self, response) -> str:
        """Extract text from ADK response"""
        if hasattr(response, 'text'):
            return response.text
        elif isinstance(response, dict) and 'text' in response:
            return response['text']
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    def run(self, user_prompt: str) -> str:
        """
        Synchronous wrapper for process_request.

        Args:
            user_prompt: Natural language user request

        Returns:
            Agent response as string
        """
        return asyncio.run(self.process_request(user_prompt))
