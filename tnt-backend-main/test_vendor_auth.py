"""Tests for Vendor Authentication Module.

Covers:
- Vendor model creation
- Vendor registration flow (via existing User)
- Vendor owner login
- Vendor staff login
- Token refresh (rotation)
- Auth guard (get_current_vendor)
- Profile get/update
- Staff CRUD
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
import bcrypt as _bcrypt_lib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure all models are imported so Base.metadata.create_all can resolve foreign keys
import app.database.init_db  # noqa: F401
from app.database.base import Base
from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStaff, VendorStatus
from app.modules.vendors.auth_service import (
    _create_access_token,
    _create_refresh_token,
    _hash_password,
    _verify_password,
    _store_refresh_jti,
    _consume_refresh_jti,
    create_staff,
    delete_staff,
    get_current_vendor,
    get_vendor_profile,
    list_staff,
    login_as_vendor_owner,
    login_as_vendor_staff,
    refresh_vendor_token,
    register_vendor,
    update_staff,
    update_vendor_profile,
)
from app.core.time_utils import utcnow_naive

# ── In-memory SQLite test DB ────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Session:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _bcrypt_hash(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode("utf-8"), _bcrypt_lib.gensalt()).decode("utf-8")


def _create_user(db: Session, phone: str = "+919999999999", role: UserRole = UserRole.STUDENT) -> User:
    user = User(phone=phone, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ══════════════════════════════════════════════════════════════════════════════
# Model Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestVendorModel:
    def test_create_vendor(self, db):
        owner = _create_user(db)
        v = Vendor(vendor_name="Test Cafe", category="food", owner_id=owner.id,
                   password_hash=_bcrypt_hash("secret123"))
        db.add(v)
        db.commit()

        assert v.vendor_id is not None
        assert v.vendor_name == "Test Cafe"
        assert v.category == "food"
        assert v.owner_id == owner.id
        assert v.status == VendorStatus.PENDING

    def test_vendor_owner_relationship(self, db):
        owner = _create_user(db)
        v = Vendor(vendor_name="My Shop", category="stationery", owner_id=owner.id,
                   password_hash=_bcrypt_hash("pass"))
        db.add(v)
        db.commit()
        db.refresh(v)

        assert v.owner.phone == "+919999999999"

    def test_create_vendor_staff(self, db):
        owner = _create_user(db)
        v = Vendor(vendor_name="Shop", category="food", owner_id=owner.id,
                   password_hash=_bcrypt_hash("pass"))
        db.add(v)
        db.commit()
        db.refresh(v)

        staff = VendorStaff(vendor_id=v.vendor_id, name="John", role="staff",
                            phone="+919888888888", password_hash=_bcrypt_hash("staffpass"))
        db.add(staff)
        db.commit()
        db.refresh(staff)

        assert staff.id is not None
        assert staff.vendor_id == v.vendor_id
        assert staff.vendor.vendor_name == "Shop"
        assert staff.is_active is True


# ══════════════════════════════════════════════════════════════════════════════
# Password Hashing
# ══════════════════════════════════════════════════════════════════════════════

class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = _hash_password("correct-horse-battery-staple")
        assert _verify_password("correct-horse-battery-staple", hashed)
        assert not _verify_password("wrong-password", hashed)

    def test_different_hashes_same_password(self):
        h1 = _hash_password("same")
        h2 = _hash_password("same")
        assert h1 != h2  # bcrypt includes salt


# ══════════════════════════════════════════════════════════════════════════════
# Token Generation & Rotation
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenManagement:
    def test_create_access_token(self):
        token = _create_access_token(1, "vendor_owner")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # valid JWT

    def test_create_and_consume_refresh_token(self, db):
        token, jti = _create_refresh_token(1, "vendor_owner")
        assert jti is not None
        assert isinstance(token, str)

        # Store
        _store_refresh_jti(jti, 1)
        # Consume — first time succeeds
        assert _consume_refresh_jti(jti) is True
        # Second time fails (already consumed)
        assert _consume_refresh_jti(jti) is False


# ══════════════════════════════════════════════════════════════════════════════
# Registration
# ══════════════════════════════════════════════════════════════════════════════

class TestVendorRegistration:
    def test_register_new_vendor(self, db):
        owner = _create_user(db)
        result = register_vendor(
            vendor_name="Test Kitchen",
            category="food",
            owner_phone=owner.phone,
            password="secret123",
            db=db,
        )
        assert result["vendor_name"] == "Test Kitchen"
        assert result["category"] == "food"
        assert result["status"] == "pending"
        assert result["owner_id"] == owner.id

    def test_register_duplicate_vendor(self, db):
        owner = _create_user(db)
        register_vendor("Unique", "food", owner.phone, "pass", db)
        with pytest.raises(HTTPException) as exc:
            register_vendor("Duplicate", "food", owner.phone, "pass", db)
        assert exc.value.status_code == 409

    def test_register_user_not_found(self, db):
        with pytest.raises(HTTPException) as exc:
            register_vendor("Ghost", "food", "+919999999998", "pass", db)
        assert exc.value.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# Login
# ══════════════════════════════════════════════════════════════════════════════

class TestVendorLogin:
    def _setup_vendor(self, db) -> tuple[Vendor, User]:
        owner = _create_user(db)
        v = Vendor(vendor_name="Test Cafe", category="food", owner_id=owner.id,
                   password_hash=_hash_password("secret123"),
                   status=VendorStatus.ACTIVE)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v, owner

    def test_vendor_owner_login_success(self, db):
        v, _ = self._setup_vendor(db)
        result = login_as_vendor_owner(v.vendor_id, "secret123", db)
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["vendor"]["vendor_name"] == "Test Cafe"

    def test_vendor_owner_login_wrong_password(self, db):
        v, _ = self._setup_vendor(db)
        with pytest.raises(HTTPException) as exc:
            login_as_vendor_owner(v.vendor_id, "wrongpass", db)
        assert exc.value.status_code == 401

    def test_vendor_owner_login_nonexistent(self, db):
        with pytest.raises(HTTPException) as exc:
            login_as_vendor_owner(9999, "any", db)
        assert exc.value.status_code == 401

    def test_vendor_staff_login_success(self, db):
        v, _ = self._setup_vendor(db)
        staff = VendorStaff(vendor_id=v.vendor_id, name="Alice", role="staff",
                            phone="+919888888888",
                            password_hash=_hash_password("staffpass"),
                            is_active=True)
        db.add(staff)
        db.commit()

        result = login_as_vendor_staff("+919888888888", "staffpass", db)
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["vendor"]["vendor_name"] == "Test Cafe"

    def test_vendor_staff_login_inactive(self, db):
        v, _ = self._setup_vendor(db)
        staff = VendorStaff(vendor_id=v.vendor_id, name="Bob", role="staff",
                            phone="+919777777777",
                            password_hash=_hash_password("pass"),
                            is_active=False)
        db.add(staff)
        db.commit()

        with pytest.raises(HTTPException) as exc:
            login_as_vendor_staff("+919777777777", "pass", db)
        assert exc.value.status_code == 403

    def test_vendor_suspended_cannot_login(self, db):
        owner = _create_user(db)
        v = Vendor(vendor_name="Suspended Shop", category="food", owner_id=owner.id,
                   password_hash=_hash_password("pass"),
                   status=VendorStatus.SUSPENDED)
        db.add(v)
        db.commit()

        with pytest.raises(HTTPException) as exc:
            login_as_vendor_owner(v.vendor_id, "pass", db)
        assert exc.value.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# Token Refresh
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenRefresh:
    def _setup_active_vendor(self, db) -> Vendor:
        owner = _create_user(db)
        v = Vendor(vendor_name="Refresh Cafe", category="food", owner_id=owner.id,
                   password_hash=_hash_password("pass"),
                   status=VendorStatus.ACTIVE)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v

    def test_refresh_success(self, db):
        v = self._setup_active_vendor(db)
        _, refresh_token = _create_refresh_token(v.vendor_id, "vendor_owner")
        _store_refresh_jti(refresh_token.split(".")[-1], v.vendor_id)  # not needed; jti is in token

        # We need to call refresh_vendor_token but the token must be signed by our key
        from app.modules.vendors.auth_service import VENDOR_JWT_SECRET_KEY, VENDOR_JWT_ALGORITHM
        # Create a proper refresh token with JTI
        import uuid
        from datetime import timedelta
        from jose import jwt

        jti = str(uuid.uuid4())
        payload = {
            "sub": str(v.vendor_id),
            "role": "vendor_owner",
            "type": "vendor_refresh",
            "staff_id": None,
            "jti": jti,
            "exp": utcnow_naive() + timedelta(days=1),
        }
        refresh_token = jwt.encode(payload, VENDOR_JWT_SECRET_KEY, algorithm=VENDOR_JWT_ALGORITHM)
        _store_refresh_jti(jti, v.vendor_id)

        result = refresh_vendor_token(refresh_token, db)
        assert "access_token" in result
        assert "refresh_token" in result
        # Should be a different token
        assert result["refresh_token"] != refresh_token

    def test_refresh_reuse_rejected(self, db):
        v = self._setup_active_vendor(db)
        from app.modules.vendors.auth_service import VENDOR_JWT_SECRET_KEY, VENDOR_JWT_ALGORITHM
        import uuid
        from datetime import timedelta
        from jose import jwt

        jti = str(uuid.uuid4())
        payload = {
            "sub": str(v.vendor_id),
            "role": "vendor_owner",
            "type": "vendor_refresh",
            "staff_id": None,
            "jti": jti,
            "exp": utcnow_naive() + timedelta(days=1),
        }
        refresh_token = jwt.encode(payload, VENDOR_JWT_SECRET_KEY, algorithm=VENDOR_JWT_ALGORITHM)
        _store_refresh_jti(jti, v.vendor_id)

        # First use — succeeds
        refresh_vendor_token(refresh_token, db)
        # Second use — must fail
        with pytest.raises(HTTPException) as exc:
            refresh_vendor_token(refresh_token, db)
        assert exc.value.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# Auth Guard
# ══════════════════════════════════════════════════════════════════════════════

class TestGetCurrentVendor:
    def _setup_vendor(self, db) -> Vendor:
        owner = _create_user(db)
        v = Vendor(vendor_name="Guard Cafe", category="food", owner_id=owner.id,
                   password_hash=_hash_password("pass"),
                   status=VendorStatus.ACTIVE)
        db.add(v)
        db.commit()
        db.refresh(v)
        return v

    def test_valid_token_returns_context(self, db):
        v = self._setup_vendor(db)
        token = _create_access_token(v.vendor_id, "vendor_owner")
        from fastapi.security import HTTPAuthorizationCredentials

        # Mock credentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        ctx = get_current_vendor(credentials=creds, db=db)
        assert ctx["vendor_id"] == v.vendor_id
        assert ctx["role"] == "vendor_owner"
        assert ctx["staff_id"] is None

    def test_inactive_vendor_rejected(self, db):
        owner = _create_user(db)
        v = Vendor(vendor_name="Inactive", category="food", owner_id=owner.id,
                   password_hash=_hash_password("pass"),
                   status=VendorStatus.INACTIVE)
        db.add(v)
        db.commit()

        token = _create_access_token(v.vendor_id, "vendor_owner")
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc:
            get_current_vendor(credentials=creds, db=db)
        assert exc.value.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# Profile
# ══════════════════════════════════════════════════════════════════════════════

class TestVendorProfile:
    def test_get_profile(self, db):
        owner = _create_user(db)
        v = Vendor(vendor_name="Profile Cafe", category="food", owner_id=owner.id,
                   password_hash=_hash_password("pass"),
                   status=VendorStatus.ACTIVE)
        db.add(v)
        db.commit()
        db.refresh(v)

        ctx = {"vendor_id": v.vendor_id, "role": "vendor_owner", "staff_id": None}
        result = get_vendor_profile(ctx, db)
        assert result["vendor_name"] == "Profile Cafe"
        assert result["vendor_id"] == v.vendor_id

    def test_update_profile(self, db):
        owner = _create_user(db)
        v = Vendor(vendor_name="Old Name", category="stationery", owner_id=owner.id,
                   password_hash=_hash_password("pass"),
                   status=VendorStatus.ACTIVE)
        db.add(v)
        db.commit()
        db.refresh(v)

        ctx = {"vendor_id": v.vendor_id, "role": "vendor_owner", "staff_id": None}
        result = update_vendor_profile(ctx, db, vendor_name="New Name", category="food")
        assert result["vendor_name"] == "New Name"
        assert result["category"] == "food"


# ══════════════════════════════════════════════════════════════════════════════
# Staff CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestStaffCRUD:
    def _setup(self, db) -> tuple[Vendor, dict]:
        owner = _create_user(db)
        v = Vendor(vendor_name="Staff Shop", category="food", owner_id=owner.id,
                   password_hash=_hash_password("pass"),
                   status=VendorStatus.ACTIVE)
        db.add(v)
        db.commit()
        db.refresh(v)
        ctx = {"vendor_id": v.vendor_id, "role": "vendor_owner", "staff_id": None}
        return v, ctx

    def test_create_staff(self, db):
        v, ctx = self._setup(db)
        result = create_staff(ctx, db, name="John Staff", role="staff",
                              phone="+919111111111", password="staffpass")
        assert result["name"] == "John Staff"
        assert result["role"] == "staff"
        assert result["is_active"] is True

    def test_list_staff(self, db):
        v, ctx = self._setup(db)
        create_staff(ctx, db, name="Staff A", role="staff",
                     phone="+919111111111", password="pass")
        create_staff(ctx, db, name="Staff B", role="manager",
                     phone="+919222222222", password="pass")

        staff_list = list_staff(ctx, db)
        assert len(staff_list) == 2

    def test_update_staff(self, db):
        v, ctx = self._setup(db)
        created = create_staff(ctx, db, name="Original", role="staff",
                               phone="+919111111111", password="pass")

        result = update_staff(ctx, created["id"], db, name="Updated", role="manager")
        assert result["name"] == "Updated"
        assert result["role"] == "manager"

    def test_toggle_staff_active(self, db):
        v, ctx = self._setup(db)
        created = create_staff(ctx, db, name="Toggle", role="staff",
                               phone="+919111111111", password="pass")

        result = update_staff(ctx, created["id"], db, is_active=False)
        assert result["is_active"] is False

        result = update_staff(ctx, created["id"], db, is_active=True)
        assert result["is_active"] is True

    def test_delete_staff(self, db):
        v, ctx = self._setup(db)
        created = create_staff(ctx, db, name="To Delete", role="staff",
                               phone="+919111111111", password="pass")
        delete_staff(ctx, created["id"], db)

        remaining = list_staff(ctx, db)
        assert len(remaining) == 0

    def test_non_owner_cannot_manage_staff(self, db):
        ctx = {"vendor_id": 1, "role": "vendor_staff", "staff_id": 5}
        with pytest.raises(HTTPException) as exc:
            create_staff(ctx, db, name="Hacker", role="staff",
                         phone="+919111111111", password="pass")
        assert exc.value.status_code == 403
