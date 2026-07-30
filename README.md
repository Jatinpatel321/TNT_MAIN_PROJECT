# TNT Smart Scheduling App

## Project Overview

The TNT Smart Scheduling App is a comprehensive, intelligent scheduling and resource management system designed for university environments. It aims to streamline the process of booking, utilizing, and managing various campus resources, from academic services to recreational facilities. The project consists of a powerful backend built with FastAPI and a cross-platform mobile application developed using React Native.

## Problem Statement

University campuses are complex ecosystems with a high demand for shared resources. Students and faculty often face challenges in scheduling appointments, booking facilities, and managing their time effectively. Existing systems are often fragmented, inefficient, and lack real-time capabilities. This project addresses these issues by providing a centralized, user-friendly platform that optimizes resource allocation and enhances the overall campus experience.

## Features

-   **User Authentication:** Secure login and registration for students, faculty, and administrators with JWT tokens and Redis token revocation.
-   **Smart Scheduling & Slot Optimization:** AI-powered slot planner with strict 90% capacity safety limits and heuristic fallbacks.
-   **Resource Booking:** Real-time booking of campus facilities such as study rooms, labs, and sports courts.
-   **Order Management & Express Pickup:** Complete system for ordering stationery, food, and campus services with express pickup eligibility enforcement.
-   **AI/ML Intelligence Subsystem:**
    -   **Dynamic ETA Engine:** Real-time completion time estimation with historical fallback gates.
    -   **Demand Forecasting:** Predictive order volume modeling across campus vendors.
    -   **Vendor Speed & Ranking:** Multi-factor scoring with live load indicators and transparent source attribution.
    -   **Fraud Detection Pipeline:** ML risk scoring backed by deterministic safety rules and complete classification metrics (Precision, Recall, F1).
-   **Payment Integration:** Seamless Razorpay payment reconciliation with Redis distributed locks.
-   **Real-time Notifications:** Multi-channel alerts (FCM push, SMS fallback, WebSockets) with 30s heartbeat.
-   **Admin Dashboard & Vendor Apps:** Comprehensive admin dashboard (`tnt-admin`), vendor portal (`tnt-vendor-frontend`), and student application (`tnt-user-frontend`).

## Technology Stack

### Backend

-   **Framework:** FastAPI (Python 3.11+)
-   **Database:** PostgreSQL with SQLAlchemy ORM & Alembic migrations
-   **Caching & Locking:** Redis (AI signal caching & distributed locking)
-   **Machine Learning:** Scikit-Learn, Joblib, Scipy, NumPy
-   **Testing & Coverage:** Pytest, pytest-cov (Enforced **95% coverage gate** on AI/ML modules)

### Frontend

-   **Student & Vendor Mobile Apps:** React Native (TypeScript), React Navigation, React Native Paper
-   **Admin Web Dashboard:** React, Vite, Tailwind CSS, Lucide Icons

## Installation & Setup

### Prerequisites

-   Node.js (v18+) and npm/yarn
-   Python 3.11+ and pip
-   PostgreSQL & Redis
-   Git

### Backend

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Jatinpatel321/TNT_MAIN_PROJECT.git
    cd TNT_MAIN_PROJECT/tnt-backend-main
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate  # On Linux/macOS: source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure environment:**
    -   Copy `.env.example` to `.env` and set PostgreSQL and Redis credentials.
5.  **Run database migrations:**
    ```bash
    alembic upgrade head
    ```
6.  **Run the application:**
    ```bash
    uvicorn app.main:app --reload
    ```

### AI/ML Testing & 95% Coverage Gate Verification

To verify that the AI/ML subsystem meets the **95% code coverage gate** and passes all unit and safety regression tests:

```bash
python -m pytest \
  tests/test_ml_engine.py tests/test_ml_bridge.py tests/test_ml_predictions.py \
  tests/test_ml_registry.py tests/test_ml_router.py tests/test_ml_promotion_retraining.py \
  tests/test_training_pipeline_coverage.py tests/test_ml_safety_regression.py \
  tests/test_model_performance_validation.py tests/test_targeted_aiml_coverage.py \
  tests/test_ai_service.py tests/test_analytics_service.py tests/test_enhanced_eta_engine.py \
  tests/test_redis_ai_cache.py tests/test_vendor_speed_service.py \
  tests/test_production_upgrades.py tests/test_preference_engine.py \
  tests/test_ai_routers.py tests/test_ai.py tests/test_analytics.py \
  --cov=app.ml --cov=app.modules.ai_intelligence \
  --cov-report=term-missing --cov-fail-under=95 -q
```

Detailed testing results and metrics: [docs/AI_ML_Testing_Validation_Report_2026-07-30.md](docs/AI_ML_Testing_Validation_Report_2026-07-30.md).

### Frontends

1.  **Student App (`tnt-user-frontend`):**
    ```bash
    cd ../tnt-user-frontend
    npm install
    npx react-native run-android
    ```
2.  **Vendor App (`tnt-vendor-frontend`):**
    ```bash
    cd ../tnt-vendor-frontend
    npm install
    npx react-native run-android
    ```
3.  **Admin Portal (`tnt-admin`):**
    ```bash
    cd ../tnt-admin
    npm install
    npm run dev
    ```

## Project Structure

```
TNT_MAIN_PROJECT/
├── tnt-backend-main/           # FastAPI Backend Service
│   ├── app/
│   │   ├── ml/                 # ML Models, Predictions, Backtest & Registry
│   │   └── modules/            # Domain Modules (ai_intelligence, slots, orders, etc.)
│   ├── docs/                   # AI/ML Validation Reports & Specifications
│   ├── ml_models/              # Serialized ML Model Artifacts (.pkl)
│   ├── tests/                  # Pytest Unit & Regression Suite
│   └── alembic/                # Database Schema Migrations
├── tnt-user-frontend/          # React Native Mobile App for Students
├── tnt-vendor-frontend/        # React Native Mobile App for Campus Vendors
└── tnt-admin/                  # React/Vite Admin Dashboard
```

## Contributors

-   Jatinpatel321
-   Jemin29
