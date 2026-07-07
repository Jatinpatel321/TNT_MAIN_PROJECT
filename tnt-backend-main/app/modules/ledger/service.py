from sqlalchemy.orm import Session

from app.modules.ledger.model import Ledger, LedgerSource, LedgerType


def add_ledger_entry(
    order_id: int,
    amount: int,
    entry_type: LedgerType,
    source: LedgerSource,
    db: Session,
    payment_id: int | None = None,
    description: str | None = None
):
    entry = Ledger(
        order_id=order_id,
        payment_id=payment_id,
        amount=amount,
        entry_type=entry_type,
        source=source,
        description=description
    )

    db.add(entry)
