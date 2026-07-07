"""
Global transaction safety decorator.

Usage
-----
::

    from app.core.db_transaction import transactional

    @transactional
    def my_service(order_id: int, user: dict, db: Session):
        ...

    @transactional
    async def my_webhook(request: Request, db: Session = Depends(get_db)):
        ...

Outcome mapping
---------------
Normal return       → ``db.commit()``
``HTTPException``   → ``db.commit()`` then re-raise
                      Deliberate business outcomes (e.g. marking a payment as
                      FAILED before returning 400) must be persisted — only
                      crashing mid-flight should roll back.
Any other exception → ``db.rollback()`` then re-raise
                      Prevents partial writes when an unexpected crash occurs
                      inside the function (e.g. ledger add throws after payment
                      status was already mutated in memory).

The ``db`` argument is found by name in the wrapped function's signature so it
can be passed either positionally or as a keyword argument, matching every
calling convention used throughout this codebase.
"""

from __future__ import annotations

import functools
import inspect
import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_db(func, args: tuple, kwargs: dict):
    """Return the ``db`` Session from *args* / *kwargs* using signature inspection."""
    if "db" in kwargs:
        return kwargs["db"]
    try:
        param_names = list(inspect.signature(func).parameters)
        idx = param_names.index("db")
        if idx < len(args):
            return args[idx]
    except (ValueError, TypeError):
        pass
    return None


def _safe_rollback(db) -> None:
    try:
        db.rollback()
    except Exception as err:
        logger.error("db_transaction event=rollback_failed error=%s", err)


def _safe_commit(db) -> None:
    db.commit()


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------

def transactional(func):
    """Wrap *func* in an atomic DB transaction (sync and async compatible)."""

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def _async_wrapper(*args, **kwargs):
            db = _get_db(func, args, kwargs)
            try:
                result = await func(*args, **kwargs)
                if db is not None:
                    _safe_commit(db)
                return result
            except HTTPException:
                # Business-logic 4xx/5xx: commit staged state (e.g. FAILED status)
                # before propagating the exception to the client.
                if db is not None:
                    _safe_commit(db)
                raise
            except Exception:
                # Unexpected crash: undo every in-memory mutation.
                if db is not None:
                    _safe_rollback(db)
                raise

        return _async_wrapper

    else:

        @functools.wraps(func)
        def _sync_wrapper(*args, **kwargs):
            db = _get_db(func, args, kwargs)
            try:
                result = func(*args, **kwargs)
                if db is not None:
                    _safe_commit(db)
                return result
            except HTTPException:
                if db is not None:
                    _safe_commit(db)
                raise
            except Exception:
                if db is not None:
                    _safe_rollback(db)
                raise

        return _sync_wrapper
