"""
AG-UI Protocol Implementation

Agent-User Interface (AG-UI) protocol for transparent, step-by-step interactions.
Provides status updates, result messages, and suggested next actions.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import json


# ============================================================================
# AG-UI MESSAGE TYPES
# ============================================================================

class MessageType(Enum):
    """AG-UI message types"""
    STATUS = "status"           # Agent is working
    RESULT = "result"           # Agent completed
    SUGGESTION = "suggestion"   # Suggested next action
    ERROR = "error"             # Error occurred
    FINAL = "final"             # Final response with all results


class AgentStatus(Enum):
    """Agent execution status"""
    STARTING = "starting"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# AG-UI MESSAGE STRUCTURES
# ============================================================================

@dataclass
class StatusUpdate:
    """Status update message - shows agent progress"""
    type: str = "status"
    agent: str = ""
    status: AgentStatus = AgentStatus.WORKING
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "agent": self.agent,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ResultMessage:
    """Result message - shows agent findings"""
    type: str = "result"
    agent: str = ""
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "agent": self.agent,
            "summary": self.summary,
            "details": self.details,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class SuggestedAction:
    """A suggested next action for the user"""
    id: str
    label: str
    description: str
    agent_target: Optional[str] = None  # Which agent handles this action
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "agent_target": self.agent_target,
            "context": self.context
        }


@dataclass
class SuggestionsMessage:
    """Suggested actions message"""
    type: str = "suggestions"
    actions: List[SuggestedAction] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "actions": [a.to_dict() for a in self.actions],
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class FinalResponse:
    """Final response with all results and suggestions"""
    type: str = "final"
    query: str = ""
    summary: str = ""
    results: List[ResultMessage] = field(default_factory=list)
    suggestions: Optional[SuggestionsMessage] = None
    execution_time_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "query": self.query,
            "summary": self.summary,
            "results": [r.to_dict() for r in self.results],
            "suggestions": self.suggestions.to_dict() if self.suggestions else None,
            "execution_time_seconds": self.execution_time_seconds,
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ============================================================================
# AG-UI MESSAGE HANDLER
# ============================================================================

class AGUIMessageHandler:
    """
    Handles AG-UI protocol message emission and rendering.
    Collects status updates, results, and generates suggestions.
    """

    def __init__(self, enable_streaming: bool = True):
        """
        Initialize AG-UI message handler.

        Args:
            enable_streaming: If True, emit messages in real-time
        """
        self.enable_streaming = enable_streaming
        self.messages: List[Any] = []
        self.status_updates: List[StatusUpdate] = []
        self.results: List[ResultMessage] = []
        self.callbacks: List[Callable] = []

    def register_callback(self, callback: Callable[[Any], None]):
        """Register a callback to receive messages in real-time"""
        self.callbacks.append(callback)

    def emit(self, message: Any):
        """Emit a message to all registered callbacks"""
        self.messages.append(message)

        # Store by type
        if isinstance(message, StatusUpdate):
            self.status_updates.append(message)
        elif isinstance(message, ResultMessage):
            self.results.append(message)

        # Call callbacks if streaming enabled
        if self.enable_streaming:
            for callback in self.callbacks:
                callback(message)

    def status(self, agent: str, message: str, status: AgentStatus = AgentStatus.WORKING):
        """Emit a status update"""
        update = StatusUpdate(
            agent=agent,
            status=status,
            message=message
        )
        self.emit(update)

    def result(self, agent: str, summary: str, details: Dict[str, Any] = None, reasoning: str = None):
        """Emit a result message"""
        result = ResultMessage(
            agent=agent,
            summary=summary,
            details=details or {},
            reasoning=reasoning
        )
        self.emit(result)

    def suggestions(self, actions: List[SuggestedAction]):
        """Emit suggested actions"""
        suggestions = SuggestionsMessage(actions=actions)
        self.emit(suggestions)
        return suggestions

    def finalize(self, query: str, summary: str, suggestions: Optional[SuggestionsMessage] = None,
                execution_time: float = 0.0) -> FinalResponse:
        """Create final response with all collected data"""
        final = FinalResponse(
            query=query,
            summary=summary,
            results=self.results,
            suggestions=suggestions,
            execution_time_seconds=execution_time
        )
        self.emit(final)
        return final

    def clear(self):
        """Clear all stored messages"""
        self.messages.clear()
        self.status_updates.clear()
        self.results.clear()


# ============================================================================
# SUGGESTION GENERATOR
# ============================================================================

class SuggestionGenerator:
    """
    Generates contextual follow-up suggestions based on results.
    """

    @staticmethod
    def generate_for_patient_analysis(result: Dict[str, Any]) -> List[SuggestedAction]:
        """Generate suggestions after patient analysis"""
        suggestions = []

        # If high-risk patients found
        if result.get("high_risk_patients", 0) > 0:
            suggestions.append(SuggestedAction(
                id="contact_high_risk",
                label="Contact high-risk patients for refill reminders",
                description=f"Send automated refill reminders to {result['high_risk_patients']} high-risk patients to prevent medication lapses",
                agent_target="PatientAnalysisAgent",
                context={"filter": "high_risk"}
            ))

        # If many patients due soon
        if result.get("due_soon_7_days", 0) > 50:
            suggestions.append(SuggestedAction(
                id="forecast_demand",
                label="Forecast demand for upcoming week",
                description=f"Run demand forecast for the {result['due_soon_7_days']} patients due for refills this week",
                agent_target="ForecastingAgent",
                context={"horizon_days": 7}
            ))

        # Always offer detailed breakdown
        suggestions.append(SuggestedAction(
            id="patient_breakdown",
            label="View detailed patient behavior breakdown",
            description="See full list of patients by behavior classification (regular, irregular, etc.)",
            agent_target="PatientAnalysisAgent",
            context={"detail_level": "full"}
        ))

        return suggestions[:3]  # Max 3 suggestions

    @staticmethod
    def generate_for_forecast(result: Dict[str, Any]) -> List[SuggestedAction]:
        """Generate suggestions after forecasting"""
        suggestions = []

        # If high demand forecasted
        if result.get("total_demand", 0) > 10000:
            suggestions.append(SuggestedAction(
                id="optimize_orders",
                label="Generate optimal order recommendations",
                description="Run full inventory optimization to determine what to order based on this forecast",
                agent_target="CompleteAnalysisAgent",
                context={}
            ))

        # If specific category was forecasted
        if result.get("category"):
            suggestions.append(SuggestedAction(
                id="compare_categories",
                label="Compare with other medication categories",
                description="See how this category's demand compares to others",
                agent_target="ForecastingAgent",
                context={"comparison": True}
            ))

        # If flu multiplier is high
        if result.get("flu_multiplier", 1.0) > 1.3:
            suggestions.append(SuggestedAction(
                id="flu_impact_report",
                label="Generate flu season impact report",
                description="Detailed analysis of how flu season affects different medication categories",
                agent_target="ExternalSignalsAgent",
                context={"focus": "flu_impact"}
            ))

        return suggestions[:3]

    @staticmethod
    def generate_for_complete_analysis(result: Dict[str, Any]) -> List[SuggestedAction]:
        """Generate suggestions after complete analysis"""
        suggestions = []

        opt = result.get("optimization", {})

        # If critical orders exist
        if opt.get("critical_orders", 0) > 0:
            suggestions.append(SuggestedAction(
                id="supply_chain_risk",
                label="Generate supply chain risk report",
                description=f"Analyze risks and alternatives for {opt['critical_orders']} critical medications",
                agent_target="CompleteAnalysisAgent",
                context={"focus": "supply_chain_risk"}
            ))

        # If no orders needed
        if opt.get("total_recommendations", 0) == 0:
            suggestions.append(SuggestedAction(
                id="adjust_thresholds",
                label="Adjust reorder thresholds",
                description="Review and optimize safety stock levels and reorder points",
                agent_target="OptimizationAgent",
                context={"action": "threshold_adjustment"}
            ))

        # Always offer detailed view
        suggestions.append(SuggestedAction(
            id="detailed_breakdown",
            label="View detailed category breakdown",
            description="See inventory status and recommendations by medication category",
            agent_target="CompleteAnalysisAgent",
            context={"detail_level": "category_breakdown"}
        ))

        return suggestions[:3]

    @staticmethod
    def generate_for_inventory_query(medication: str = None, category: str = None) -> List[SuggestedAction]:
        """Generate suggestions after inventory query"""
        suggestions = []

        if medication:
            suggestions.extend([
                SuggestedAction(
                    id="forecast_medication",
                    label=f"Forecast demand for {medication}",
                    description="Predict future demand and identify when to reorder",
                    agent_target="ForecastingAgent",
                    context={"medication": medication}
                ),
                SuggestedAction(
                    id="patient_history",
                    label=f"See patients taking {medication}",
                    description="View all patients prescribed this medication and their refill patterns",
                    agent_target="PatientAnalysisAgent",
                    context={"medication": medication}
                )
            ])

        if category:
            suggestions.append(SuggestedAction(
                id="forecast_category",
                label=f"Forecast demand for {category} category",
                description="Predict demand for all medications in this category",
                agent_target="ForecastingAgent",
                context={"category": category}
            ))

        return suggestions[:3]


# ============================================================================
# FOLLOW-UP ACTION ROUTER
# ============================================================================

class FollowUpActionRouter:
    """
    Routes user-selected follow-up actions to appropriate agents.
    """

    def __init__(self, orchestrator):
        """
        Initialize router with orchestrator reference.

        Args:
            orchestrator: ApothecaryOrchestrator instance
        """
        self.orchestrator = orchestrator

    async def route_action(self, action: SuggestedAction) -> str:
        """
        Route a selected action to the appropriate agent.

        Args:
            action: The selected action

        Returns:
            Response from the agent
        """
        action_id = action.id

        # Map action IDs to prompts
        action_prompts = {
            "contact_high_risk": "Show me the list of high-risk patients who need refill reminders",
            "forecast_demand": "Forecast medication demand for the next 7 days",
            "patient_breakdown": "Show detailed patient behavior breakdown by classification",
            "optimize_orders": "Run complete inventory analysis and generate order recommendations",
            "compare_categories": "Compare demand across all medication categories",
            "flu_impact_report": "Generate detailed flu season impact report for all medication categories",
            "supply_chain_risk": "Analyze supply chain risks for critical medications",
            "adjust_thresholds": "Show current safety stock levels and reorder thresholds for all medications",
            "detailed_breakdown": "Show detailed inventory breakdown by medication category",
            "forecast_medication": f"Forecast demand for {action.context.get('medication', '')}",
            "forecast_category": f"Forecast demand for {action.context.get('category', '')} category",
            "patient_history": f"Show patients taking {action.context.get('medication', '')}"
        }

        prompt = action_prompts.get(action_id, action.description)

        # Process via orchestrator
        return await self.orchestrator.process_request(prompt)
