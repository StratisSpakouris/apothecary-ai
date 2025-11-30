# Streamlit Dashboard - User Guide

## 🎯 Overview

The **Apothecary-AI Streamlit Dashboard** provides a beautiful web-based interface for pharmacy inventory management. It leverages the AG-UI protocol to provide transparent, interactive analysis with real-time updates and visual insights.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install streamlit plotly
```

### 2. Launch Dashboard

```bash
streamlit run streamlit_app.py
```

The dashboard will open in your browser at `http://localhost:8501`

---

## 🎨 Dashboard Features

### Phase 1 Features (Current)

✅ **Text Input for Queries**
- Natural language query input
- Quick action buttons in sidebar
- Example queries provided

✅ **Real-Time AG-UI Message Display**
- Live status updates as agents work
- Progress indicators
- Results with reasoning chains

✅ **Clickable Suggestion Buttons**
- Interactive follow-up actions
- No need to type - just click
- Contextual suggestions based on results

✅ **Results Display in Cards**
- Beautiful formatted results
- Expandable details sections
- JSON data viewers

✅ **Basic Inventory Charts**
- Inventory value by category (bar chart)
- Patient behavior breakdown (pie chart)
- Forecast metrics display
- Optimization summary tables

✅ **Session State Management**
- Conversation history (last 5 queries)
- Persistent suggestions
- Query replay capability

---

## 📊 Interface Walkthrough

### Main Dashboard

```
┌────────────────────────────────────────────────────────────────┐
│  🧪 Apothecary-AI Dashboard                                    │
│  AI-Powered Pharmacy Inventory Management System               │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  💬 Ask Apothecary-AI                                          │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ What's the inventory of Metformin?                     │   │
│  └────────────────────────────────────────────────────────┘   │
│  [🚀 Submit]                                                   │
│                                                                  │
│  ────────────────────────────────────────────────────────────  │
│                                                                  │
│  🔄 [Orchestrator] Analyzing request...                        │
│  ⚙️  [DataQueryTools] Checking inventory levels for Metformin... │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ ✓ DataQueryTools completed:                            │   │
│  │   Current stock: 2,450 units of Metformin              │   │
│  │   → Total value: $612.50 across 3 lots                │   │
│  │   📊 View Details ▼                                    │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ✅ Query completed successfully                               │
│  ⏱️ Execution time: 0.12s                                      │
│                                                                  │
│  ────────────────────────────────────────────────────────────  │
│                                                                  │
│  📋 Suggested Next Actions                                     │
│  Click a button to execute the suggested action:               │
│                                                                  │
│  ┌──────────────────────┐ ┌──────────────────────┐           │
│  │ Forecast demand for  │ │ See patients taking  │           │
│  │ Metformin            │ │ Metformin            │           │
│  │                      │ │                      │           │
│  │ Predict future...    │ │ View all patients... │           │
│  └──────────────────────┘ └──────────────────────┘           │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

### Sidebar

```
┌─────────────────────────┐
│ 🧪 Apothecary-AI        │
│ AI-Powered Pharmacy...  │
├─────────────────────────┤
│                         │
│ 🎯 Quick Actions        │
│ ┌─────────────────────┐ │
│ │ 📊 Check Inventory  │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ 👥 Patient Analysis │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ 📈 Forecast Demand  │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ 🎯 Complete Analysis│ │
│ └─────────────────────┘ │
│                         │
├─────────────────────────┤
│ 💡 Example Queries      │
│ • What's the inventory  │
│   of Metformin?         │
│ • Analyze patient...    │
│ • Forecast cardio...    │
├─────────────────────────┤
│ ℹ️ System Info          │
│ Version: 1.0.0          │
│ Protocol: A2A + AG-UI   │
│                         │
│ ┌─────────────────────┐ │
│ │ 🗑️ Clear History    │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

---

## 🎬 Usage Examples

### Example 1: Check Medication Inventory

**Step 1**: Type query or click "📊 Check Inventory"

**Step 2**: See real-time status updates:
```
⚙️  [DataQueryTools] Checking inventory levels...
```

**Step 3**: View results with visualization:
```
✓ DataQueryTools completed:
  Current stock: 2,450 units of Metformin
  → Total value: $612.50 across 3 lots

📊 Inventory Value by Category
[Bar chart showing all categories]
```

**Step 4**: Click suggested action:
```
[Forecast demand for Metformin] [See patients taking Metformin]
```

---

### Example 2: Patient Analysis

**Step 1**: Click "👥 Patient Analysis" in sidebar

**Step 2**: Watch pipeline execute:
```
⚙️  [PatientAnalysisAgent] Analyzing patient prescription refill patterns...
```

**Step 3**: View results with visualization:
```
✓ PatientAnalysisAgent completed:
  Analyzed 394 patients: 203 need refills within 7 days
  → Identified 103 high-risk patients who may lapse on medications

📊 Patient Analysis Visualization
├─ Patient Behavior Classification (Pie Chart)
├─ Total Profiles: 394
├─ Due Soon (7 days): 203
└─ High-Risk Patients: 103
```

**Step 4**: Click suggestion to drill down:
```
[Contact high-risk patients] [Forecast demand] [View breakdown]
```

---

### Example 3: Complete Inventory Analysis

**Step 1**: Click "🎯 Complete Analysis"

**Step 2**: Watch 4-stage pipeline:
```
⚙️  [PatientProfilingAgent] Stage 1/4: Analyzing patient prescription patterns...
⚙️  [ExternalSignalsAgent] Stage 2/4: Gathering external health signals...
⚙️  [ForecastingAgent] Stage 3/4: Forecasting 30-day medication demand...
⚙️  [OptimizationAgent] Stage 4/4: Calculating optimal inventory orders...
```

**Step 3**: View comprehensive results:
```
✓ CompleteAnalysisAgent completed:
  Inventory levels are sufficient - no orders needed at this time
  → Current inventory value: $46,127.10. Flu season impact: 1.56x
     demand multiplier applied. Safety stock: 7 days supply.

🎯 Optimization Summary
├─ Order Recommendations: 0
├─ Critical Orders: 0
├─ Total Order Cost: $0.00
└─ Current Inventory: $46,127.10
```

**Step 4**: Review suggested actions:
```
[Generate supply chain risk report]
[Adjust reorder thresholds]
[View detailed category breakdown]
```

---

## 📊 Visualizations

### 1. Inventory Value by Category (Bar Chart)
- Shows total value of each medication category
- Color-coded by value
- Hover for exact amounts
- Auto-loads on dashboard startup

### 2. Patient Behavior Breakdown (Pie Chart)
- Shows distribution of patient behaviors:
  - Highly Regular
  - Regular
  - Irregular
  - New Patient
- Appears after patient analysis query

### 3. Forecast Metrics (Card Layout)
- Total Forecasted Demand
- Medications Forecasted
- Average Confidence
- Flu Season Impact (with delta indicator)

### 4. Optimization Summary (Table + Metrics)
- Current inventory metrics
- Order recommendations count
- Critical medications table (if any)
- Cost breakdowns

### 5. Category Breakdown (Table + Pie Chart)
- Medications in category
- Quantities and values
- Distribution pie chart

---

## 🎯 Quick Actions Explained

### 📊 Check Inventory
**Query**: "Show current inventory status"

**What it does**:
- Displays inventory overview chart
- Shows total value, unique medications, total units
- Provides category breakdown

---

### 👥 Patient Analysis
**Query**: "Analyze patient refill patterns"

**What it does**:
- Analyzes 394 patient-medication combinations
- Identifies patients due for refills
- Flags high-risk patients
- Shows behavior classification

---

### 📈 Forecast Demand
**Query**: "Forecast medication demand for next 30 days"

**What it does**:
- Runs patient profiling
- Gathers external signals (flu, weather)
- Generates 30-day forecast
- Shows confidence levels

---

### 🎯 Complete Analysis
**Query**: "Run complete inventory analysis and generate order recommendations"

**What it does**:
- Executes full 4-stage pipeline
- Provides order recommendations
- Shows critical medications
- Calculates EOQ and safety stock

---

## 🔄 Interactive Features

### Clickable Suggestions
- Automatically generated based on results
- Context-aware (different for each query type)
- Click to execute without typing
- Results appear inline

### Conversation History
- Stores last 5 queries
- Click to expand and review
- Shows timestamp and execution time
- Replay previous queries

### Expandable Details
- "📊 View Details" shows raw JSON
- Charts expand/collapse
- Full data tables available

### Real-Time Updates
- Status messages appear as agents work
- No page refresh needed
- Live progress indication

---

## 🎨 Visual Design

### Color Scheme
- **Primary**: Blue (#1f77b4) - Headers, status boxes
- **Success**: Green (#28a745) - Completed results
- **Warning**: Orange - High-risk indicators
- **Danger**: Red - Critical alerts

### Icons
- 🔄 Starting
- ⚙️  Working
- ✅ Completed
- ❌ Failed
- 📋 Suggestions
- 📊 Charts

### Layout
- **Wide mode**: Maximum screen space
- **Sidebar**: Always accessible quick actions
- **Cards**: Organized result presentation
- **Expandable sections**: Progressive disclosure

---

## ⚡ Performance

| Feature | Performance |
|---------|-------------|
| **Dashboard Load** | < 2s |
| **Simple Query (inventory check)** | ~0.1s |
| **Patient Analysis** | ~5-10s |
| **Demand Forecast** | ~10-15s |
| **Complete Analysis** | ~15-20s |
| **Chart Rendering** | < 0.5s |
| **Suggestion Click** | Immediate (inline) |

---

## 🔧 Customization

### Change Port
```bash
streamlit run streamlit_app.py --server.port 8502
```

### Headless Mode (Server)
```bash
streamlit run streamlit_app.py --server.headless true
```

### Custom Theme
Edit `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

---

## 🐛 Troubleshooting

### Issue: Dashboard won't load
**Solution**: Ensure all dependencies installed
```bash
pip install streamlit plotly pandas
```

### Issue: Data files not found
**Solution**: Verify data files exist:
```bash
ls data/raw/inventory/current_stock.csv
ls data/raw/medications/medication_database.csv
ls data/raw/patients/prescription_history.csv
```

### Issue: AG-UI messages not showing
**Solution**: Check orchestrator initialization:
```python
orchestrator = ApothecaryOrchestrator(enable_agui=True)  # Must be True
```

### Issue: Charts not rendering
**Solution**: Install plotly:
```bash
pip install plotly
```

---

## 🔮 Future Enhancements (Phase 2 & 3)

### Phase 2: Advanced Features
- [ ] Forecast visualization with confidence intervals (line charts)
- [ ] Patient behavior heatmaps
- [ ] Inventory status gauges per medication
- [ ] Flu season impact overlay on forecasts
- [ ] Export results to PDF/Excel

### Phase 3: Production Features
- [ ] Multi-user authentication
- [ ] User roles (admin, pharmacist, viewer)
- [ ] Historical query logging with search
- [ ] Email alerts for critical medications
- [ ] Mobile-responsive design
- [ ] Dark mode
- [ ] Scheduled reports
- [ ] API integration dashboard

---

## 📚 Technical Details

### Architecture
```
User Browser
    ↓
Streamlit Frontend (streamlit_app.py)
    ↓
Session State Management
    ↓
ApothecaryOrchestrator (with AG-UI)
    ↓
A2A Wrapper Agents
    ↓
Deterministic Agents
    ↓
Data Sources
```

### File Structure
```
apothecary-ai/
├── streamlit_app.py                    # Main dashboard
├── src/
│   ├── orchestrator.py                 # A2A + AG-UI orchestrator
│   ├── agui_protocol.py                # AG-UI message protocol
│   └── streamlit_components/
│       ├── __init__.py
│       └── charts.py                    # Visualization components
```

### Session State Variables
- `orchestrator` - ApothecaryOrchestrator instance
- `conversation_history` - List of past queries
- `agui_messages` - Current AG-UI messages
- `current_suggestions` - Active suggestions
- `processing` - Query processing flag

---

## ✅ Summary

The Streamlit Dashboard provides:

✅ **Beautiful UI** - Professional, modern design
✅ **Real-Time Updates** - See agents working live
✅ **Interactive** - Click suggestions, no typing needed
✅ **Visual Insights** - Charts and graphs for data
✅ **User-Friendly** - No technical knowledge required
✅ **AG-UI Integration** - Transparent, explainable AI
✅ **Fast** - Responsive and quick
✅ **Accessible** - Browser-based, any device

Perfect for pharmacy staff who want powerful AI analysis with an easy-to-use interface! 🎉
