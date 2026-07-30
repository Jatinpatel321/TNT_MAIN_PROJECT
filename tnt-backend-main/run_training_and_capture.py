"""
Run ML training pipeline against live PostgreSQL database and capture metrics.
Output is written to docs/ml_baseline_metrics.md.

Usage:
    .\.venv\Scripts\python.exe run_training_and_capture.py
"""
import json
import os
import sys
from datetime import datetime

# Make sure we can import app modules
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

results = {}

print("=" * 60)
print(f"TNT ML Training Run — {datetime.utcnow().isoformat()}Z")
print(f"DB: {DATABASE_URL.split('@')[-1]}")
print("=" * 60)

# ── 1. ETA ──────────────────────────────────────────────────────────────
print("\n[1/5] Training ETA prediction model...")
from app.ml.training_pipeline import train_eta_models
r = train_eta_models(db, days=90)
results["eta_prediction"] = r
print(f"  => {r.get('status')} | rows={r.get('rows_trained')} | best={r.get('best_model')} | rmse={r.get('best_rmse')}")

# ── 2. Demand ────────────────────────────────────────────────────────────
print("\n[2/5] Training demand forecast model...")
from app.ml.training_pipeline import ModelTrainer
trainer = ModelTrainer(db)
r = trainer.train_demand(days=90)
results["demand_forecast"] = r
print(f"  => {r.get('status')} | rows={r.get('rows_trained')} | best={r.get('best_model')} | rmse={r.get('best_rmse')}")

# ── 3. Slot recommendation ───────────────────────────────────────────────
print("\n[3/5] Training slot recommendation model...")
r = trainer.train_slot_recommendation()
results["slot_recommendation"] = r
print(f"  => {r.get('status')} | rows={r.get('rows_trained')} | best={r.get('best_model')} | rmse={r.get('best_rmse')}")

# ── 4. Vendor ranking ────────────────────────────────────────────────────
print("\n[4/5] Training vendor ranking model...")
r = trainer.train_vendor_ranking()
results["vendor_ranking"] = r
print(f"  => {r.get('status')} | rows={r.get('rows_trained')} | best={r.get('best_model')} | rmse={r.get('best_rmse')}")

# ── 5. Fraud detection ───────────────────────────────────────────────────
print("\n[5/5] Training fraud detection model...")
from app.ml.training_pipeline import train_fraud_detection
r = train_fraud_detection(db)
results["fraud_detection"] = r
print(f"  => {r.get('status')} | rows={r.get('rows_trained')}")

db.close()

# Dump raw JSON for reference
print("\n\nRAW RESULTS JSON:")
print(json.dumps(results, indent=2, default=str))

# Write marker file so the next script can parse it
with open("docs/training_raw_results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print("\nRaw results written to docs/training_raw_results.json")
