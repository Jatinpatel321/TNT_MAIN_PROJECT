import logging
from datetime import timedelta
from sqlalchemy.orm import Session
from app.core.time_utils import utcnow_naive
from app.modules.complaints.model import Complaint, ComplaintStatus

logger = logging.getLogger("tnt.complaints.escalation")

def auto_escalate_complaints_job(db: Session) -> int:
    """Escalate complaints that have been open/assigned/in_progress for more than 24 hours."""
    threshold_time = utcnow_naive() - timedelta(hours=24)
    
    active_statuses = [
        ComplaintStatus.OPEN,
        ComplaintStatus.ASSIGNED,
        ComplaintStatus.IN_PROGRESS
    ]
    
    overdue_complaints = db.query(Complaint).filter(
        Complaint.status.in_(active_statuses),
        Complaint.created_at <= threshold_time
    ).all()
    
    count = 0
    for complaint in overdue_complaints:
        complaint.status = ComplaintStatus.ESCALATED
        complaint.updated_at = utcnow_naive()
        count += 1
        logger.info(f"Escalated complaint #{complaint.id} (created at {complaint.created_at})")
        
    if count > 0:
        db.commit()
        
    logger.info(f"Auto-escalation check completed. Escalated {count} complaints.")
    return count
