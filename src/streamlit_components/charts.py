"""
Visualization Components for Streamlit Dashboard

Renders charts and graphs for inventory, forecasts, and patient data.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
from pathlib import Path


def load_inventory_data():
    """Load current inventory data"""
    try:
        inventory_path = Path("data/raw/inventory/current_stock.csv")
        medication_path = Path("data/raw/medications/medication_database.csv")

        if inventory_path.exists() and medication_path.exists():
            inventory = pd.read_csv(inventory_path)
            medications = pd.read_csv(medication_path)

            # Merge to get categories
            inventory = inventory.merge(
                medications[['medication', 'category']],
                on='medication',
                how='left'
            )

            return inventory
        return None
    except Exception as e:
        st.error(f"Error loading inventory data: {e}")
        return None


def render_inventory_overview_with_chart():
    """Render inventory overview with table and pie chart side-by-side"""
    inventory = load_inventory_data()

    if inventory is None:
        st.warning("No inventory data available")
        return

    # Group by medication to get totals
    medication_summary = inventory.groupby('medication').agg({
        'quantity': 'sum',
        'unit_cost': 'mean',
        'category': 'first'
    }).reset_index()

    medication_summary['total_value'] = (
        medication_summary['quantity'] * medication_summary['unit_cost']
    )

    # Sort by quantity descending
    medication_summary = medication_summary.sort_values('quantity', ascending=False)

    # Summary metrics at top
    col1, col2, col3 = st.columns(3)

    with col1:
        total_value = medication_summary['total_value'].sum()
        st.metric("Total Inventory Value", f"${total_value:,.2f}")

    with col2:
        total_items = len(medication_summary)
        st.metric("Unique Medications", total_items)

    with col3:
        total_quantity = medication_summary['quantity'].sum()
        st.metric("Total Units", f"{total_quantity:,}")

    st.markdown("---")

    # Two columns: Table on left, Chart on right
    col_table, col_chart = st.columns([1, 1])

    with col_table:
        st.markdown("### 📋 Inventory Table")
        # Display table with formatting
        display_df = medication_summary[['medication', 'quantity', 'category']].copy()
        display_df.columns = ['Medication', 'Quantity', 'Category']

        st.dataframe(
            display_df.style.format({
                'Quantity': '{:,.0f}'
            }),
            use_container_width=True,
            height=400
        )

    with col_chart:
        st.markdown("### 📊 Distribution by Category")
        # Group by category for pie chart
        category_summary = medication_summary.groupby('category')['quantity'].sum().reset_index()

        # Create pie chart
        fig = px.pie(
            category_summary,
            values='quantity',
            names='category',
            title='Inventory Distribution',
            color_discrete_sequence=px.colors.sequential.Blues_r
        )

        fig.update_layout(height=400)
        fig.update_traces(textposition='inside', textinfo='percent+label')

        st.plotly_chart(fig, use_container_width=True)


def render_inventory_chart():
    """Render inventory overview chart (legacy - bar chart version)"""
    inventory = load_inventory_data()

    if inventory is None:
        st.warning("No inventory data available")
        return

    # Group by category
    category_summary = inventory.groupby('category').agg({
        'quantity': 'sum',
        'unit_cost': 'mean'
    }).reset_index()

    category_summary['total_value'] = (
        category_summary['quantity'] * category_summary['unit_cost']
    )

    # Create bar chart
    fig = px.bar(
        category_summary,
        x='category',
        y='total_value',
        title='Inventory Value by Category',
        labels={'total_value': 'Total Value ($)', 'category': 'Category'},
        color='total_value',
        color_continuous_scale='Blues'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        height=400,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        total_value = category_summary['total_value'].sum()
        st.metric("Total Inventory Value", f"${total_value:,.2f}")

    with col2:
        total_items = inventory['medication'].nunique()
        st.metric("Unique Medications", total_items)

    with col3:
        total_quantity = inventory['quantity'].sum()
        st.metric("Total Units", f"{total_quantity:,}")


def render_category_breakdown(category_data: Dict[str, Any]):
    """Render category breakdown from query results"""
    if not category_data or 'medications' not in category_data:
        return

    df = pd.DataFrame(category_data['medications'])

    if df.empty:
        st.warning("No data to display")
        return

    # Create table
    st.dataframe(
        df[['medication', 'quantity', 'total_value']].style.format({
            'quantity': '{:,.0f}',
            'total_value': '${:,.2f}'
        }),
        use_container_width=True
    )

    # Create pie chart
    fig = px.pie(
        df,
        values='total_value',
        names='medication',
        title=f'Inventory Distribution - {category_data.get("category", "Category")}'
    )

    st.plotly_chart(fig, use_container_width=True)


def render_forecast_chart(forecast_data: Dict[str, Any]):
    """Render demand forecast chart"""
    if not forecast_data:
        st.warning("No forecast data available")
        return

    # Extract forecast information
    total_demand = forecast_data.get('total_demand', 0)
    medications = forecast_data.get('total_medications', 0)
    confidence = forecast_data.get('average_confidence', 0)
    flu_multiplier = forecast_data.get('flu_multiplier', 1.0)

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Forecasted Demand", f"{total_demand:,.0f} units")

    with col2:
        st.metric("Medications Forecasted", medications)

    with col3:
        st.metric("Average Confidence", f"{confidence:.0%}")

    with col4:
        flu_color = "inverse" if flu_multiplier > 1.3 else "off"
        st.metric(
            "Flu Season Impact",
            f"{flu_multiplier:.2f}x",
            delta=f"{(flu_multiplier - 1) * 100:.0f}%" if flu_multiplier > 1 else None,
            delta_color=flu_color
        )

    # Create a simple bar chart if we have category data
    if 'category' in forecast_data:
        st.info(f"📊 Forecast for **{forecast_data['category']}** category")


def render_patient_analysis_chart(analysis_data: Dict[str, Any]):
    """Render patient analysis visualization"""
    if not analysis_data:
        return

    # Extract behavior breakdown
    behavior = analysis_data.get('behavior_breakdown', {})

    if behavior:
        # Create pie chart
        df = pd.DataFrame([
            {'Behavior': k.replace('_', ' ').title(), 'Count': v}
            for k, v in behavior.items()
        ])

        fig = px.pie(
            df,
            values='Count',
            names='Behavior',
            title='Patient Behavior Classification',
            color_discrete_sequence=px.colors.sequential.Blues
        )

        st.plotly_chart(fig, use_container_width=True)

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Profiles", analysis_data.get('total_profiles', 0))

    with col2:
        st.metric("Unique Patients", analysis_data.get('unique_patients', 0))

    with col3:
        due_soon = analysis_data.get('due_soon_7_days', 0)
        st.metric("Due Soon (7 days)", due_soon, delta=f"{due_soon} patients")

    with col4:
        high_risk = analysis_data.get('high_risk_patients', 0)
        delta_color = "inverse" if high_risk > 0 else "off"
        st.metric("High-Risk Patients", high_risk, delta_color=delta_color)


def render_optimization_summary(opt_data: Dict[str, Any]):
    """Render optimization results summary"""
    if not opt_data or 'optimization' not in opt_data:
        return

    opt = opt_data['optimization']

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        recommendations = opt.get('total_recommendations', 0)
        st.metric("Order Recommendations", recommendations)

    with col2:
        critical = opt.get('critical_orders', 0)
        delta_color = "inverse" if critical > 0 else "off"
        st.metric("Critical Orders", critical, delta_color=delta_color)

    with col3:
        order_cost = opt.get('total_order_cost', 0)
        st.metric("Total Order Cost", f"${order_cost:,.2f}")

    with col4:
        inventory_value = opt.get('current_inventory_value', 0)
        st.metric("Current Inventory", f"${inventory_value:,.2f}")

    # Show critical medications if any
    if opt.get('critical_medications'):
        st.markdown("### ⚠️ Critical Medications")

        critical_meds = pd.DataFrame(opt['critical_medications'])

        st.dataframe(
            critical_meds.style.format({
                'order_quantity': '{:,.0f}',
                'order_cost': '${:,.2f}',
                'stockout_risk': '{:.0%}'
            }),
            use_container_width=True
        )


def render_inventory_status_gauge(medication: str, current_stock: int, forecasted_demand: int):
    """Render a gauge showing inventory status"""
    days_supply = (current_stock / forecasted_demand * 30) if forecasted_demand > 0 else 999

    # Determine color
    if days_supply < 3:
        color = "red"
        status = "CRITICAL"
    elif days_supply < 7:
        color = "orange"
        status = "LOW"
    elif days_supply < 14:
        color = "yellow"
        status = "MODERATE"
    else:
        color = "green"
        status = "GOOD"

    # Create gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=days_supply,
        title={'text': f"{medication} - Days Supply"},
        delta={'reference': 7, 'suffix': " days"},
        gauge={
            'axis': {'range': [None, 30]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 3], 'color': "lightgray"},
                {'range': [3, 7], 'color': "lightgray"},
                {'range': [7, 14], 'color': "lightgray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 3
            }
        }
    ))

    fig.update_layout(height=250)

    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Status: **{status}** | Current Stock: {current_stock:,} units | 30-day Demand: {forecasted_demand:,} units")
