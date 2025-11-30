"""
Optimization Schemas

Data structures for inventory optimization and order recommendations.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import date
from enum import Enum


class OrderPriority(str, Enum):
    """Priority level for orders."""
    CRITICAL = "critical"  # Urgent - risk of stockout
    HIGH = "high"  # Should order soon
    MEDIUM = "medium"  # Normal reorder
    LOW = "low"  # Can wait


class OrderReason(str, Enum):
    """Reason for order recommendation."""
    STOCKOUT_RISK = "stockout_risk"  # Below safety stock
    REORDER_POINT = "reorder_point"  # Hit reorder point
    DEMAND_SPIKE = "demand_spike"  # Forecasted spike
    EXPIRING_SOON = "expiring_soon"  # Current stock expiring
    ROUTINE = "routine"  # Normal replenishment
    SHORTAGE = "shortage"  # Known supply shortage


class MedicationInventory(BaseModel):
    """
    Current inventory status for a medication.
    """

    medication: str = Field(..., description="Medication name")
    category: Optional[str] = Field(None, description="Medication category")

    # Current stock
    current_quantity: int = Field(..., description="Units currently in stock")
    lot_count: int = Field(0, description="Number of different lots")

    # Expiration tracking
    earliest_expiry: Optional[date] = Field(None, description="Date of earliest expiring lot")
    units_expiring_soon: int = Field(0, description="Units expiring within 30 days")

    # Cost information
    unit_cost: float = Field(..., description="Cost per unit")
    case_size: int = Field(1, description="Units per case/order")

    # Lead time
    lead_time_days: int = Field(7, description="Days from order to delivery")


class OrderRecommendation(BaseModel):
    """
    Order recommendation for a single medication.
    """

    medication: str = Field(..., description="Medication name")
    category: Optional[str] = Field(None, description="Medication category")

    # Current status
    current_quantity: int = Field(..., description="Current stock level")
    forecasted_demand_30d: float = Field(..., description="Predicted demand next 30 days")

    # Optimization results
    recommended_order_quantity: int = Field(..., description="Suggested order quantity (units)")
    recommended_cases: int = Field(..., description="Suggested order (cases)")
    reorder_point: int = Field(..., description="Reorder when stock hits this level")
    safety_stock: int = Field(..., description="Minimum stock to maintain")

    # Financial
    order_cost: float = Field(..., description="Total cost of recommended order")
    days_of_supply: float = Field(..., description="Days this order will last")

    # Priority and reasoning
    priority: OrderPriority = Field(..., description="Order priority level")
    reasons: List[OrderReason] = Field(..., description="Why this order is recommended")
    urgency_score: float = Field(..., ge=0, le=1, description="Urgency score (0-1)")

    # Risk assessment
    stockout_risk: float = Field(..., ge=0, le=1, description="Risk of running out (0-1)")
    overstock_risk: float = Field(..., ge=0, le=1, description="Risk of excess (0-1)")

    # Metadata
    notes: List[str] = Field(default_factory=list, description="Additional notes")


class OptimizationSummary(BaseModel):
    """
    High-level summary of optimization results.
    """

    optimization_date: date = Field(..., description="When optimization was run")

    # Order statistics
    total_recommendations: int = Field(..., description="Total order recommendations")
    critical_orders: int = Field(0, description="Critical priority orders")
    high_priority_orders: int = Field(0, description="High priority orders")

    # Financial
    total_order_cost: float = Field(..., description="Total cost of all recommended orders")
    estimated_carrying_cost: float = Field(0.0, description="Estimated monthly carrying cost")
    potential_savings: float = Field(0.0, description="Potential cost savings")

    # Risk metrics
    medications_at_risk: int = Field(0, description="Medications at stockout risk")
    average_stockout_risk: float = Field(..., ge=0, le=1, description="Average stockout risk")

    # Inventory metrics
    total_current_value: float = Field(..., description="Value of current inventory")
    total_forecasted_demand: float = Field(..., description="30-day forecasted demand")


class OptimizationResult(BaseModel):
    """
    Complete optimization result with all order recommendations.

    This is the main output from the OptimizationAgent.
    """

    # Time reference
    analysis_date: date = Field(..., description="When optimization was performed")
    optimization_horizon_days: int = Field(30, description="Optimization horizon")

    # Recommendations
    order_recommendations: List[OrderRecommendation] = Field(
        ...,
        description="List of order recommendations"
    )

    # Summary
    summary: OptimizationSummary = Field(..., description="High-level summary")

    # Inputs used
    forecasting_available: bool = Field(..., description="Was forecast data available")
    inventory_available: bool = Field(..., description="Was inventory data available")

    # Metadata
    notes: List[str] = Field(default_factory=list, description="Optimization notes")

    def get_critical_orders(self) -> List[OrderRecommendation]:
        """Get critical and high priority orders."""
        return [
            order for order in self.order_recommendations
            if order.priority in [OrderPriority.CRITICAL, OrderPriority.HIGH]
        ]

    def get_order_by_medication(self, medication: str) -> Optional[OrderRecommendation]:
        """Get order recommendation for specific medication."""
        for order in self.order_recommendations:
            if order.medication == medication:
                return order
        return None

    def get_total_order_cost(self) -> float:
        """Calculate total cost of all recommended orders."""
        return sum(order.order_cost for order in self.order_recommendations)

    def get_orders_by_priority(self, priority: OrderPriority) -> List[OrderRecommendation]:
        """Get all orders of a specific priority."""
        return [
            order for order in self.order_recommendations
            if order.priority == priority
        ]


class OptimizationConfig(BaseModel):
    """
    Configuration for OptimizationAgent.
    """

    # Service level targets
    target_service_level: float = Field(
        0.95,
        ge=0,
        le=1,
        description="Target service level (probability of not stocking out)"
    )

    # Safety stock settings
    safety_stock_days: int = Field(7, description="Days of safety stock to maintain")
    lead_time_variability: float = Field(0.1, description="Lead time standard deviation factor")

    # Cost parameters
    carrying_cost_rate: float = Field(
        0.20,
        description="Annual carrying cost as % of inventory value"
    )
    stockout_cost_multiplier: float = Field(
        5.0,
        description="Cost of stockout relative to unit cost"
    )
    order_fixed_cost: float = Field(
        50.0,
        description="Fixed cost per order (processing, shipping)"
    )

    # Thresholds
    critical_threshold_days: int = Field(
        3,
        description="Days of stock remaining to trigger critical alert"
    )
    high_priority_threshold_days: int = Field(
        7,
        description="Days of stock remaining to trigger high priority"
    )

    # Optimization method
    use_eoq: bool = Field(True, description="Use Economic Order Quantity formula")
    round_to_case_size: bool = Field(True, description="Round orders to case sizes")

    # Constraints
    max_order_value: Optional[float] = Field(
        None,
        description="Maximum order value (budget constraint)"
    )
    min_order_quantity: int = Field(1, description="Minimum order quantity (units)")
