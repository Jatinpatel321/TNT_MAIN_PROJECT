# AI Inventory Planning System
## Smart Predictions for Optimal Stock Management

---

## Overview

The AI Inventory Planning System provides intelligent predictions and suggestions for inventory management. It uses historical sales data and statistical analysis to forecast demand, predict stock-outs, and generate actionable recommendations.

### Core Predictions

| Prediction | Description | Methods |
|-----------|-------------|---------|
| **Items likely to finish** | Stock-out probability & timeline | Historical demand, current stock, consumption rate |
| **Items to restock** | Priority-based restock list | Stock levels, demand forecasting, thresholds |
| **Expected demand** | Future sales quantity prediction | Weighted moving average (7/30/90 days) |
| **Expected wastage** | Items at waste risk | Stock-to-sales ratio, slow-mover detection |

### Generated Outputs

| Output | Description |
|--------|-------------|
| **Restock Suggestions** | What, when, how much to order |
| **Waste Reduction Suggestions** | How to minimize waste & save costs |
| **Smart Purchase Plan** | Optimal purchase quantities with vendor suggestions |

---

## Architecture

```
Sales History (7/30/90 days) ──┐
                               ├──► AIInventoryPlanningService ──► REST API ──► Frontend
Current Stock (Inventory DB) ──┘         │
                                          │
                              ┌───────────┴────────────┐
                              │                        │
                         Predictions              Suggestions
                              │                        │
                    ┌─────────┼─────────┐    ┌─────────┼─────────┐
                    │         │         │    │         │         │
              Demand   Stock-out  Waste   Restock   Waste    Purchase
              Forecast  Risk     Risk    Plan     Reduction  Plan
```

---

## API Endpoints

**Base Path**: `/v1/vendors/inventory/ai`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/plan` | GET | Complete inventory plan (all sections) |
| `/items-finishing` | GET | Items likely to finish soon |
| `/items-restock` | GET | Items needing restock |
| `/demand` | GET | Expected demand predictions |
| `/wastage` | GET | Expected wastage predictions |
| `/restock-suggestions` | GET | Restock suggestions |
| `/waste-suggestions` | GET | Waste reduction suggestions |
| `/purchase-plan` | GET | Smart purchase plan |

---

## Prediction Methods

### Demand Prediction
Uses weighted historical average:
- Last 7 days: 50% weight (recent trends)
- Last 30 days: 30% weight (medium-term)
- Last 90 days: 20% weight (long-term baseline)

### Stock-Out Prediction
- Days until out = current_stock / daily_demand
- Probability based on days remaining:
  - 0 days: 100%
  - 1 day: 90%
  - 3 days: 50%
  - 7+ days: 5%

### Waste Prediction
- Items sitting >7 days at current sales rate are at waste risk
- Slow-moving items (daily demand < 1) with >10 stock
- Overstocked items flagged for promotion/reduction

---

## Integration with Inventory Module

The AI system integrates with the existing inventory module at:
- `app/modules/vendors/inventory_service.py` - Existing inventory service
- `app/modules/vendors/inventory_router.py` - Existing inventory endpoints
- `app/modules/vendors/ai_inventory_planning_service.py` - **New AI service**
- `app/modules/vendors/ai_inventory_router.py` - **New AI endpoints**

The AI service queries the same `MenuItem` and `Inventory` models, extending the existing functionality with predictions and suggestions.