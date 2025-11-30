# A2A Orchestrator Quick Reference

## 🎯 What Changed

The system now supports **flexible, modular execution** via **Agent-to-Agent (A2A) protocol** using Google ADK.

### Before A2A:
- ❌ Always ran full pipeline (all 4 stages)
- ❌ No way to query simple data
- ❌ User had to know which script to run

### After A2A:
- ✅ **Intelligent routing** - system decides what to run
- ✅ **Modular execution** - runs only required stages
- ✅ **Natural language** - simple user prompts
- ✅ **Fast queries** - direct data lookup for simple requests

---

## 🏗️ Architecture

```
User Prompt → ApothecaryOrchestrator → [A2A Decision]
                                            ↓
                        ┌───────────────────┼───────────────────┐
                        ↓                   ↓                   ↓
                  Direct Query      Patient Analysis    Forecasting Agent
                  (0.1s)            (5-10s)             (10-15s)
                                                            ↓
                                                    Complete Analysis
                                                    (15-20s)
```

---

## 📊 Use Cases & Examples

### 1️⃣ Simple Data Queries (No Agent - Fast)

**When:** User just wants to lookup existing data
**Speed:** ~0.1s
**Examples:**
```
Show me the prescription history for patient P001
What's the current inventory of Metformin?
List all cardiovascular medications in stock
Tell me about Lisinopril
```

**What runs:** Direct database query (no agents)

---

### 2️⃣ Patient Analysis (PatientAnalysisAgent only)

**When:** User wants to analyze patient refill patterns
**Speed:** ~5-10s
**Examples:**
```
Analyze patient refill patterns
Which patients need refills this week?
Identify high-risk patients
```

**What runs:**
- PatientProfilingAgent (via A2A wrapper)

---

### 3️⃣ Demand Forecasting (Partial Pipeline)

**When:** User wants demand predictions
**Speed:** ~10-15s
**Examples:**
```
Forecast demand for the next 30 days
What's the summer forecast for antihistamines?
How will flu season affect antiviral demand?
```

**What runs:**
1. PatientProfilingAgent
2. ExternalSignalsAgent
3. ForecastingAgent

(Skips optimization - faster!)

---

### 4️⃣ Complete Analysis & Orders (Full Pipeline)

**When:** User wants order recommendations
**Speed:** ~15-20s
**Examples:**
```
Run complete inventory analysis
What medications should I order?
Generate optimal order recommendations
```

**What runs:**
1. PatientProfilingAgent
2. ExternalSignalsAgent
3. ForecastingAgent
4. OptimizationAgent

(Full pipeline)

---

## 🚀 How to Use

### Option 1: Interactive CLI (Recommended)

```bash
python scripts/apothecary_cli.py
```

Then type any prompt:
```
>>> Show me the prescription history for patient P001
>>> Analyze patient refill patterns
>>> Forecast demand for cardiovascular medications
>>> Run complete inventory analysis
```

Commands:
- `/help` - Show help
- `/examples` - Show example prompts
- `/quit` - Exit

---

### Option 2: Single Query

```bash
python scripts/apothecary_cli.py --query "Show me inventory for Metformin"
```

---

### Option 3: Show Examples

```bash
python scripts/apothecary_cli.py --examples
```

---

## 🔧 Technical Details

### Files Created

1. **src/orchestrator.py**
   - `ApothecaryOrchestrator` - Main A2A coordinator
   - `DataQueryTools` - Direct data queries

2. **src/agents/a2a_wrappers.py**
   - `PatientAnalysisA2AAgent` - Wraps PatientProfilingAgent
   - `ForecastingA2AAgent` - Wraps full forecasting pipeline
   - `CompleteAnalysisA2AAgent` - Wraps complete pipeline

3. **scripts/apothecary_cli.py**
   - Interactive CLI interface
   - Single query mode
   - Example prompts display

4. **EXAMPLE_PROMPTS.md**
   - Comprehensive examples
   - Use case explanations
   - Expected outputs

---

## 🎯 Key Benefits

| Feature | Before | After |
|---------|--------|-------|
| **Simple queries** | Run full pipeline (~20s) | Direct lookup (~0.1s) |
| **Flexibility** | Fixed 4-stage pipeline | Modular execution |
| **User interface** | Technical scripts | Natural language |
| **Agent selection** | Manual | Automatic (A2A) |
| **Extensibility** | Hard to add agents | Easy via A2A protocol |

---

## 📖 Example Session

```bash
$ python scripts/apothecary_cli.py

🧪 APOTHECARY-AI - AI-Powered Pharmacy Inventory Management
================================================================================

Interactive Mode - Type your query or /help for assistance

>>> Show me the prescription history for patient P001

Processing...

Response:
{
  "patient_id": "P001",
  "found": true,
  "total_prescriptions": 24,
  "unique_medications": 3,
  "medications": ["Lisinopril", "Metformin", "Atorvastatin"],
  "recent_fills": [...]
}

>>> Analyze patient refill patterns

Processing...

Response:
{
  "analysis_date": "2025-11-30",
  "total_profiles": 394,
  "due_soon_7_days": 203,
  "high_risk_patients": 103,
  "behavior_breakdown": {
    "highly_regular": 86,
    "regular": 113,
    "irregular": 190
  }
}

>>> /quit

Goodbye! 👋
```

---

## 🔄 How It Decides

The orchestrator uses this decision tree:

1. **Check prompt for keywords:**
   - "patient history" / "prescription history" → Direct query
   - "inventory" (without "forecast") → Direct query
   - "tell me about" / "information about" → Direct query
   - "list categories" → Direct query

2. **If not a simple query, route to LLM agent:**
   - "analyze" / "patterns" → PatientAnalysisAgent
   - "forecast" / "predict" / "demand" → ForecastingAgent
   - "order" / "recommend" / "complete" → CompleteAnalysisAgent

3. **LLM agent decides internally:**
   - Which sub-agents to call via A2A
   - What data to return

---

## ⚡ Performance Comparison

| Task | Old Approach | New Approach | Time Saved |
|------|--------------|--------------|------------|
| Check inventory | 20s (full pipeline) | 0.1s (direct query) | **99.5%** |
| Patient analysis | 20s (full pipeline) | 5s (patient agent only) | **75%** |
| Demand forecast | 20s (full pipeline) | 10s (skip optimization) | **50%** |
| Order recommendations | 20s (full pipeline) | 20s (full pipeline) | 0% |

---

## 🧪 Test It Out

Try these prompts in order to see different execution paths:

```bash
python scripts/apothecary_cli.py
```

1. **Fast query:**
   ```
   >>> What's the inventory of Metformin?
   ```
   Watch: Returns in ~0.1s (no agent)

2. **Patient analysis:**
   ```
   >>> Analyze patient refill patterns
   ```
   Watch: Takes ~5s (runs PatientProfilingAgent only)

3. **Forecast:**
   ```
   >>> Forecast demand for cardiovascular medications
   ```
   Watch: Takes ~10s (runs profiling + signals + forecasting)

4. **Complete:**
   ```
   >>> Run complete inventory analysis
   ```
   Watch: Takes ~20s (runs all 4 stages)

---

## 📚 Next Steps

1. **Install dependencies:**
   ```bash
   pip install colorama
   ```

2. **Try the CLI:**
   ```bash
   python scripts/apothecary_cli.py
   ```

3. **Read examples:**
   - See [EXAMPLE_PROMPTS.md](EXAMPLE_PROMPTS.md) for detailed use cases

4. **Experiment:**
   - Try different prompts
   - Observe which agents get called
   - Compare execution times

---

## ✅ Summary

The A2A architecture allows Apothecary-AI to:
- **Understand natural language queries**
- **Route to appropriate agents automatically**
- **Execute only necessary pipeline stages**
- **Return results faster for simple queries**

This makes the system more user-friendly and efficient! 🎉
