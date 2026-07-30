# ML Baseline Test Report

**Execution Date:** 2026-07-29  
**Command Run:** `pytest -q` (executed via `.venv\Scripts\python.exe -m pytest -q`)  
**Environment:** Windows x64, Python 3.11.9, pytest-9.1.1  

---

## Executive Summary

This report establishes the baseline pass/fail status of the test suite prior to any AI/ML integration or application code modifications.

- **Total Test Items Executed:** 1,201
- **Passed:** 1,167
- **Failed:** 18
- **Skipped:** 16
- **Errors during execution/collection:** 9

---

## Pass/Fail Baseline Details

### 1. Existing Test Failures (Pre-existing)

#### `test_admin_kpis.py`
- `test_admin_kpis_endpoint`: FAILED (`ModuleNotFoundError` / missing runtime context setup)

#### `test_core_coverage.py`
- `TestRequireRole::test_role_matches`: FAILED
- `TestRequireRole::test_role_mismatch_raises_403`: FAILED
- `TestRequireRole::test_vendor_role_mismatch`: FAILED
- `TestMenuFileUpload::test_valid_jpeg_saves_and_returns_path`: FAILED
- `TestMenuFileUpload::test_valid_png_saves_and_returns_path`: FAILED
- `TestMenuFileUpload::test_valid_webp_saves_and_returns_path`: FAILED

#### `tests/test_sms_dispatch.py`
- `TestUrgentEventSMSSent::test_delay_alert_triggers_sms`: FAILED
- `TestUrgentEventSMSSent::test_order_cancelled_triggers_sms`: FAILED
- `TestUrgentEventSMSSent::test_order_ready_triggers_sms`: FAILED
- `TestPromotionalSMSNotSent::test_system_defaults_to_sms`: FAILED
- `TestSMSFallbackSuppression::test_sms_not_skipped_when_fallback_false`: FAILED
- `TestSMSFallbackSuppression::test_sms_sent_when_push_fails`: FAILED
- `TestSMSMessageContent::test_cancellation_message`: FAILED
- `TestSMSMessageContent::test_delay_message`: FAILED
- `TestSMSMessageContent::test_ready_message`: FAILED
- `TestSlotCancellationSMSTriggered::test_cancel_slot_triggers_notification`: FAILED
- `TestPerUserSMSFallbackPreference::test_sms_fallback_false_from_prefs`: FAILED

#### `tests/test_ml_engine.py`
- `test_dataset_builder_integration`: FAILED (`FileNotFoundError: [Errno 2] No such file or directory: 'ml_models/test_model'`)
- `test_registry_list_and_load`: ERROR (`AttributeError: type object 'ModelRegistry' has no attribute 'list_models'`)
- `test_registry_rollback`: ERROR (`AttributeError`)
- `test_registry_update_metrics`: ERROR (`AttributeError`)
- `test_registry_delete_model`: ERROR (`AttributeError`)
- `test_registry_get_registry_summary`: ERROR (`AttributeError`)
- `test_training_pipeline_execution`: ERROR (`FileNotFoundError`)
- `test_explainability`: ERROR (`AttributeError`)
- `test_predictions`: ERROR (`AttributeError`)

---

## Raw Pytest Baseline Output

```text
=========================== short test summary info ===========================
FAILED test_admin_kpis.py::test_admin_kpis_endpoint - ModuleNotFoundError
FAILED test_core_coverage.py::TestRequireRole::test_role_matches - TypeError
FAILED test_core_coverage.py::TestRequireRole::test_role_mismatch_raises_403
FAILED test_core_coverage.py::TestRequireRole::test_vendor_role_mismatch - TypeError
FAILED test_core_coverage.py::TestMenuFileUpload::test_valid_jpeg_saves_and_returns_path
FAILED test_core_coverage.py::TestMenuFileUpload::test_valid_png_saves_and_returns_path
FAILED test_core_coverage.py::TestMenuFileUpload::test_valid_webp_saves_and_returns_path
FAILED tests/test_sms_dispatch.py::TestUrgentEventSMSSent::test_delay_alert_triggers_sms
FAILED tests/test_sms_dispatch.py::TestUrgentEventSMSSent::test_order_cancelled_triggers_sms
FAILED tests/test_sms_dispatch.py::TestUrgentEventSMSSent::test_order_ready_triggers_sms
FAILED tests/test_sms_dispatch.py::TestPromotionalSMSNotSent::test_system_defaults_to_sms
FAILED tests/test_sms_dispatch.py::TestSMSFallbackSuppression::test_sms_not_skipped_when_fallback_false
FAILED tests/test_sms_dispatch.py::TestSMSFallbackSuppression::test_sms_sent_when_push_fails
FAILED tests/test_sms_dispatch.py::TestSMSMessageContent::test_cancellation_message
FAILED tests/test_sms_dispatch.py::TestSMSMessageContent::test_delay_message
FAILED tests/test_sms_dispatch.py::TestSMSMessageContent::test_ready_message
FAILED tests/test_sms_dispatch.py::TestSlotCancellationSMSTriggered::test_cancel_slot_triggers_notification
FAILED tests/test_sms_dispatch.py::TestPerUserSMSFallbackPreference::test_sms_fallback_false_from_prefs
FAILED tests/test_ml_engine.py::test_dataset_builder_integration - FileNotFoundError
ERROR tests/test_ml_engine.py::test_registry_list_and_load - AttributeError
ERROR tests/test_ml_engine.py::test_registry_rollback - AttributeError
ERROR tests/test_ml_engine.py::test_registry_update_metrics - AttributeError
ERROR tests/test_ml_engine.py::test_registry_delete_model - AttributeError
ERROR tests/test_ml_engine.py::test_registry_get_registry_summary - AttributeError
ERROR tests/test_ml_engine.py::test_training_pipeline_execution - FileNotFoundError
ERROR tests/test_ml_engine.py::test_explainability - AttributeError
ERROR tests/test_ml_engine.py::test_predictions - AttributeError
================= 1167 passed, 16 skipped, 18 failed, 9 errors in 309.10s =================
```
