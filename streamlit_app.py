"""
Apothecary-AI Streamlit Dashboard

Web-based interface for pharmacy inventory management with AG-UI protocol integration.
"""

import streamlit as st
import sys
from pathlib import Path
import asyncio
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator import ApothecaryOrchestrator
from src.agui_protocol import (
    StatusUpdate,
    ResultMessage,
    SuggestionsMessage,
    FinalResponse,
    AgentStatus
)
from src.streamlit_components.charts import (
    render_inventory_chart,
    render_inventory_overview_with_chart,
    render_forecast_chart,
    render_patient_analysis_chart,
    render_optimization_summary,
    render_category_breakdown
)

# Page config
st.set_page_config(
    page_title="Apothecary-AI",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
        background-color: #f0f8ff;
        color: #1a1a1a;
    }
    .result-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #28a745;
        background-color: #f0fff4;
        color: #1a1a1a;
    }
    .suggestion-button {
        margin: 0.25rem;
    }
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Make info/success/warning/error text more visible */
    .stAlert > div {
        color: #1a1a1a !important;
    }
    .stAlert p, .stAlert div, .stAlert span {
        color: #1a1a1a !important;
    }
    .stInfo, .stSuccess, .stWarning, .stError {
        color: #1a1a1a !important;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
def init_session_state():
    """Initialize Streamlit session state"""
    if 'orchestrator' not in st.session_state:
        st.session_state.orchestrator = None

    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []

    if 'agui_messages' not in st.session_state:
        st.session_state.agui_messages = []

    if 'current_suggestions' not in st.session_state:
        st.session_state.current_suggestions = None

    if 'processing' not in st.session_state:
        st.session_state.processing = False


def initialize_orchestrator():
    """Initialize the Apothecary orchestrator"""
    if st.session_state.orchestrator is None:
        with st.spinner("Initializing Apothecary-AI system..."):
            try:
                # Check if data files exist
                data_files = [
                    Path("data/raw/patients/prescription_history.csv"),
                    Path("data/raw/inventory/current_stock.csv"),
                    Path("data/raw/medications/medication_database.csv")
                ]

                missing_files = [f for f in data_files if not f.exists()]

                if missing_files:
                    st.error("❌ Missing required data files:")
                    for f in missing_files:
                        st.error(f"   • {f}")
                    st.info("💡 Please ensure data files are in the correct location")
                    st.stop()

                # Check for API key
                import os
                if not os.getenv("GOOGLE_API_KEY"):
                    st.warning("⚠️ GOOGLE_API_KEY not found in environment")
                    st.info("💡 Create a `.env` file with: GOOGLE_API_KEY=your_key_here")
                    st.info("💡 Or the system will use simulation mode for EODY reports")

                # Initialize orchestrator
                orchestrator = ApothecaryOrchestrator(enable_agui=True)

                # Register callback to collect AG-UI messages
                def collect_message(message):
                    st.session_state.agui_messages.append(message)

                orchestrator.agui.register_callback(collect_message)
                st.session_state.orchestrator = orchestrator

            except Exception as e:
                import traceback
                st.error(f"❌ Failed to initialize system: {str(e)}")
                with st.expander("🔍 View Error Details"):
                    st.code(traceback.format_exc())
                st.stop()


def render_status_update(status: StatusUpdate):
    """Render a status update message"""
    status_icons = {
        AgentStatus.STARTING: "🔄",
        AgentStatus.WORKING: "⚙️",
        AgentStatus.COMPLETED: "✅",
        AgentStatus.FAILED: "❌"
    }

    icon = status_icons.get(status.status, "•")

    st.markdown(f"""
    <div class="status-box">
        {icon} <strong>[{status.agent}]</strong> {status.message}
    </div>
    """, unsafe_allow_html=True)


def render_result_message(result: ResultMessage):
    """Render a result message"""
    # Check if this is a formatted response (markdown)
    if result.details and "formatted_response" in result.details:
        # Render formatted markdown response
        st.markdown(result.details["formatted_response"])
    else:
        # Regular result box
        st.markdown(f"""
        <div class="result-box">
            <strong>✓ {result.agent} completed:</strong><br>
            {result.summary}
            {f'<br><em>→ {result.reasoning}</em>' if result.reasoning else ''}
        </div>
        """, unsafe_allow_html=True)

        # Show details in expander (skip formatted_response key)
        if result.details:
            details_to_show = {k: v for k, v in result.details.items() if k != "formatted_response"}
            if details_to_show:
                with st.expander("📊 View Details"):
                    st.json(details_to_show)


def render_suggestions(suggestions: SuggestionsMessage):
    """Render suggested actions as clickable buttons"""
    st.markdown("### 📋 Suggested Next Actions")
    st.markdown("Click a button to execute the suggested action:")

    cols = st.columns(len(suggestions.actions))

    for i, action in enumerate(suggestions.actions):
        with cols[i]:
            if st.button(
                action.label,
                key=f"suggestion_{action.id}_{datetime.now().timestamp()}",
                use_container_width=True,
                type="secondary"
            ):
                # Execute the selected action
                st.session_state.selected_action = action
                st.rerun()

            st.caption(action.description)


def render_final_response(response: FinalResponse):
    """Render the final response"""
    # Show all results
    for result in response.results:
        render_result_message(result)

        # Add visualizations based on result data
        if result.details:
            details = result.details

            # Patient analysis visualization
            if 'total_profiles' in details and 'behavior_breakdown' in details:
                with st.expander("📊 Patient Analysis Visualization", expanded=True):
                    render_patient_analysis_chart(details)

            # Forecast visualization
            elif 'total_demand' in details and 'total_medications' in details:
                with st.expander("📈 Forecast Visualization", expanded=True):
                    render_forecast_chart(details)

            # Optimization visualization
            elif 'optimization' in details:
                with st.expander("🎯 Optimization Summary", expanded=True):
                    render_optimization_summary(details)

            # Category breakdown
            elif 'category' in details and 'medications' in details:
                with st.expander("📦 Category Breakdown", expanded=True):
                    render_category_breakdown(details)

    # Summary (skip generic messages)
    generic_summaries = ["Query completed successfully", "Analysis completed successfully"]
    if response.summary and response.summary not in generic_summaries:
        st.success(f"✅ {response.summary}")

    # Execution time
    st.caption(f"⏱️ Execution time: {response.execution_time_seconds:.2f}s")

    # Suggestions
    if response.suggestions:
        st.markdown("---")
        render_suggestions(response.suggestions)
        st.session_state.current_suggestions = response.suggestions


def render_sidebar():
    """Render the sidebar"""
    with st.sidebar:
        st.markdown("## 🧪 Apothecary-AI")
        st.markdown("AI-Powered Pharmacy Inventory Management")
        st.markdown("---")

        # Quick actions
        st.markdown("### 🎯 Quick Actions")

        if st.button("📊 Check Inventory", use_container_width=True):
            st.session_state.quick_query = "Show current inventory status"

        if st.button("👥 Patient Analysis", use_container_width=True):
            st.session_state.quick_query = "Analyze patient refill patterns"

        if st.button("📈 Forecast Demand", use_container_width=True):
            st.session_state.quick_query = "Forecast medication demand for next 30 days"

        if st.button("🎯 Complete Analysis", use_container_width=True):
            st.session_state.quick_query = "Run complete inventory analysis and generate order recommendations"

        st.markdown("---")

        # Example queries
        st.markdown("### 💡 Example Queries")
        st.markdown("""
        - What's the inventory of Metformin?
        - Analyze patient refill patterns
        - Forecast cardiovascular medication demand
        - Run complete inventory analysis
        - Which patients need refills this week?
        """)

        st.markdown("---")

        # System info
        st.markdown("### ℹ️ System Info")
        st.caption(f"Version: 1.0.0")
        st.caption(f"Protocol: A2A + AG-UI")

        # Clear history
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.conversation_history = []
            st.session_state.agui_messages = []
            st.session_state.current_suggestions = None
            st.rerun()


def render_conversation_history():
    """Render conversation history"""
    if st.session_state.conversation_history:
        st.markdown("### 📜 Conversation History")

        for i, conv in enumerate(reversed(st.session_state.conversation_history[-5:])):
            is_latest = (i == 0)
            with st.expander(f"🔍 {conv['query'][:50]}... ({conv['timestamp'][:19]})", expanded=is_latest):
                st.markdown(f"**Query:** {conv['query']}")

                # Render AG-UI messages
                if 'messages' in conv and conv['messages']:
                    st.markdown("---")
                    for msg in conv['messages']:
                        if isinstance(msg, StatusUpdate):
                            render_status_update(msg)

                # Render response (flattened, no nested expanders)
                if 'response' in conv:
                    st.markdown("---")
                    if isinstance(conv['response'], FinalResponse):
                        response = conv['response']

                        # Show all results inline (no expanders)
                        for result in response.results:
                            # Check if this is a formatted response (markdown)
                            if result.details and "formatted_response" in result.details:
                                # Render formatted markdown response
                                st.markdown(result.details["formatted_response"])
                            else:
                                # Regular result box
                                st.markdown(f"""
                                <div class="result-box">
                                    <strong>✓ {result.agent} completed:</strong><br>
                                    {result.summary}
                                    {f'<br><em>→ {result.reasoning}</em>' if result.reasoning else ''}
                                </div>
                                """, unsafe_allow_html=True)

                                # Show details as JSON inline (skip formatted_response key)
                                if result.details:
                                    details_to_show = {k: v for k, v in result.details.items() if k != "formatted_response"}
                                    if details_to_show:
                                        st.json(details_to_show)

                        # Summary (skip generic messages)
                        generic_summaries = ["Query completed successfully", "Analysis completed successfully"]
                        if response.summary and response.summary not in generic_summaries:
                            st.success(f"✅ {response.summary}")

                        # Execution time
                        st.caption(f"⏱️ Execution time: {response.execution_time_seconds:.2f}s")

                        # Suggestions (if any)
                        if response.suggestions:
                            st.markdown("---")
                            render_suggestions(response.suggestions)
                    else:
                        st.write(conv['response'])


def main():
    """Main application"""
    init_session_state()

    # Header
    st.markdown('<div class="main-header">🧪 Apothecary-AI Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Pharmacy Inventory Management System</div>', unsafe_allow_html=True)

    # Sidebar
    render_sidebar()

    # Initialize orchestrator
    initialize_orchestrator()

    # Handle selected action from suggestions FIRST (before showing input)
    if 'selected_action' in st.session_state:
        action = st.session_state.selected_action
        del st.session_state.selected_action

        # Clear previous AG-UI messages
        st.session_state.agui_messages = []

        try:
            with st.spinner(f"🔄 Executing: {action.label}..."):
                # Route the action
                if st.session_state.orchestrator.action_router:
                    result = asyncio.run(
                        st.session_state.orchestrator.action_router.route_action(action)
                    )

                    # Add to conversation history
                    st.session_state.conversation_history.append({
                        "query": f"[Suggested Action] {action.label}",
                        "timestamp": datetime.now().isoformat(),
                        "messages": st.session_state.agui_messages.copy(),
                        "response": result
                    })

        except Exception as e:
            import traceback
            st.error(f"❌ Error executing action: {str(e)}")
            with st.expander("🔍 View Error Details"):
                st.code(traceback.format_exc())

    # Handle quick query from sidebar
    if 'quick_query' in st.session_state:
        default_query = st.session_state.quick_query
        del st.session_state.quick_query
        # Process quick query immediately
        st.session_state.agui_messages = []

        try:
            # Special handling for inventory status query
            if "inventory status" in default_query.lower():
                with st.spinner(f"🔄 Loading inventory..."):
                    # Just render the chart directly, no need to process through orchestrator
                    st.markdown("---")
                    render_inventory_overview_with_chart()
            else:
                with st.spinner(f"🔄 Processing query: {default_query[:50]}..."):
                    response = st.session_state.orchestrator.run(default_query)

                    # Add to conversation history
                    st.session_state.conversation_history.append({
                        "query": default_query,
                        "timestamp": datetime.now().isoformat(),
                        "messages": st.session_state.agui_messages.copy(),
                        "response": response
                    })

        except Exception as e:
            import traceback
            st.error(f"❌ Error occurred: {str(e)}")
            with st.expander("🔍 View Full Error Details"):
                st.code(traceback.format_exc())

    # Main query input
    st.markdown("### 💬 Ask Apothecary-AI")

    # Text input for user query
    query = st.text_input(
        "Enter your query:",
        placeholder="e.g., What's the current inventory of Metformin?",
        key="query_input"
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        submit_button = st.button("🚀 Submit", type="primary", use_container_width=True)

    # Process query when button is clicked
    if submit_button:
        if query and query.strip():
            st.session_state.agui_messages = []

            try:
                with st.spinner(f"🔄 Processing query: {query[:50]}..."):
                    response = st.session_state.orchestrator.run(query.strip())

                    # Add to conversation history
                    st.session_state.conversation_history.append({
                        "query": query.strip(),
                        "timestamp": datetime.now().isoformat(),
                        "messages": st.session_state.agui_messages.copy(),
                        "response": response
                    })

                    # Force rerun to show in history
                    st.rerun()

            except Exception as e:
                import traceback
                st.error(f"❌ Error occurred: {str(e)}")
                with st.expander("🔍 View Full Error Details"):
                    st.code(traceback.format_exc())
        else:
            st.warning("⚠️ Please enter a query first!")

    # Show conversation history
    if st.session_state.conversation_history:
        st.markdown("---")
        render_conversation_history()


if __name__ == "__main__":
    main()
