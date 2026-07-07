"""
AI Inventory Planning Service
==============================

Predicts inventory needs using ML/statistical analysis:

- Items likely to finish: Stock-out probability prediction
- Items to restock: Reorder suggestions based on demand
- Expected demand: Future order quantity prediction
- Expected wastage: Wastage prediction based on expiry & demand

Generates:
- Restock Suggestions: What, when, how much to order
- Waste Reduction Suggestions: How to minimize waste
- Smart Purchase Planning: Optimal purchase quantities
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.menu.model import MenuItem, Inventory
from app.modules.orders.model import Order, OrderItem, OrderStatus

logger = logging.getLogger("tnt.ai.inventory")


# ── Data Models ─────────────────────────────────────────────────────────


class StockStatus(Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    OVERSTOCKED = "overstocked"


class RestockPriority(Enum):
    CRITICAL = "critical"  # Out of stock or about to
    HIGH = "high"  # <1 day stock remaining
    MEDIUM = "medium"  # <3 days stock remaining
    LOW = "low"  # <7 days stock remaining


@dataclass
class ItemPrediction:
    """Prediction for a single inventory item."""
    item_id: int
    item_name: str
    current_stock: int
    stock_status: StockStatus
    
    # Demand predictions
    predicted_demand_today: int
    predicted_demand_3days: int
    predicted_demand_7days: int
    
    # Stock-out prediction
    days_until_out_of_stock: float
    stock_out_probability: float  # 0-1
    
    # Restock info
    restock_suggested: bool
    restock_quantity: int
    restock_priority: RestockPriority
    restock_by_date: Optional[str]
    
    # Waste prediction
    predicted_wastage: float
    waste_risk: str  # high/medium/low
    
    # Purchase planning
    optimal_purchase_quantity: int
    purchase_window_days: int


@dataclass
class InventoryPlanningResult:
    """Complete inventory planning results for a vendor."""
    vendor_id: int
    generated_at: str
    
    # Predictions
    items_likely_to_finish: List[Dict[str, Any]]
    items_to_restock: List[Dict[str, Any]]
    expected_demand: Dict[str, Any]
    expected_wastage: Dict[str, Any]
    
    # Suggestions
    restock_suggestions: List[Dict[str, Any]]
    waste_reduction_suggestions: List[Dict[str, Any]]
    smart_purchase_plan: List[Dict[str, Any]]
    
    # Summary
    summary: Dict[str, Any]
    insights: List[str]


# ── AI Inventory Planning Service ──────────────────────────────────────


class AIInventoryPlanningService:
    """AI-powered inventory planning and prediction service."""

    def __init__(self, db: Session):
        self.db = db

    # ── Main Planning Engine ─────────────────────────────────────────────

    def generate_inventory_plan(self, vendor_id: int) -> InventoryPlanningResult:
        """Generate complete inventory plan for a vendor.
        
        Args:
            vendor_id: Vendor ID
            
        Returns:
            InventoryPlanningResult with all predictions and suggestions
        """
        # Get all items for vendor
        items = self.db.query(MenuItem).filter(
            MenuItem.vendor_id == vendor_id,
            MenuItem.is_available == True,
        ).all()
        
        if not items:
            return self._empty_plan(vendor_id)
        
        # Get sales history for demand prediction
        cutoff_7d = utcnow_naive() - timedelta(days=7)
        cutoff_30d = utcnow_naive() - timedelta(days=30)
        cutoff_90d = utcnow_naive() - timedelta(days=90)
        
        order_items_7d = self.db.query(OrderItem).join(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff_7d,
            Order.status != OrderStatus.CANCELLED,
        ).all()
        
        order_items_30d = self.db.query(OrderItem).join(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff_30d,
            Order.status != OrderStatus.CANCELLED,
        ).all()
        
        order_items_90d = self.db.query(OrderItem).join(Order).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= cutoff_90d,
            Order.status != OrderStatus.CANCELLED,
        ).all()
        
        # Build sales data per item
        item_sales_7d = self._aggregate_sales(order_items_7d)
        item_sales_30d = self._aggregate_sales(order_items_30d)
        item_sales_90d = self._aggregate_sales(order_items_90d)
        
        # Process each item
        predictions = []
        items_likely_to_finish = []
        items_to_restock = []
        
        for item in items:
            inventory = self.db.query(Inventory).filter(
                Inventory.menu_item_id == item.id
            ).first()
            
            current_stock = inventory.current_stock if inventory else 0
            low_stock_threshold = inventory.low_stock_threshold if inventory else 10
            
            # Get item sales
            sales_7d = item_sales_7d.get(item.id, 0)
            sales_30d = item_sales_30d.get(item.id, 0)
            sales_90d = item_sales_90d.get(item.id, 0)
            
            # Predict demand
            predicted_daily = self._predict_daily_demand(sales_7d, sales_30d, sales_90d)
            
            # Predict stock-out
            days_until_out = self._predict_days_until_out(current_stock, predicted_daily)
            stock_out_prob = self._predict_stock_out_probability(
                current_stock, predicted_daily, low_stock_threshold
            )
            
            # Determine stock status
            if current_stock <= 0:
                stock_status = StockStatus.OUT_OF_STOCK
            elif current_stock <= low_stock_threshold:
                stock_status = StockStatus.LOW_STOCK
            else:
                stock_status = StockStatus.IN_STOCK
            
            # Determine restock needs
            restock_needed = self._should_restock(
                current_stock, predicted_daily, low_stock_threshold
            )
            
            restock_qty = self._calculate_restock_quantity(
                current_stock, predicted_daily, stock_status
            )
            
            restock_priority = self._determine_restock_priority(
                current_stock, predicted_daily, low_stock_threshold
            )
            
            restock_by = self._calculate_restock_by_date(
                current_stock, predicted_daily
            )
            
            # Predict wastage
            predicted_wastage = self._predict_wastage(
                sales_30d, sales_90d, current_stock
            )
            waste_risk = self._assess_waste_risk(predicted_wastage, sales_30d)
            
            # Purchase planning
            optimal_qty = self._calculate_optimal_purchase(
                predicted_daily, stock_status, restock_priority
            )
            purchase_window = int(days_until_out) if days_until_out > 0 else 1
            
            prediction = ItemPrediction(
                item_id=item.id,
                item_name=item.name,
                current_stock=current_stock,
                stock_status=stock_status,
                predicted_demand_today=round(predicted_daily),
                predicted_demand_3days=round(predicted_daily * 3),
                predicted_demand_7days=round(predicted_daily * 7),
                days_until_out_of_stock=round(days_until_out, 1),
                stock_out_probability=round(stock_out_prob, 2),
                restock_suggested=restock_needed,
                restock_quantity=restock_qty,
                restock_priority=restock_priority,
                restock_by_date=restock_by,
                predicted_wastage=round(predicted_wastage, 1),
                waste_risk=waste_risk,
                optimal_purchase_quantity=optimal_qty,
                purchase_window_days=purchase_window,
            )
            
            predictions.append(prediction)
            
            # Track items likely to finish
            if days_until_out <= 3 or stock_out_prob > 0.7:
                items_likely_to_finish.append({
                    "item_id": item.id,
                    "item_name": item.name,
                    "current_stock": current_stock,
                    "daily_demand": round(predicted_daily, 1),
                    "days_until_out": round(days_until_out, 1),
                    "stock_out_probability": round(stock_out_prob, 2),
                    "severity": "critical" if days_until_out <= 1 else "high" if days_until_out <= 2 else "moderate",
                })
            
            # Track items to restock
            if restock_needed:
                items_to_restock.append({
                    "item_id": item.id,
                    "item_name": item.name,
                    "current_stock": current_stock,
                    "suggested_restock_quantity": restock_qty,
                    "priority": restock_priority.value,
                    "restock_by": restock_by,
                    "reason": self._get_restock_reason(current_stock, predicted_daily, low_stock_threshold),
                })
        
        # Generate summary
        summary = self._generate_summary(predictions)
        
        # Generate insights
        insights = self._generate_insights(predictions, summary)
        
        # Format expected demand
        expected_demand = {
            "total_daily_demand": sum(p.predicted_demand_today for p in predictions),
            "total_weekly_demand": sum(p.predicted_demand_7days for p in predictions),
            "items": [
                {
                    "item_id": p.item_id,
                    "item_name": p.item_name,
                    "daily": p.predicted_demand_today,
                    "weekly": p.predicted_demand_7days,
                }
                for p in predictions[:20]
            ],
        }
        
        # Format expected wastage
        expected_wastage = {
            "total_predicted_wastage": round(sum(p.predicted_wastage for p in predictions), 1),
            "high_risk_items": [p.item_name for p in predictions if p.waste_risk == "high"],
            "items": [
                {
                    "item_id": p.item_id,
                    "item_name": p.item_name,
                    "predicted_wastage": p.predicted_wastage,
                    "waste_risk": p.waste_risk,
                }
                for p in predictions if p.predicted_wastage > 0
            ],
        }
        
        return InventoryPlanningResult(
            vendor_id=vendor_id,
            generated_at=utcnow_naive().isoformat(),
            items_likely_to_finish=items_likely_to_finish,
            items_to_restock=items_to_restock,
            expected_demand=expected_demand,
            expected_wastage=expected_wastage,
            restock_suggestions=self._generate_restock_suggestions(predictions, items_to_restock),
            waste_reduction_suggestions=self._generate_waste_reduction_suggestions(predictions),
            smart_purchase_plan=self._generate_purchase_plan(predictions),
            summary=summary,
            insights=insights,
        )

    def _empty_plan(self, vendor_id: int) -> InventoryPlanningResult:
        """Return empty plan when no items exist."""
        return InventoryPlanningResult(
            vendor_id=vendor_id,
            generated_at=utcnow_naive().isoformat(),
            items_likely_to_finish=[],
            items_to_restock=[],
            expected_demand={"total_daily_demand": 0, "total_weekly_demand": 0, "items": []},
            expected_wastage={"total_predicted_wastage": 0, "high_risk_items": [], "items": []},
            restock_suggestions=[],
            waste_reduction_suggestions=[
                {"type": "general", "suggestion": "Add inventory items to start AI planning"}
            ],
            smart_purchase_plan=[],
            summary={
                "total_items": 0,
                "in_stock": 0,
                "low_stock": 0,
                "out_of_stock": 0,
                "overstocked": 0,
                "items_to_restock": 0,
                "items_likely_to_finish": 0,
                "items_with_waste_risk": 0,
            },
            insights=["No inventory items found. Add items to start AI planning."],
        )

    def _aggregate_sales(self, order_items: List[OrderItem]) -> Dict[int, int]:
        """Aggregate sales quantities per item."""
        sales = defaultdict(int)
        for oi in order_items:
            sales[oi.menu_item_id] += oi.quantity
        return dict(sales)

    def _predict_daily_demand(self, sales_7d: int, sales_30d: int, sales_90d: int) -> float:
        """Predict daily demand using weighted historical average."""
        # Weights: last 7 days = 0.5, last 30 days = 0.3, last 90 days = 0.2
        daily_7d = sales_7d / 7 if sales_7d > 0 else 0
        daily_30d = sales_30d / 30 if sales_30d > 0 else 0
        daily_90d = sales_90d / 90 if sales_90d > 0 else 0
        
        if daily_7d > 0:
            predicted = daily_7d * 0.5 + daily_30d * 0.3 + daily_90d * 0.2
        elif daily_30d > 0:
            predicted = daily_30d * 0.7 + daily_90d * 0.3
        else:
            predicted = daily_90d or 1  # Minimum demand of 1
        
        return max(0.5, predicted)

    def _predict_days_until_out(self, current_stock: int, daily_demand: float) -> float:
        """Predict days until stock runs out."""
        if daily_demand <= 0:
            return float('inf')
        if current_stock <= 0:
            return 0.0
        return current_stock / daily_demand

    def _predict_stock_out_probability(
        self, current_stock: int, daily_demand: float, low_stock_threshold: int
    ) -> float:
        """Predict probability of stock-out (0-1)."""
        if daily_demand <= 0:
            return 0.0
        
        days_until_out = self._predict_days_until_out(current_stock, daily_demand)
        
        if days_until_out <= 0:
            return 1.0
        elif days_until_out <= 1:
            return 0.9
        elif days_until_out <= 2:
            return 0.75
        elif days_until_out <= 3:
            return 0.5
        elif days_until_out <= 5:
            return 0.3
        elif days_until_out <= 7:
            return 0.15
        else:
            return 0.05

    def _should_restock(self, current_stock: int, daily_demand: float, threshold: int) -> bool:
        """Determine if item needs restocking."""
        if daily_demand <= 0:
            return False
        
        days_remaining = current_stock / daily_demand if daily_demand > 0 else float('inf')
        
        return (
            current_stock <= 0 or
            current_stock <= threshold or
            days_remaining <= 3
        )

    def _calculate_restock_quantity(self, current_stock: int, daily_demand: float, status: StockStatus) -> int:
        """Calculate suggested restock quantity."""
        if status == StockStatus.OUT_OF_STOCK:
            # Order for 7 days
            return max(1, round(daily_demand * 7))
        elif status == StockStatus.LOW_STOCK:
            # Order for 5 days
            return max(1, round(daily_demand * 5))
        else:
            # Calculate how much to top up
            days_to_cover = 7
            needed = round(daily_demand * days_to_cover)
            return max(0, needed - current_stock)

    def _determine_restock_priority(
        self, current_stock: int, daily_demand: float, threshold: int
    ) -> RestockPriority:
        """Determine restock priority level."""
        if current_stock <= 0:
            return RestockPriority.CRITICAL
        
        if daily_demand <= 0:
            return RestockPriority.LOW
        
        days_remaining = current_stock / daily_demand
        
        if days_remaining <= 1:
            return RestockPriority.CRITICAL
        elif days_remaining <= 3:
            return RestockPriority.HIGH
        elif days_remaining <= 7:
            return RestockPriority.MEDIUM
        else:
            return RestockPriority.LOW

    def _calculate_restock_by_date(self, current_stock: int, daily_demand: float) -> Optional[str]:
        """Calculate date by which restock is needed."""
        if daily_demand <= 0:
            return None
        
        days_remaining = current_stock / daily_demand if daily_demand > 0 else float('inf')
        
        if days_remaining == float('inf'):
            return None
        
        # Recommend restock 1 day before stock-out
        restock_by = utcnow_naive() + timedelta(days=max(0, days_remaining - 1))
        return restock_by.strftime("%Y-%m-%d")

    def _predict_wastage(self, sales_30d: int, sales_90d: int, current_stock: int) -> float:
        """Predict wastage (items that may expire or be wasted)."""
        # Wastage = stock that won't be sold before expiry
        # Approximate: items not sold / total stock
        if sales_30d <= 0 and sales_90d <= 0:
            return current_stock * 0.5  # High uncertainty
        
        # If selling less than stock, predict waste
        avg_daily_sales = sales_90d / 90 if sales_90d > 0 else 0
        
        if avg_daily_sales <= 0:
            return 0.0
        
        # Items that will sit for >7 days are potential waste
        days_to_clear = current_stock / avg_daily_sales
        if days_to_clear > 7:
            waste = current_stock - (avg_daily_sales * 7)
            return max(0, waste)
        
        return 0.0

    def _assess_waste_risk(self, predicted_wastage: float, sales_30d: int) -> str:
        """Assess waste risk level."""
        if predicted_wastage <= 0:
            return "low"
        elif predicted_wastage <= 10:
            return "medium"
        elif sales_30d <= 0:
            return "high"
        else:
            return "high"

    def _calculate_optimal_purchase(
        self, daily_demand: float, status: StockStatus, priority: RestockPriority
    ) -> int:
        """Calculate optimal purchase quantity."""
        if daily_demand <= 0:
            return 0
        
        # Base: 7 days supply
        base_qty = round(daily_demand * 7)
        
        # Adjust based on status
        if status == StockStatus.OUT_OF_STOCK:
            return base_qty
        elif status == StockStatus.LOW_STOCK:
            return round(base_qty * 0.8)
        else:
            return max(0, base_qty)

    def _get_restock_reason(self, current_stock: int, daily_demand: float, threshold: int) -> str:
        """Get reason for restock suggestion."""
        if current_stock <= 0:
            return "Out of stock"
        elif current_stock <= threshold:
            return f"Low stock ({current_stock}/{threshold})"
        else:
            days = round(current_stock / daily_demand, 1) if daily_demand > 0 else 0
            return f"Only {days} days remaining"

    # ── Summary & Insights ───────────────────────────────────────────────

    def _generate_summary(self, predictions: List[ItemPrediction]) -> Dict[str, Any]:
        """Generate summary statistics."""
        total = len(predictions)
        in_stock = sum(1 for p in predictions if p.stock_status == StockStatus.IN_STOCK)
        low_stock = sum(1 for p in predictions if p.stock_status == StockStatus.LOW_STOCK)
        out_of_stock = sum(1 for p in predictions if p.stock_status == StockStatus.OUT_OF_STOCK)
        overstocked = sum(1 for p in predictions if p.stock_status == StockStatus.OVERSTOCKED)
        to_restock = sum(1 for p in predictions if p.restock_suggested)
        likely_finish = sum(1 for p in predictions if p.days_until_out_of_stock <= 3)
        waste_risk = sum(1 for p in predictions if p.waste_risk == "high")
        
        return {
            "total_items": total,
            "in_stock": in_stock,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "overstocked": overstocked,
            "items_to_restock": to_restock,
            "items_likely_to_finish": likely_finish,
            "items_with_waste_risk": waste_risk,
        }

    def _generate_insights(self, predictions: List[ItemPrediction], summary: Dict[str, Any]) -> List[str]:
        """Generate AI insights."""
        insights = []
        
        # Stock status insights
        if summary["out_of_stock"] > 0:
            insights.append(f"URGENT: {summary['out_of_stock']} items are out of stock - immediate restock needed")
        if summary["low_stock"] > 0:
            insights.append(f"{summary['low_stock']} items are running low - schedule restock soon")
        if summary["items_likely_to_finish"] > 0:
            insights.append(f"{summary['items_likely_to_finish']} items likely to finish in the next 3 days")
        if summary["overstocked"] > 0:
            insights.append(f"{summary['overstocked']} items are overstocked - consider promotion or reduction")
        
        # Waste insights
        if summary["items_with_waste_risk"] > 0:
            insights.append(f"{summary['items_with_waste_risk']} items have high wastage risk - adjust ordering")
        
        # Priority items
        critical_items = [p for p in predictions if p.restock_priority == RestockPriority.CRITICAL]
        if critical_items:
            names = ", ".join(p.item_name for p in critical_items[:3])
            insights.append(f"Critical restock needed for: {names}")
        
        total_demand = sum(p.predicted_demand_7days for p in predictions)
        if total_demand > 0:
            insights.append(f"Expected weekly demand: ~{total_demand} units across all items")
        
        return insights

    # ── Suggestion Generators ────────────────────────────────────────────

    def _generate_restock_suggestions(self, predictions: List[ItemPrediction], to_restock: List[Dict]) -> List[Dict]:
        """Generate structured restock suggestions."""
        suggestions = []
        
        for item in to_restock:
            suggestion = {
                "item_name": item["item_name"],
                "current_stock": item["current_stock"],
                "suggested_quantity": item["suggested_restock_quantity"],
                "priority": item["priority"],
                "restock_by": item["restock_by"],
                "reason": item["reason"],
                "action": f"Order {item['suggested_restock_quantity']} units of {item['item_name']} by {item['restock_by']}" if item['restock_by'] else f"Order {item['suggested_restock_quantity']} units of {item['item_name']} immediately",
            }
            suggestions.append(suggestion)
        
        return suggestions

    def _generate_waste_reduction_suggestions(self, predictions: List[ItemPrediction]) -> List[Dict]:
        """Generate waste reduction suggestions."""
        suggestions = []
        
        # Check for overstocked items
        overstocked = [p for p in predictions if p.stock_status == StockStatus.OVERSTOCKED]
        if overstocked:
            names = ", ".join(p.item_name for p in overstocked[:5])
            suggestions.append({
                "type": "overstock",
                "severity": "high" if len(overstocked) > 3 else "medium",
                "suggestion": f"Reduce order quantities for overstocked items: {names}",
                "action": "Run a promotion or bundle deal to clear excess stock",
                "estimated_savings": f"Reduce waste by up to {len(overstocked) * 10} units",
            })
        
        # Check for slow-moving items
        slow_movers = [p for p in predictions if p.predicted_demand_today < 1 and p.current_stock > 10]
        if slow_movers:
            names = ", ".join(p.item_name for p in slow_movers[:3])
            suggestions.append({
                "type": "slow_moving",
                "severity": "medium",
                "suggestion": f"Review slow-moving items: {names} - consider reducing stock levels",
                "action": "Reduce reorder quantities and monitor demand",
                "estimated_savings": "Reduce carrying costs by 20-30%",
            })
        
        # General waste reduction tips
        suggestions.append({
            "type": "general",
            "severity": "low",
            "suggestion": "Implement FIFO (First In, First Out) inventory rotation",
            "action": "Train staff on proper stock rotation procedures",
            "estimated_savings": "Reduce spoilage by 15-25%",
        })
        
        suggestions.append({
            "type": "general",
            "severity": "low",
            "suggestion": "Use demand forecasting to optimize order quantities",
            "action": "Review AI predictions weekly and adjust orders accordingly",
            "estimated_savings": "Reduce overstock by 10-20%",
        })
        
        # Demand-based suggestions
        high_demand = [p for p in predictions if p.predicted_demand_today > 10]
        if high_demand:
            names = ", ".join(p.item_name for p in high_demand[:3])
            suggestions.append({
                "type": "demand_optimization",
                "severity": "medium",
                "suggestion": f"High demand items ({names}) - ensure adequate stock to prevent lost sales",
                "action": "Increase safety stock for high-demand items",
                "estimated_savings": "Prevent 5-10% revenue loss from stockouts",
            })
        
        return suggestions

    def _generate_purchase_plan(self, predictions: List[ItemPrediction]) -> List[Dict]:
        """Generate smart purchase plan."""
        plan = []
        
        # Group by priority
        for priority in [RestockPriority.CRITICAL, RestockPriority.HIGH, RestockPriority.MEDIUM, RestockPriority.LOW]:
            items = [p for p in predictions if p.restock_priority == priority]
            
            if not items:
                continue
            
            for item in items:
                plan.append({
                    "item_name": item.item_name,
                    "priority": priority.value,
                    "current_stock": item.current_stock,
                    "daily_demand": item.predicted_demand_today,
                    "optimal_quantity": item.optimal_purchase_quantity,
                    "days_to_cover": item.purchase_window_days,
                    "estimated_cost": self._estimate_cost(item.optimal_purchase_quantity),
                    "expected_delivery_window": self._get_delivery_window(priority),
                    "suggested_vendor": self._suggest_vendor(item.item_name),
                })
        
        return plan

    def _estimate_cost(self, quantity: int) -> Dict[str, float]:
        """Estimate cost for purchase quantity."""
        # Simplified: assume $5 per unit average cost
        avg_unit_cost = 5.0
        total_cost = quantity * avg_unit_cost
        return {
            "unit_cost": avg_unit_cost,
            "total_cost": round(total_cost, 2),
            "estimated": True,
        }

    def _get_delivery_window(self, priority: RestockPriority) -> str:
        """Get delivery window based on priority."""
        windows = {
            RestockPriority.CRITICAL: "Immediate (same day)",
            RestockPriority.HIGH: "Next 24 hours",
            RestockPriority.MEDIUM: "1-2 days",
            RestockPriority.LOW: "2-3 days",
        }
        return windows.get(priority, "3-5 days")

    def _suggest_vendor(self, item_name: str) -> str:
        """Suggest vendor for item."""
        # Simplified vendor suggestion logic
        if any(kw in item_name.lower() for kw in ["print", "paper", "xerox", "binding", "stationery"]):
            return "Office Supplies Co. - standard 1-2 day delivery"
        elif any(kw in item_name.lower() for kw in ["food", "snack", "drink", "beverage"]):
            return "Fresh Foods Distributor - standard 2-3 day delivery"
        else:
            return "General Supplies - standard 3-5 day delivery"

    # ── Public API Methods ───────────────────────────────────────────────

    def get_items_likely_to_finish(self, vendor_id: int) -> Dict[str, Any]:
        """Get items likely to finish soon."""
        plan = self.generate_inventory_plan(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "total_items": len(plan.items_likely_to_finish),
            "items": plan.items_likely_to_finish,
            "insights": [
                i for i in plan.insights if "finish" in i.lower() or "out of stock" in i.lower() or "critical" in i.lower()
            ],
        }

    def get_items_to_restock(self, vendor_id: int) -> Dict[str, Any]:
        """Get items that need restocking."""
        plan = self.generate_inventory_plan(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "total_items": len(plan.items_to_restock),
            "items": plan.items_to_restock,
            "priority_breakdown": {
                "critical": len([i for i in plan.items_to_restock if i["priority"] == "critical"]),
                "high": len([i for i in plan.items_to_restock if i["priority"] == "high"]),
                "medium": len([i for i in plan.items_to_restock if i["priority"] == "medium"]),
                "low": len([i for i in plan.items_to_restock if i["priority"] == "low"]),
            },
        }

    def get_expected_demand(self, vendor_id: int) -> Dict[str, Any]:
        """Get expected demand predictions."""
        plan = self.generate_inventory_plan(vendor_id)
        return plan.expected_demand

    def get_expected_wastage(self, vendor_id: int) -> Dict[str, Any]:
        """Get expected wastage predictions."""
        plan = self.generate_inventory_plan(vendor_id)
        return plan.expected_wastage

    def get_restock_suggestions(self, vendor_id: int) -> Dict[str, Any]:
        """Get restock suggestions."""
        plan = self.generate_inventory_plan(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "total_suggestions": len(plan.restock_suggestions),
            "suggestions": plan.restock_suggestions,
            "insights": [
                i for i in plan.insights if "restock" in i.lower()
            ],
        }

    def get_waste_reduction_suggestions(self, vendor_id: int) -> Dict[str, Any]:
        """Get waste reduction suggestions."""
        plan = self.generate_inventory_plan(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "total_suggestions": len(plan.waste_reduction_suggestions),
            "suggestions": plan.waste_reduction_suggestions,
            "insights": [
                i for i in plan.insights if "wast" in i.lower() or "overstock" in i.lower()
            ],
        }

    def get_smart_purchase_plan(self, vendor_id: int) -> Dict[str, Any]:
        """Get smart purchase plan."""
        plan = self.generate_inventory_plan(vendor_id)
        
        # Calculate total estimated cost
        total_cost = sum(
            p.get("estimated_cost", {}).get("total_cost", 0)
            for p in plan.smart_purchase_plan
        )
        
        return {
            "vendor_id": vendor_id,
            "total_items": len(plan.smart_purchase_plan),
            "plan": plan.smart_purchase_plan,
            "total_estimated_cost": round(total_cost, 2),
            "summary": plan.summary,
            "insights": plan.insights,
        }
