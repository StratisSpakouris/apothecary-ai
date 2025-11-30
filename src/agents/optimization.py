"""
Optimization Agent

Calculates optimal inventory orders based on forecasted demand,
current inventory, and cost parameters.

Uses Economic Order Quantity (EOQ) and safety stock calculations.
"""

from src.utils.logging import setup_logger
from src.schemas.forecasting import ForecastingResult
from src.schemas.optimization import (
    OptimizationResult,
    OrderRecommendation,
    OptimizationSummary,
    OptimizationConfig,
    MedicationInventory,
    OrderPriority,
    OrderReason
)

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import math


class OptimizationAgent:
    """
    Agent responsible for optimizing inventory orders.

    Combines:
    - Forecasted demand (from ForecastingAgent)
    - Current inventory levels
    - Cost parameters (carrying cost, stockout cost, order cost)

    Outputs:
    - Order recommendations with quantities and priorities
    - Reorder points and safety stock levels
    - Cost estimates and ROI analysis

    Uses EOQ (Economic Order Quantity) and safety stock formulas.
    Does NOT use LLM - pure operations research/optimization.
    """

    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialize Optimization Agent.

        Args:
            config: Optional configuration for optimization parameters
        """
        self.name = "OptimizationAgent"
        self.logger = setup_logger(self.name)
        self.config = config or OptimizationConfig()

        self.logger.info(f"Optimization Agent initialized")
        self.logger.info(f"  Target service level: {self.config.target_service_level:.0%}")
        self.logger.info(f"  Safety stock: {self.config.safety_stock_days} days")

    def execute(
        self,
        forecast: ForecastingResult,
        inventory_data: pd.DataFrame,
        medication_db: Optional[pd.DataFrame] = None
    ) -> OptimizationResult:
        """
        Generate optimal order recommendations.

        Args:
            forecast: Forecasting results with demand predictions
            inventory_data: Current inventory DataFrame with columns:
                           [medication, quantity, unit_cost, expiration_date, lot_number]
            medication_db: Optional medication database with:
                          [medication, category, case_size, lead_time_days]

        Returns:
            OptimizationResult with order recommendations
        """
        self.logger.info(f"Starting inventory optimization")
        self.logger.info(f"  Forecast period: {forecast.forecast_start_date} to {forecast.forecast_end_date}")
        self.logger.info(f"  Medications in forecast: {forecast.summary.total_medications}")

        # Step 1: Build current inventory status
        current_inventory = self._build_inventory_status(
            inventory_data,
            medication_db
        )

        # Step 2: Calculate demand from forecast
        demand_by_medication = self._aggregate_forecast_demand(forecast)

        # Step 3: Generate order recommendations
        order_recommendations = []

        for medication, forecasted_demand in demand_by_medication.items():
            inventory = current_inventory.get(medication)

            if inventory is None:
                self.logger.warning(f"  No inventory data for {medication}, skipping")
                continue

            recommendation = self._optimize_medication(
                medication=medication,
                inventory=inventory,
                forecasted_demand=forecasted_demand,
                forecast_horizon_days=forecast.summary.forecast_horizon_days
            )

            if recommendation:
                order_recommendations.append(recommendation)

        # Step 4: Generate summary
        summary = self._generate_summary(
            order_recommendations,
            current_inventory,
            demand_by_medication
        )

        # Build result
        result = OptimizationResult(
            analysis_date=date.today(),
            optimization_horizon_days=forecast.summary.forecast_horizon_days,
            order_recommendations=order_recommendations,
            summary=summary,
            forecasting_available=True,
            inventory_available=len(inventory_data) > 0,
            notes=[]
        )

        self.logger.info(f"Optimization complete:")
        self.logger.info(f"  Total recommendations: {len(order_recommendations)}")
        self.logger.info(f"  Critical orders: {summary.critical_orders}")
        self.logger.info(f"  Total order cost: ${summary.total_order_cost:,.2f}")

        return result

    def _build_inventory_status(
        self,
        inventory_data: pd.DataFrame,
        medication_db: Optional[pd.DataFrame]
    ) -> Dict[str, MedicationInventory]:
        """
        Build current inventory status for each medication.

        Returns:
            Dict[medication -> MedicationInventory]
        """
        inventory_status = {}

        # Group by medication
        for medication, group in inventory_data.groupby('medication'):
            # Sum quantities across lots
            total_quantity = group['quantity'].sum()

            # Count lots
            lot_count = group['lot_number'].nunique() if 'lot_number' in group.columns else 1

            # Get expiration info
            earliest_expiry = None
            units_expiring_soon = 0

            if 'expiration_date' in group.columns:
                group_with_dates = group.dropna(subset=['expiration_date']).copy()

                if len(group_with_dates) > 0:
                    # Convert to datetime if needed
                    if not pd.api.types.is_datetime64_any_dtype(group_with_dates['expiration_date']):
                        group_with_dates['expiration_date'] = pd.to_datetime(group_with_dates['expiration_date'])

                    earliest_expiry = group_with_dates['expiration_date'].min().date()

                    # Units expiring within 30 days
                    thirty_days_from_now = pd.Timestamp(date.today() + timedelta(days=30))
                    expiring_soon = group_with_dates[group_with_dates['expiration_date'] <= thirty_days_from_now]
                    units_expiring_soon = expiring_soon['quantity'].sum()

            # Get cost info
            unit_cost = group['unit_cost'].mean()

            # Get medication DB info
            case_size = 1
            lead_time_days = 7  # Default

            if medication_db is not None:
                med_info = medication_db[medication_db['medication'] == medication]
                if len(med_info) > 0:
                    case_size = int(med_info.iloc[0].get('case_size', 1))
                    lead_time_days = int(med_info.iloc[0].get('lead_time_days', 7))

            inventory_status[medication] = MedicationInventory(
                medication=medication,
                current_quantity=int(total_quantity),
                lot_count=lot_count,
                earliest_expiry=earliest_expiry,
                units_expiring_soon=int(units_expiring_soon),
                unit_cost=float(unit_cost),
                case_size=case_size,
                lead_time_days=lead_time_days
            )

        self.logger.info(f"  Inventory status: {len(inventory_status)} medications")

        return inventory_status

    def _aggregate_forecast_demand(
        self,
        forecast: ForecastingResult
    ) -> Dict[str, float]:
        """
        Aggregate forecasted demand by medication.

        Returns:
            Dict[medication -> total_demand]
        """
        demand = defaultdict(float)

        for med_forecast in forecast.medication_forecasts:
            demand[med_forecast.medication] += med_forecast.predicted_demand

        return dict(demand)

    def _optimize_medication(
        self,
        medication: str,
        inventory: MedicationInventory,
        forecasted_demand: float,
        forecast_horizon_days: int
    ) -> Optional[OrderRecommendation]:
        """
        Generate order recommendation for a single medication.

        Uses EOQ formula and safety stock calculations.
        """
        # Calculate daily demand rate
        daily_demand = forecasted_demand / forecast_horizon_days

        # Calculate safety stock (based on lead time and variability)
        z_score = 1.65  # For 95% service level
        lead_time_demand = daily_demand * inventory.lead_time_days
        safety_stock = int(daily_demand * self.config.safety_stock_days)

        # Calculate reorder point
        reorder_point = int(lead_time_demand + safety_stock)

        # Check if order is needed
        current_quantity = inventory.current_quantity
        days_of_supply = current_quantity / daily_demand if daily_demand > 0 else 999

        # Determine if we need to order
        needs_order = current_quantity <= reorder_point

        # Calculate order quantity using EOQ if order is needed
        if needs_order or days_of_supply < self.config.high_priority_threshold_days:
            if self.config.use_eoq:
                # EOQ = sqrt((2 * D * S) / H)
                # D = annual demand
                # S = order cost
                # H = holding cost per unit per year

                annual_demand = daily_demand * 365
                holding_cost_per_unit = inventory.unit_cost * self.config.carrying_cost_rate

                if holding_cost_per_unit > 0:
                    eoq = math.sqrt(
                        (2 * annual_demand * self.config.order_fixed_cost) / holding_cost_per_unit
                    )
                else:
                    # Fallback: order for forecast_horizon_days
                    eoq = forecasted_demand

                order_quantity = int(eoq)
            else:
                # Simple approach: order enough for horizon + safety stock
                order_quantity = int(forecasted_demand + safety_stock - current_quantity)

            # Ensure minimum order
            order_quantity = max(order_quantity, self.config.min_order_quantity)

            # Round to case size if enabled
            if self.config.round_to_case_size and inventory.case_size > 1:
                recommended_cases = math.ceil(order_quantity / inventory.case_size)
                order_quantity = recommended_cases * inventory.case_size
            else:
                recommended_cases = math.ceil(order_quantity / inventory.case_size)

            # Calculate costs
            order_cost = order_quantity * inventory.unit_cost

            # Calculate days of supply after order
            days_of_supply_after_order = (current_quantity + order_quantity) / daily_demand if daily_demand > 0 else 999

            # Determine priority and reasons
            reasons = []
            if days_of_supply < self.config.critical_threshold_days:
                priority = OrderPriority.CRITICAL
                reasons.append(OrderReason.STOCKOUT_RISK)
            elif days_of_supply < self.config.high_priority_threshold_days:
                priority = OrderPriority.HIGH
                reasons.append(OrderReason.REORDER_POINT)
            elif needs_order:
                priority = OrderPriority.MEDIUM
                reasons.append(OrderReason.ROUTINE)
            else:
                priority = OrderPriority.LOW
                reasons.append(OrderReason.ROUTINE)

            # Check for expiring stock
            if inventory.units_expiring_soon > 0:
                reasons.append(OrderReason.EXPIRING_SOON)

            # Calculate urgency score
            urgency_score = max(0, min(1, 1 - (days_of_supply / self.config.high_priority_threshold_days)))

            # Calculate stockout risk
            stockout_risk = max(0, min(1, 1 - (current_quantity / reorder_point)))

            # Calculate overstock risk (after order)
            target_stock = forecasted_demand + safety_stock
            overstock_risk = max(0, min(1, (current_quantity + order_quantity - target_stock) / target_stock))

            # Create recommendation
            recommendation = OrderRecommendation(
                medication=medication,
                category=inventory.category,
                current_quantity=current_quantity,
                forecasted_demand_30d=forecasted_demand,
                recommended_order_quantity=order_quantity,
                recommended_cases=recommended_cases,
                reorder_point=reorder_point,
                safety_stock=safety_stock,
                order_cost=order_cost,
                days_of_supply=days_of_supply_after_order,
                priority=priority,
                reasons=reasons,
                urgency_score=urgency_score,
                stockout_risk=stockout_risk,
                overstock_risk=overstock_risk,
                notes=[]
            )

            return recommendation
        else:
            # No order needed - sufficient stock
            return None

    def _generate_summary(
        self,
        order_recommendations: List[OrderRecommendation],
        current_inventory: Dict[str, MedicationInventory],
        demand_by_medication: Dict[str, float]
    ) -> OptimizationSummary:
        """Generate high-level summary of optimization results."""

        # Count by priority
        critical_orders = sum(1 for o in order_recommendations if o.priority == OrderPriority.CRITICAL)
        high_priority_orders = sum(1 for o in order_recommendations if o.priority == OrderPriority.HIGH)

        # Total costs
        total_order_cost = sum(o.order_cost for o in order_recommendations)

        # Current inventory value
        total_current_value = sum(
            inv.current_quantity * inv.unit_cost
            for inv in current_inventory.values()
        )

        # Carrying cost estimate (monthly)
        estimated_carrying_cost = total_current_value * (self.config.carrying_cost_rate / 12)

        # Risk metrics
        medications_at_risk = sum(1 for o in order_recommendations if o.stockout_risk > 0.5)
        avg_stockout_risk = np.mean([o.stockout_risk for o in order_recommendations]) if order_recommendations else 0.0

        # Total forecasted demand
        total_forecasted_demand = sum(demand_by_medication.values())

        return OptimizationSummary(
            optimization_date=date.today(),
            total_recommendations=len(order_recommendations),
            critical_orders=critical_orders,
            high_priority_orders=high_priority_orders,
            total_order_cost=total_order_cost,
            estimated_carrying_cost=estimated_carrying_cost,
            potential_savings=0.0,  # Could calculate based on avoided stockouts
            medications_at_risk=medications_at_risk,
            average_stockout_risk=avg_stockout_risk,
            total_current_value=total_current_value,
            total_forecasted_demand=total_forecasted_demand
        )
