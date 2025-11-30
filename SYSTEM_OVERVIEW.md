# Apothecary-AI System Overview

**AI-Powered Pharmacy Inventory Management System**

---

## 🎯 System Purpose

Apothecary-AI is an intelligent system that analyzes patient prescription patterns, monitors external health signals (flu activity, weather, events), forecasts medication demand, and generates optimal inventory orders for pharmacies.

---

## 🏗️ Architecture

### Multi-Agent Pipeline

```
Patient Data → [1] Patient Profiling → Patient Profiles
                                              ↓
EODY Reports → [2] Report Analysis   → Flu Data ────┐
Weather API  → [3] External Signals  → Signals      │
Events/News  →                                      ↓
                                          [4] Forecasting → Demand Forecasts
                                                                  ↓
Inventory DB ────────────────────────────────────────→ [5] Optimization
                                                                  ↓
                                                      Order Recommendations
```

### A2A Protocol Architecture

The system uses **Agent-to-Agent (A2A) protocol** via Google ADK for intelligent request routing:

```
User Query (Natural Language)
        ↓
ApothecaryOrchestrator (LlmAgent)
        ↓
[A2A Protocol Decision]
        ↓
    ┌───┴───┬─────────────┬──────────────┐
    ↓       ↓             ↓              ↓
Direct   Patient    Forecasting   Complete
Query    Analysis   Agent         Analysis
Tools    Agent      (A2A)         Agent
         (A2A)                    (A2A)
```

**Benefits:**
- Natural language interface - users don't specify which agent to use
- Intelligent routing - simple queries bypass agents (fast)
- Modular execution - only runs necessary pipeline stages
- Scalable - easy to add new agents

---

## 🤖 Agents

### Deterministic Agents (Statistical/ML)

#### 1. **PatientProfilingAgent**
- **Purpose**: Analyzes prescription refill patterns
- **Input**: Historical prescription data
- **Processing**:
  - Calculates refill intervals and consistency
  - Classifies behavior (highly_regular, regular, irregular, new_patient)
  - Predicts next refill dates with 95% confidence intervals
  - Identifies patients at risk of medication lapse
- **Output**: Patient profiles with refill predictions

**Key Metrics**:
- Refill interval standard deviation
- Consistency score (0-1)
- Risk of lapse score (0-1)
- Days until expected refill

---

#### 2. **ExternalSignalsAgent**
- **Purpose**: Gathers external factors affecting demand
- **Input**: Date to analyze
- **Processing**:
  - Fetches flu activity from EODY reports or simulation
  - Gets weather data from OpenWeather API
  - Identifies holidays and local events
  - Tracks known drug shortages
  - Calculates demand multipliers per category
- **Output**: External signals with multipliers

**Data Sources**:
- EODY (Greek flu surveillance)
- OpenWeather API
- Holidays library (8 European countries)
- Supply chain alerts

**Multipliers**:
- Flu activity: 1.0x - 2.25x (based on ILI levels)
- Weather: 1.0x - 1.5x (cold snaps increase demand)
- Events: 1.2x for early refills before holidays

---

#### 3. **ForecastingAgent**
- **Purpose**: Predicts medication demand
- **Input**: Patient profiles + external signals + historical data
- **Processing**:
  - Aggregates patient refill predictions by medication/date
  - Applies external signal multipliers
  - Supports Prophet time series forecasting (optional)
  - Generates 30-day daily forecasts per medication
  - Calculates confidence intervals (95%)
  - Detects demand spikes and anomalies
- **Output**: Daily forecasts with alerts

**Features**:
- Patient-based forecasting (from actual refill predictions)
- External signal integration (flu, weather, events)
- Category-level aggregations
- Spike detection (>1.5x baseline)
- Confidence scoring

---

#### 4. **OptimizationAgent**
- **Purpose**: Calculates optimal inventory orders
- **Input**: Forecasts + current inventory + cost parameters
- **Processing**:
  - Calculates safety stock (7 days default)
  - Determines reorder points
  - Uses Economic Order Quantity (EOQ) formula
  - Rounds to case sizes
  - Prioritizes orders (critical, high, medium, low)
  - Assesses stockout and overstock risks
- **Output**: Order recommendations with quantities and costs

**Optimization Algorithms**:
- EOQ: `sqrt((2 * D * S) / H)` where:
  - D = annual demand
  - S = order cost
  - H = holding cost per unit
- Safety Stock: `daily_demand × safety_days`
- Reorder Point: `lead_time_demand + safety_stock`

**Priority Levels**:
- **Critical**: < 3 days supply remaining
- **High**: < 7 days supply remaining
- **Medium**: At reorder point
- **Low**: Routine replenishment

---

### LLM-Powered Agents (Google ADK + Gemini)

#### 5. **DocumentParserAgent**
- **Purpose**: Extracts text from PDF documents
- **Method**: Multi-method (PyPDF2 → pdfplumber fallback)
- **Input**: PDF file path
- **Output**: Extracted text with metadata

---

#### 6. **ReportAnalystAgent**
- **Purpose**: Analyzes Greek EODY flu reports
- **Framework**: Google ADK (Agent Development Kit)
- **Model**: Gemini 2.5 Flash
- **Input**: Extracted Greek text
- **Processing**:
  - Understands Greek medical terminology
  - Extracts structured flu data
  - Outputs English summary
  - Provides confidence scores
- **Output**: FluDataExtraction with:
  - Flu level (1-10 scale)
  - Trend (increasing, stable, decreasing)
  - ILI rate per 100k
  - Dominant strain
  - Positivity rate
  - Alerts

---

## 📊 Data Schemas (Pydantic)

### Patient Profiling
- `PatientProfile`: Individual patient-medication behavior
- `RefillPattern`: Statistical refill metrics
- `RefillPrediction`: Next refill forecast with confidence
- `PatientProfilingResult`: Complete analysis output

### External Signals
- `FluActivity`: Flu surveillance data with multipliers
- `WeatherData`: Temperature, precipitation, conditions
- `DrugShortage`: Known supply chain issues
- `LocalEvent`: Holidays, flu season, tourist season
- `ExternalSignals`: Complete environmental context

### Forecasting
- `MedicationForecast`: Daily demand prediction per medication
- `CategoryForecast`: Aggregated by category
- `ForecastSummary`: High-level metrics
- `ForecastingResult`: Complete 30-day forecast

### Optimization
- `MedicationInventory`: Current stock status
- `OrderRecommendation`: Optimal order with priority
- `OptimizationSummary`: Financial and risk metrics
- `OptimizationResult`: Complete order recommendations

---

## 🧪 Test Results (Latest Run)

**Test Date**: 2025-11-30 13:01:42

### Stage 1: Patient Profiling
```
✓ Profiles: 394 patient-medication combinations
✓ Due soon: 203 patients (within 7 days)
✓ High-risk: 103 patients (lapse risk ≥20%)
✓ Behavior:
  - Irregular: 190
  - Regular: 113
  - Highly Regular: 86
```

### Stage 2: External Signals
```
✓ Flu Activity: Level 5/10 (rapid_increase)
✓ Demand Multiplier: 1.56x for antivirals
✓ Weather: 63°F, few clouds
✓ Supply Chain: 2 shortages detected
✓ Events: 1 upcoming (Flu Season Peak)
```

### Stage 3: Demand Forecasting
```
✓ Forecast Period: 2025-11-30 to 2025-12-29 (30 days)
✓ Medications: 14
✓ Total Demand: 13,455 units
✓ Daily Forecasts: 420 (14 meds × 30 days)
✓ Confidence: 71% average
✓ Alerts: 0 high-priority
```

### Stage 4: Inventory Optimization
```
✓ Current Inventory Value: $46,127.10
✓ Order Recommendations: 0 (well-stocked)
✓ Critical Orders: 0
✓ Monthly Carrying Cost: $768.78
✓ Medications at Risk: 0
✓ Average Stockout Risk: 0.0%
```

**Interpretation**: Current inventory levels are sufficient for forecasted demand. No urgent orders needed. This indicates well-managed inventory.

---

## 📈 Key Performance Metrics

### Accuracy
- **Patient Prediction Confidence**: 85% (for regular patients)
- **Forecast Confidence**: 71% average
- **Service Level Target**: 95% (probability of not stocking out)

### Financial
- **Current Inventory**: $46,127 value
- **Monthly Carrying Cost**: $768.78 (20% annual rate)
- **Average Order Cost**: Variable (EOQ-optimized)

### Risk Management
- **Safety Stock**: 7 days supply
- **Reorder Point**: Lead time + safety stock
- **Stockout Risk**: Real-time monitoring
- **Overstock Risk**: Prevents excess inventory

---

## 🔧 Configuration

### Forecasting Config
```python
ForecastingConfig(
    forecast_horizon_days=30,
    confidence_level=0.95,
    use_prophet=False,  # Can enable with more historical data
    use_patient_predictions=True,
    use_external_signals=True,
    spike_threshold=1.5
)
```

### Optimization Config
```python
OptimizationConfig(
    target_service_level=0.95,
    safety_stock_days=7,
    carrying_cost_rate=0.20,  # 20% annual
    order_fixed_cost=50.0,
    use_eoq=True,
    round_to_case_size=True
)
```

---

## 💾 Data Requirements

### Required Data Files
1. **prescription_history.csv**
   - Columns: patient_id, medication, fill_date, quantity, days_supply
   - Purpose: Patient behavior analysis

2. **current_stock.csv**
   - Columns: medication, lot_number, quantity, unit_cost, expiration_date
   - Purpose: Inventory optimization

3. **medication_database.csv**
   - Columns: medication, category, case_size, shelf_life_months, lead_time_days
   - Purpose: Product information

### Optional Data
4. **EODY Reports (PDFs)**
   - Greek flu surveillance reports
   - Processed with Gemini for flu data extraction

---

## 🚀 Usage

### Interactive CLI (A2A Protocol) ⭐ **Recommended**
```bash
# Start interactive mode
python scripts/apothecary_cli.py

# Examples in interactive mode:
>>> Show me the prescription history for patient P001
>>> What's the current inventory of Metformin?
>>> Analyze patient refill patterns
>>> Forecast demand for cardiovascular medications for next 30 days
>>> Run complete inventory analysis and recommend orders
```

### Single Query Mode
```bash
# Run a single query and exit
python scripts/apothecary_cli.py --query "Show me inventory for Metformin"

# Show example prompts
python scripts/apothecary_cli.py --examples
```

### Run Complete Pipeline (Direct)
```bash
# Run all 4 stages sequentially
python scripts/test_complete_pipeline.py
```

### Process EODY Reports
```bash
# Place PDFs in data/eody_reports/uploads/
python scripts/process_eody_reports.py
```

**See [EXAMPLE_PROMPTS.md](EXAMPLE_PROMPTS.md) for detailed usage examples and use cases.**

---

## 🌍 Supported Regions

- **Primary**: Greece (Athens)
- **Extended**: Germany, France, Italy, Spain, Portugal, Netherlands, Belgium, Austria
- **Flu Data**: EODY (Greece), simulation for others
- **Weather**: OpenWeather API (global)
- **Holidays**: Country-specific calendars

---

## 🔮 Future Enhancements

1. **Streamlit Dashboard**
   - Interactive visualizations
   - Real-time monitoring
   - Order management interface

2. **Automated Scheduling**
   - Daily pipeline execution
   - Email alerts for critical orders
   - Slack/Teams integration

3. **Advanced Forecasting**
   - Prophet with more historical data
   - Seasonal decomposition
   - Trend analysis

4. **Database Integration**
   - PostgreSQL for historical data
   - Time-series database for metrics
   - Audit trail for decisions

5. **Multi-Pharmacy Support**
   - Chain-wide inventory optimization
   - Transfer recommendations
   - Centralized procurement

---

## 📚 Dependencies

### Core
- **Python**: 3.12+
- **Pandas**: 2.1.0 (data processing)
- **NumPy**: 1.26.0 (numerical computation)
- **Pydantic**: 2.5.0 (data validation)

### Forecasting
- **Prophet**: 1.1.5 (time series forecasting)
- **scikit-learn**: 1.3.0 (ML utilities)

### LLM & ADK
- **google-adk**: Latest (Agent Development Kit)
- **google-genai**: 1.0.0 (Gemini API)
- **google-cloud-aiplatform**: 1.73.0

### APIs & Services
- **requests**: 2.31.0 (HTTP)
- **python-dotenv**: 1.0.0 (environment)
- **holidays**: 0.35 (calendar data)

### PDF Processing
- **pypdf2**: 3.0.1 (PDF text extraction)
- **pdfplumber**: 0.11.0 (fallback PDF parser)

### Utilities
- **loguru**: 0.7.2 (logging)
- **python-dateutil**: 2.8.2 (date handling)

---

## 📄 License & Credits

**Framework**: Google Agent Development Kit (ADK)
**LLM**: Google Gemini 2.5 Flash
**Forecasting**: Facebook Prophet

---

## 🎯 Success Metrics

✅ **Complete end-to-end pipeline functional**
✅ **All 6 agents implemented and tested**
✅ **Processes 3,646 prescription records**
✅ **Generates 420 daily forecasts (14 meds × 30 days)**
✅ **Manages $46K inventory value**
✅ **71% average forecast confidence**
✅ **Zero stockouts predicted with current inventory**

**System Status**: Production-ready for Greek pharmacies 🇬🇷
