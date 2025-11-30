# Apothecary-AI Example Prompts

This document demonstrates the capabilities of Apothecary-AI through example user prompts. The system uses **A2A (Agent-to-Agent) protocol** to intelligently route requests to the appropriate agents or data query tools.

---

## 🎯 How It Works

The orchestrator analyzes your natural language request and:
1. **Simple queries** → Uses direct data lookup (fast, no agent needed)
2. **Analysis tasks** → Routes to appropriate agent via A2A protocol
3. **Complex tasks** → Coordinates multiple agents sequentially

---

## 📊 Use Case 1: Simple Data Queries
**Execution:** Direct data lookup (no agents)
**Speed:** Fast (~0.1s)
**When:** User just wants to lookup existing data

### Example Prompts:

```
Show me the prescription history for patient P001
```
**What happens:**
- Direct query to prescription database
- No agent execution
- Returns: Patient's prescription records, refill dates, medications

---

```
What's the current inventory of Metformin?
```
**What happens:**
- Direct query to inventory database
- No agent execution
- Returns: Total quantity, value, lot details, expiration dates

---

```
List all cardiovascular medications in stock
```
**What happens:**
- Filters inventory by category
- No agent execution
- Returns: List of medications, quantities, total value

---

```
Tell me about Lisinopril
```
**What happens:**
- Queries medication database
- No agent execution
- Returns: Category, case size, lead time, current stock, patient count

---

```
List all medication categories
```
**What happens:**
- Queries medication database
- No agent execution
- Returns: All available categories

---

## 👥 Use Case 2: Patient Refill Analysis
**Execution:** PatientAnalysisA2AAgent via A2A protocol
**Speed:** Medium (~5-10s)
**When:** User wants to analyze patient behavior patterns

### Example Prompts:

```
Analyze patient refill patterns for today
```
**What happens:**
- Orchestrator routes to PatientAnalysisAgent via A2A
- Agent analyzes 394 patient-medication combinations
- Calculates refill intervals, consistency scores, risk of lapse
- Returns: Patient profiles, due dates, behavior classification

**Expected Output:**
```json
{
  "analysis_date": "2025-11-30",
  "total_profiles": 394,
  "unique_patients": 100,
  "due_soon_7_days": 203,
  "high_risk_patients": 103,
  "behavior_breakdown": {
    "highly_regular": 86,
    "regular": 113,
    "irregular": 190,
    "new_patient": 5
  }
}
```

---

```
Which patients need refills this week?
```
**What happens:**
- Routes to PatientAnalysisAgent
- Identifies patients due for refills within 7 days
- Returns: 203 patients with predicted refill dates

---

```
Identify high-risk patients for medication lapse
```
**What happens:**
- Routes to PatientAnalysisAgent
- Calculates risk scores based on refill inconsistency
- Returns: 103 high-risk patients (risk ≥ 20%)

---

## 📈 Use Case 3: Demand Forecasting
**Execution:** ForecastingA2AAgent via A2A protocol
**Speed:** Medium (~10-15s)
**When:** User wants to predict future medication demand

### Example Prompts:

```
Forecast medication demand for the next 30 days
```
**What happens:**
- Orchestrator routes to ForecastingAgent via A2A
- Agent coordinates with:
  1. PatientAnalysisAgent (refill predictions)
  2. ExternalSignalsAgent (flu, weather, events)
- Applies demand multipliers based on external signals
- Generates 420 daily forecasts (14 medications × 30 days)

**Expected Output:**
```json
{
  "forecast_period": "2025-11-30 to 2025-12-29",
  "total_medications": 14,
  "total_demand": 13455,
  "average_confidence": 0.71,
  "high_priority_alerts": 0,
  "flu_multiplier": 1.56
}
```

---

```
What's the summer demand forecast for antihistamines?
```
**What happens:**
- Routes to ForecastingAgent with category filter
- Forecasts only antihistamine medications
- Returns: Category-specific demand prediction

**Expected Output:**
```json
{
  "forecast_period": "2025-11-30 to 2025-12-29",
  "category": "antihistamines",
  "medications": 3,
  "total_demand": 1250,
  "average_confidence": 0.68,
  "flu_multiplier": 1.0
}
```

---

```
How will flu season affect antiviral demand?
```
**What happens:**
- Routes to ForecastingAgent
- Fetches flu activity from EODY reports (Level 5/10)
- Applies flu multiplier (1.56x) to antiviral forecasts
- Returns: Demand forecast with flu impact

---

## 🎯 Use Case 4: Complete Analysis & Order Recommendations
**Execution:** CompleteAnalysisA2AAgent via A2A protocol
**Speed:** Slower (~15-20s) - runs full pipeline
**When:** User wants optimal order recommendations

### Example Prompts:

```
Run complete inventory analysis and recommend orders
```
**What happens:**
- Orchestrator routes to CompleteAnalysisAgent via A2A
- Agent runs full pipeline:
  1. **Patient Profiling** - Analyzes refill patterns
  2. **External Signals** - Gathers flu, weather, events
  3. **Forecasting** - Predicts 30-day demand
  4. **Optimization** - Calculates optimal orders using EOQ

**Expected Output:**
```json
{
  "analysis_date": "2025-11-30",
  "patient_analysis": {
    "total_profiles": 394,
    "due_soon": 203
  },
  "external_signals": {
    "flu_level": 5,
    "flu_multiplier": 1.56
  },
  "forecast": {
    "period": "2025-11-30 to 2025-12-29",
    "total_demand": 13455,
    "confidence": 0.71
  },
  "optimization": {
    "total_recommendations": 0,
    "critical_orders": 0,
    "high_priority_orders": 0,
    "total_order_cost": 0.0,
    "current_inventory_value": 46127.10,
    "critical_medications": []
  }
}
```

---

```
What medications should I order immediately?
```
**What happens:**
- Routes to CompleteAnalysisAgent
- Runs full pipeline
- Prioritizes critical orders (< 3 days supply)
- Returns: Critical medications with order quantities

**Example Output (if critical orders exist):**
```json
{
  "critical_medications": [
    {
      "medication": "Oseltamivir",
      "order_quantity": 500,
      "order_cost": 1250.00,
      "stockout_risk": 0.85
    }
  ]
}
```

---

```
Generate optimal order recommendations with EOQ
```
**What happens:**
- Routes to CompleteAnalysisAgent
- Uses Economic Order Quantity (EOQ) formula
- Calculates safety stock (7 days)
- Returns: Optimized orders by priority

---

## 🔄 How Routing Works

### Simple Query Example:
```
User: "What's the inventory of Metformin?"
  ↓
Orchestrator: Detects simple inventory query
  ↓
DataQueryTools: Direct database lookup
  ↓
Response: Inventory details (0.1s)
```

### Analysis Example:
```
User: "Analyze patient refill patterns"
  ↓
Orchestrator: Routes to PatientAnalysisAgent via A2A
  ↓
PatientAnalysisAgent: Executes PatientProfilingAgent
  ↓
Response: Patient analysis results (5s)
```

### Forecast Example:
```
User: "Forecast demand for cardiovascular medications"
  ↓
Orchestrator: Routes to ForecastingAgent via A2A
  ↓
ForecastingAgent:
  - Calls PatientAnalysisAgent (A2A)
  - Calls ExternalSignalsAgent
  - Runs forecasting algorithm
  - Filters by category
  ↓
Response: Category-specific forecast (10s)
```

### Complete Pipeline Example:
```
User: "Run complete inventory analysis"
  ↓
Orchestrator: Routes to CompleteAnalysisAgent via A2A
  ↓
CompleteAnalysisAgent:
  - Stage 1: PatientProfilingAgent
  - Stage 2: ExternalSignalsAgent
  - Stage 3: ForecastingAgent
  - Stage 4: OptimizationAgent
  ↓
Response: Full analysis with order recommendations (20s)
```

---

## 🚀 Usage

### Interactive CLI:
```bash
python scripts/apothecary_cli.py
```

Then type any of the example prompts above.

### Single Query:
```bash
python scripts/apothecary_cli.py --query "Show me inventory for Metformin"
```

### Show Examples:
```bash
python scripts/apothecary_cli.py --examples
```

---

## 🎯 Summary: When to Use What

| Use Case | Example Prompt | Agent Used | Execution Time |
|----------|---------------|------------|----------------|
| **Patient History** | "Show history for patient P001" | None (direct query) | ~0.1s |
| **Inventory Check** | "What's the inventory of Metformin?" | None (direct query) | ~0.1s |
| **Medication Info** | "Tell me about Lisinopril" | None (direct query) | ~0.1s |
| **Patient Analysis** | "Analyze refill patterns" | PatientAnalysisAgent | ~5-10s |
| **Demand Forecast** | "Forecast demand for 30 days" | ForecastingAgent | ~10-15s |
| **Category Forecast** | "Summer forecast for antihistamines" | ForecastingAgent | ~10-15s |
| **Order Recommendations** | "What should I order?" | CompleteAnalysisAgent | ~15-20s |

---

## ✅ Key Benefits of A2A Architecture

1. **Intelligent Routing** - Orchestrator automatically selects the right tool/agent
2. **Modular Execution** - Only runs necessary agents for the task
3. **Natural Language** - Users don't need to know which agent to call
4. **Efficient** - Simple queries bypass agents entirely
5. **Scalable** - Easy to add new agents via A2A protocol

---

## 🔧 Technical Details

### A2A Protocol Flow:
```
User Prompt
  ↓
ApothecaryOrchestrator (LlmAgent)
  ↓
[A2A Protocol]
  ↓
├─→ DataQueryTools (direct)
├─→ PatientAnalysisA2AAgent (LlmAgent wrapper)
├─→ ForecastingA2AAgent (LlmAgent wrapper)
└─→ CompleteAnalysisA2AAgent (LlmAgent wrapper)
      ↓
  [Underlying Agents]
      ↓
  PatientProfilingAgent (deterministic)
  ExternalSignalsAgent (deterministic)
  ForecastingAgent (deterministic)
  OptimizationAgent (deterministic)
```

### Why A2A?
- **Standardized Communication** - Agents communicate via consistent protocol
- **Discoverability** - Orchestrator knows available sub-agents
- **Composability** - Agents can call other agents
- **Extensibility** - Easy to add new agents
- **Google ADK Integration** - Native support in ADK framework

---

## 📚 Next Steps

Try these prompts in the CLI and observe:
1. Which agent gets called
2. How long execution takes
3. What data is returned

This will help you understand when the system runs the full pipeline vs. simple queries!
