from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User, UserRole
from app.modules.users.schemas import UserCreate, UserPreferencesUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


def _get_current_db_user(user: dict, db: Session) -> User:
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.phone == user.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone already registered")

    new_user = User(
        phone=user.phone,
        name=user.name,
        full_name=user.name,
        role=UserRole(user.role.value),
        university_id=user.university_id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/me", response_model=UserResponse)
def get_me(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return _get_current_db_user(user, db)


@router.put("/me", response_model=UserResponse)
def update_profile(
    name: str,
    university_id: str | None = None,
    preferences: dict | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = _get_current_db_user(user, db)

    if db_user.phone != user["phone"]:
        raise HTTPException(status_code=403, detail="Cannot edit other user's profile")

    if db_user.role.value in ["student", "faculty"] and not university_id:
        raise HTTPException(status_code=400, detail="University ID required for students/faculty")

    db_user.name = name
    db_user.full_name = name
    if university_id is not None:
        db_user.university_id = university_id
    if preferences is not None:
        db_user.preferences = preferences

    db.commit()
    db.refresh(db_user)
    return db_user


@router.put("/me/preferences")
def update_preferences(
    body: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Set structured dietary and meal preferences for the current user.

    These preferences are stored in the ``preferences`` JSON column on the
    User model and are consumed by the AI personalization engine
    (``GET /ai/personalization``) in addition to order-history signals.

    Any field left as ``null`` is ignored — only supplied fields are merged
    into the existing preferences blob.  This means partial updates are safe
    to call without overwriting unrelated preference fields.
    """
    db_user = _get_current_db_user(user, db)

    current_prefs: dict = db_user.preferences or {}
    update_data = body.model_dump(exclude_none=True)

    for key, value in update_data.items():
        if isinstance(value, list):
            update_data[key] = [v.value if hasattr(v, "value") else v for v in value]

    merged = {**current_prefs, **update_data}
    db_user.preferences = merged
    db.commit()

    return {
        "message": "Preferences updated",
        "preferences": merged,
    }


@router.get("/me/preferences")
def get_preferences(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return the structured preferences for the current user."""
    db_user = _get_current_db_user(user, db)
    return {"preferences": db_user.preferences or {}}
