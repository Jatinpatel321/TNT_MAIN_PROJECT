"""TNT Backend Application Package.
Provides compatibility shims for Pydantic v1 / v2 method interfaces
and stubs for optional ML dependencies.
"""
import sys
import types

# Stub out optional ML libraries if not installed in the environment
for mod_name in ['joblib', 'scipy', 'pandas', 'sklearn', 'xgboost', 'lightgbm']:
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            stub = types.ModuleType(mod_name)
            stub.__file__ = '<stub>'
            stub.__package__ = mod_name
            sys.modules[mod_name] = stub

from pydantic import BaseModel

# Ensure Pydantic 1.10 BaseModel provides model_dump and model_validate shims
if not hasattr(BaseModel, "model_dump"):
    def _model_dump(self, *args, **kwargs):
        # Support exclude_unset / exclude_none / etc
        return self.dict(*args, **kwargs)
    BaseModel.model_dump = _model_dump

if not hasattr(BaseModel, "model_validate"):
    @classmethod
    def _model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, dict):
            return cls.parse_obj(obj)
        try:
            return cls.from_orm(obj)
        except Exception:
            return cls.parse_obj(obj)
    BaseModel.model_validate = _model_validate

