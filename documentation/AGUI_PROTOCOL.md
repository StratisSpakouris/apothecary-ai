# AG-UI Protocol Integration

## 🎯 Overview

The **AG-UI (Agent-User Interface) protocol** provides a transparent, step-by-step interaction experience that shows exactly what each agent is doing and why. Instead of seeing just final results, users get real-time status updates, reasoning chains, and contextual follow-up suggestions.

---

## 🏗️ Architecture

```
User Query
    ↓
Orchestrator (analyzes intent)
    ↓
┌───────────────────────────────────┐
│ AG-UI Protocol Layer              │
│                                   │
│ • Status Updates (real-time)     │
│ • Result Messages (with reasoning)│
│ • Suggested Actions (contextual)  │
└───────────────────────────────────┘
    ↓
Agent Execution
    ↓
Interactive Suggestions
    ↓
Follow-Up Actions
```

---

## 📊 AG-UI Message Types

### 1. Status Updates

**Purpose**: Show which agent is working in real-time

**Structure**:
```python
{
  "type": "status",
  "agent": "PatientProfilingAgent",
  "status": "working",  # starting, working, completed, failed
  "message": "Analyzing patient prescription refill patterns...",
  "timestamp": "2025-11-30T14:30:00"
}
```

**Example Output**:
```
⚙️  [PatientProfilingAgent] Analyzing patient prescription refill patterns...
⚙️  [ExternalSignalsAgent] Gathering external health signals (flu, weather, events)...
⚙️  [ForecastingAgent] Generating 30-day demand forecast with confidence intervals...
```

---

### 2. Result Messages

**Purpose**: Show what each agent found with reasoning

**Structure**:
```python
{
  "type": "result",
  "agent": "ForecastingAgent",
  "summary": "Forecasted 13,455 units demand across 14 medications over 30 days",
  "details": { ... },
  "reasoning": "Forecast confidence: 71%. Flu season active: applying 1.56x demand multiplier to respiratory medications.",
  "timestamp": "2025-11-30T14:30:15"
}
```

**Example Output**:
```
✓ ForecastingAgent completed:
  Forecasted 13,455 units demand across 14 medications over 30 days
  → Forecast confidence: 71%. Flu season active: applying 1.56x demand multiplier to respiratory medications.
```

---

### 3. Suggested Actions

**Purpose**: Provide 2-3 contextual follow-up options

**Structure**:
```python
{
  "type": "suggestions",
  "actions": [
    {
      "id": "optimize_orders",
      "label": "Generate optimal order recommendations",
      "description": "Run full inventory optimization to determine what to order based on this forecast",
      "agent_target": "CompleteAnalysisAgent",
      "context": {}
    }
  ],
  "timestamp": "2025-11-30T14:30:20"
}
```

**Example Output**:
```
📋 Suggested Next Actions:
  [1] Generate optimal order recommendations
      Run full inventory optimization to determine what to order based on this forecast
  [2] Compare with other medication categories
      See how this category's demand compares to others
  [3] Generate flu season impact report
      Detailed analysis of how flu season affects different medication categories

Select an action (1-3) or press Enter to skip:
>>> 1
```

---

## 🔄 Complete Interaction Flow

### Example 1: Simple Inventory Query

**User**: `What's the current inventory of Metformin?`

**AG-UI Flow**:
```
🔄 [Orchestrator] Analyzing request: 'What's the current inventory of Metformin?...'
⚙️  [DataQueryTools] Checking inventory levels for Metformin...

✓ DataQueryTools completed:
  Current stock: 2,450 units of Metformin
  → Total value: $612.50 across 3 lots

================================================================================
✓ Query completed successfully
================================================================================

Execution time: 0.12s

📋 Suggested Next Actions:
  [1] Forecast demand for Metformin
      Predict future demand and identify when to reorder
  [2] See patients taking Metformin
      View all patients prescribed this medication and their refill patterns
```

---

### Example 2: Demand Forecasting

**User**: `Forecast demand for cardiovascular medications`

**AG-UI Flow**:
```
🔄 [Orchestrator] Analyzing request: 'Forecast demand for cardiovascular medications...'
⚙️  [Orchestrator] Routing to appropriate agent via A2A protocol...
⚙️  [PatientProfilingAgent] Analyzing patient refill patterns to predict demand...
⚙️  [ExternalSignalsAgent] Gathering external health signals (flu activity, weather data, events)...
⚙️  [ForecastingAgent] Generating 30-day demand forecast with confidence intervals...

✓ ForecastingAgent completed:
  Forecasted 4,230 units demand across 5 medications over 30 days
  → Forecast confidence: 68%. Flu season impact: 1.56x multiplier applied.

================================================================================
✓ Demand forecast complete: 4,230 units predicted over 30 days
================================================================================

Execution time: 10.5s

📋 Suggested Next Actions:
  [1] Generate optimal order recommendations
      Run full inventory optimization to determine what to order based on this forecast
  [2] Compare with other medication categories
      See how this category's demand compares to others
  [3] Generate flu season impact report
      Detailed analysis of how flu season affects different medication categories

Select an action (1-3) or press Enter to skip:
>>> 1

✅ Executing: Generate optimal order recommendations

⚙️  [PatientProfilingAgent] Stage 1/4: Analyzing patient prescription refill patterns...
⚙️  [ExternalSignalsAgent] Stage 2/4: Gathering external health signals (flu, weather, supply chain)...
⚙️  [ForecastingAgent] Stage 3/4: Forecasting 30-day medication demand...
⚙️  [OptimizationAgent] Stage 4/4: Calculating optimal inventory orders using Economic Order Quantity (EOQ)...

✓ CompleteAnalysisAgent completed:
  Inventory levels are sufficient - no orders needed at this time
  → Current inventory value: $46,127.10. Flu season impact: 1.56x demand multiplier applied. Safety stock: 7 days supply.

================================================================================
✓ Inventory analysis complete: Stock levels sufficient
================================================================================

Execution time: 18.3s
```

---

### Example 3: Complete Analysis

**User**: `Run complete inventory analysis`

**AG-UI Flow**:
```
🔄 [Orchestrator] Analyzing request: 'Run complete inventory analysis...'
⚙️  [Orchestrator] Routing to appropriate agent via A2A protocol...
⚙️  [PatientProfilingAgent] Stage 1/4: Analyzing patient prescription refill patterns...
⚙️  [ExternalSignalsAgent] Stage 2/4: Gathering external health signals (flu, weather, supply chain)...
⚙️  [ForecastingAgent] Stage 3/4: Forecasting 30-day medication demand...
⚙️  [OptimizationAgent] Stage 4/4: Calculating optimal inventory orders using Economic Order Quantity (EOQ)...

✓ CompleteAnalysisAgent completed:
  ⚠️ 2 CRITICAL medications need immediate ordering (< 3 days supply remaining)
  → Current inventory value: $46,127.10. Flu season impact: 1.56x demand multiplier applied. Safety stock: 7 days supply.

================================================================================
✓ ⚠️ URGENT: 2 medications critically low
================================================================================

Execution time: 19.7s

📋 Suggested Next Actions:
  [1] Generate supply chain risk report
      Analyze risks and alternatives for 2 critical medications
  [2] Adjust reorder thresholds
      Review and optimize safety stock levels and reorder points
  [3] View detailed category breakdown
      See inventory status and recommendations by medication category

Select an action (1-3) or press Enter to skip:
>>>
```

---

## 🎨 Visual Indicators

| Icon | Meaning | Status |
|------|---------|--------|
| 🔄 | Starting | Agent initializing |
| ⚙️  | Working | Agent processing |
| ✅ | Completed | Agent finished successfully |
| ❌ | Failed | Error occurred |
| 📋 | Suggestions | Follow-up actions available |
| → | Reasoning | Why/how agent decided |
| ⚠️ | Warning | Urgent attention needed |

---

## 🧠 Contextual Suggestion Generation

Suggestions are dynamically generated based on query type and results:

### Patient Analysis Suggestions

**Context**: After analyzing patient refill patterns

**Suggestions**:
1. **If high-risk patients found** → "Contact high-risk patients for refill reminders"
2. **If many patients due soon** → "Forecast demand for upcoming week"
3. **Always** → "View detailed patient behavior breakdown"

---

### Forecasting Suggestions

**Context**: After generating demand forecast

**Suggestions**:
1. **If high demand forecasted** → "Generate optimal order recommendations"
2. **If specific category** → "Compare with other medication categories"
3. **If flu multiplier high** → "Generate flu season impact report"

---

### Complete Analysis Suggestions

**Context**: After full pipeline with optimization

**Suggestions**:
1. **If critical orders exist** → "Generate supply chain risk report"
2. **If no orders needed** → "Adjust reorder thresholds"
3. **Always** → "View detailed category breakdown"

---

### Inventory Query Suggestions

**Context**: After checking inventory

**Suggestions**:
1. **For specific medication** → "Forecast demand for [medication]"
2. **For specific medication** → "See patients taking [medication]"
3. **For category** → "Forecast demand for [category] category"

---

## 🔧 Technical Implementation

### 1. Message Handler

```python
from src.agui_protocol import AGUIMessageHandler

# Initialize
agui = AGUIMessageHandler(enable_streaming=True)

# Emit status
agui.status(
    agent="PatientProfilingAgent",
    message="Analyzing patient prescription refill patterns...",
    status=AgentStatus.WORKING
)

# Emit result
agui.result(
    agent="PatientProfilingAgent",
    summary="Analyzed 394 patients: 203 need refills within 7 days",
    details={"total_profiles": 394, "due_soon": 203},
    reasoning="Identified 103 high-risk patients who may lapse on medications"
)

# Generate suggestions
suggestions = agui.suggestions([
    SuggestedAction(
        id="forecast_demand",
        label="Forecast demand for upcoming week",
        description="Run demand forecast for the 203 patients due for refills",
        agent_target="ForecastingAgent"
    )
])

# Finalize
final = agui.finalize(
    query=user_prompt,
    summary="Analysis complete",
    suggestions=suggestions,
    execution_time=10.5
)
```

---

### 2. Follow-Up Action Routing

```python
from src.agui_protocol import FollowUpActionRouter

# Initialize router
router = FollowUpActionRouter(orchestrator)

# Route selected action
selected_action = suggestions.actions[0]
result = await router.route_action(selected_action)
```

---

### 3. CLI Rendering

```python
# Register real-time callback
orchestrator.agui.register_callback(render_agui_message)

# Process request
response = orchestrator.run(user_prompt)

# Render response
suggestions = render_agui_response(response)

# Handle selection
if suggestions:
    follow_up = handle_suggestion_selection(orchestrator, suggestions)
    if follow_up:
        render_agui_response(follow_up)
```

---

## 🚀 Usage

### Enable AG-UI (Default)

```bash
python scripts/apothecary_cli.py
```

AG-UI is enabled by default and provides the transparent interaction experience.

---

### Disable AG-UI (Legacy Mode)

```python
orchestrator = ApothecaryOrchestrator(enable_agui=False)
```

Returns plain text responses without AG-UI protocol.

---

## ⚡ Benefits

| Feature | Without AG-UI | With AG-UI |
|---------|--------------|------------|
| **Transparency** | Black box | See each agent working |
| **Reasoning** | Just results | Understand why |
| **Interactivity** | One-shot queries | Follow-up suggestions |
| **User Experience** | Technical output | Guided conversation |
| **Trust** | Uncertain | Transparent process |
| **Learning Curve** | Need to know agents | Suggested next steps |

---

## 📚 Examples by Use Case

### Use Case 1: Pharmacy Manager Checking Stock

**Query**: "What's the inventory of Lisinopril?"

**AG-UI Shows**:
- ✅ Fast lookup (0.1s)
- Current stock: 3,200 units
- Suggestions: Forecast demand, See patients

**Benefit**: Manager immediately sees stock AND gets prompted to check if they need to reorder

---

### Use Case 2: Pharmacist Planning for Flu Season

**Query**: "How will flu season affect demand?"

**AG-UI Shows**:
- ⚙️  Checking flu activity (EODY reports)
- ⚙️  Analyzing historical patterns
- ⚙️  Forecasting with 1.56x multiplier
- ✅ Antiviral demand up 56%
- Suggestions: Generate orders, Adjust thresholds

**Benefit**: Transparent reasoning chain shows HOW the system calculated flu impact

---

### Use Case 3: Owner Making Purchase Decisions

**Query**: "What should I order this week?"

**AG-UI Shows**:
- ⚙️  Stage 1/4: Patient analysis
- ⚙️  Stage 2/4: External signals
- ⚙️  Stage 3/4: Forecasting
- ⚙️  Stage 4/4: Optimization
- ✅ 2 critical medications (< 3 days supply)
- Suggestions: Supply chain risk, Adjust thresholds

**Benefit**: Owner sees complete analysis and understands urgency

---

## 🎯 Key Principles

### 1. Transparency
Every agent operation is visible. Users see exactly what's happening and when.

### 2. Reasoning
Results include WHY, not just WHAT. E.g., "Flu season active: applying 1.56x multiplier"

### 3. Contextual Suggestions
Follow-ups are tailored to the query and results, not generic.

### 4. Interactive Flow
Users can drill down into areas of interest without new queries.

### 5. Non-Intrusive
Suggestions are optional. Users can ignore them and continue.

---

## 🔮 Future Enhancements

1. **Progress Indicators**: Show percentage complete for long operations
2. **Agent Collaboration Visualization**: Show when agents call each other
3. **Confidence Scores**: Visual indicators for prediction confidence
4. **Historical Comparison**: "This is 15% higher than last month"
5. **Multi-Path Suggestions**: Branch into multiple follow-up areas

---

## ✅ Summary

AG-UI protocol transforms Apothecary-AI from a black box into a **transparent, interactive assistant** that:
- Shows its work in real-time
- Explains its reasoning
- Suggests relevant next steps
- Handles follow-up actions seamlessly

This creates a **conversational, guided experience** rather than isolated queries.
