import os
import sys
import logging
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Set model storage dir if not already set
if not os.environ.get("MODEL_STORAGE_DIR"):
    os.environ["MODEL_STORAGE_DIR"] = "ml_models"

# Configure logging to show training progress
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("seed_and_train")

import app.database.init_db
from app.database.session import SessionLocal
from scripts.seed_ai_data import seed_ai_data
from app.ml.training_pipeline import ModelTrainer, train_fraud_detection
from app.ml.registry import ModelRegistry

def main():
    logger.info("Ensuring database tables exist...")
    from app.database.init_db import init_db
    init_db()
    
    logger.info("Initializing database session...")
    db = SessionLocal()
    
    try:
        # Clear/Reset DB before seeding to avoid duplicate constraints
        logger.info("Cleaning up existing database tables...")
        from app.database.base import Base
        from sqlalchemy import text
        table_names = list(Base.metadata.tables.keys())
        if table_names:
            tables_str = ", ".join([f'"{name}"' for name in table_names])
            db.execute(text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;"))
            db.commit()
            logger.info("All data cleared successfully via TRUNCATE CASCADE.")
            
        # a. Calls seed_ai_data() to generate synthetic training data
        logger.info("Step 1: Seeding synthetic training data...")
        seed_stats = seed_ai_data(db)
        logger.info(f"Seed stats: {seed_stats}")
        
        # b. Runs the full training pipeline for every model
        logger.info("Step 2: Running training pipeline...")
        trainer = ModelTrainer(db)
        
        models_to_train = [
            ("ETA Prediction", trainer.train_eta),
            ("Demand Forecasting", trainer.train_demand),
            ("Slot Recommendation", trainer.train_slot_recommendation),
            ("Recommendation Engine", trainer.train_recommendation),
            ("Vendor Ranking", trainer.train_vendor_ranking),
        ]
        
        trained_results = {}
        
        for name, train_fn in models_to_train:
            logger.info(f"Training {name}...")
            try:
                res = train_fn()
                trained_results[name] = res
                logger.info(f"Finished training {name}: {res.get('status')}")
            except Exception as e:
                logger.error(f"Failed to train {name}: {e}")
                trained_results[name] = {"status": "failed", "error": str(e)}
                
        # Train Fraud Detection
        logger.info("Training Fraud Detection...")
        try:
            fraud_res = train_fraud_detection(db)
            trained_results["Fraud Detection"] = fraud_res
            logger.info(f"Finished training Fraud Detection: {fraud_res.get('status')}")
        except Exception as e:
            logger.error(f"Failed to train Fraud Detection: {e}")
            trained_results["Fraud Detection"] = {"status": "failed", "error": str(e)}
            
        # d. Prints a summary: model name, feature count, training metric (RMSE or accuracy), artifact path.
        print("\n" + "="*80)
        print(f"{'ML MODEL TRAINING PIPELINE SUMMARY':^80}")
        print("="*80)
        print(f"{'Model Name':<25} | {'Features':<8} | {'Metric Value (RMSE/Acc)':<25} | {'Artifact Path'}")
        print("-" * 80)
        
        # Mapping model types in registry to print names
        registry_mapping = {
            "eta_prediction": "ETA Prediction",
            "demand_forecast": "Demand Forecasting",
            "slot_recommendation": "Slot Recommendation",
            "recommendation_engine": "Recommendation Engine",
            "vendor_ranking": "Vendor Ranking",
            "fraud_detection": "Fraud Detection"
        }
        
        for model_type, pretty_name in registry_mapping.items():
            try:
                # Load latest version info from registry
                latest_version = ModelRegistry.get_latest_version(model_type)
                if not latest_version:
                    print(f"{pretty_name:<25} | {'N/A':<8} | {'Not trained/failed':<25} | N/A")
                    continue
                    
                model_data = ModelRegistry.load(model_type, latest_version)
                if not model_data:
                    print(f"{pretty_name:<25} | {'N/A':<8} | {'Failed to load':<25} | N/A")
                    continue
                    
                model, metadata = model_data
                features = metadata.get("features", [])
                metrics = metadata.get("metrics", {})
                file_path = metadata.get("file_path", "N/A")
                
                feat_count = len(features) if features else 0
                
                # Format metrics nicely
                metric_val = "N/A"
                if "rmse" in metrics:
                    metric_val = f"RMSE: {metrics['rmse']:.4f}"
                elif "accuracy" in metrics:
                    metric_val = f"Accuracy: {metrics['accuracy']:.4f}"
                elif "explained_variance" in metrics:
                    metric_val = f"ExpVar: {metrics['explained_variance']:.4f}"
                elif metadata.get("accuracy") is not None:
                    metric_val = f"Score: {metadata.get('accuracy'):.4f}"
                    
                print(f"{pretty_name:<25} | {feat_count:<8} | {metric_val:<25} | {file_path}")
            except Exception as e:
                print(f"{pretty_name:<25} | {'Error':<8} | {str(e)[:23]:<25} | N/A")
                
        print("="*80)
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
