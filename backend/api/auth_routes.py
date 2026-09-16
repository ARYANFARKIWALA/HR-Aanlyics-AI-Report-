"""Authentication and Authorization API routes (Module 11)."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.authorization import (
    DEFAULT_ROLE_PERMISSIONS,
    SYSTEM_PERMISSIONS,
)
from ..auth.dependencies import get_current_user, require_permission, require_role
from ..auth.jwt_handler import create_access_token
from ..auth.password import hash_password, validate_password_strength, verify_password
from ..auth.security_audit import SecurityAuditService
from ..auth.sessions import SessionManager
from ..database.connection import get_db
from ..database.models import User
from ..database.models_auth import (
    ColumnPermission,
    Permission,
    Role,
    RolePermission,
    RowAccessRule,
    SecurityAuditLog,
    UserDatabaseAccess,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication & Authorization"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    session_token: str | None = None
    user_id: int
    username: str
    full_name: str
    role: str
    department_id: int | None = None
    permissions: list[str] = []


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "hr_analyst"
    department_id: int | None = None


class DatabaseAccessRequest(BaseModel):
    user_id: int
    database_id: str
    can_read: bool = True
    can_write: bool = False
    can_execute: bool = True


class ColumnPermissionRequest(BaseModel):
    database_id: str
    table_name: str
    column_name: str
    role_id: int | None = None
    user_id: int | None = None
    is_allowed: bool = True
    is_masked: bool = False
    mask_type: str = "partial"


class RowAccessRuleRequest(BaseModel):
    database_id: str
    table_name: str
    filter_expression: str
    description: str | None = None
    role_id: int | None = None
    user_id: int | None = None


@router.post("/login", response_model=TokenResponse)
def login(creds: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticates user, checks lockout, and generates JWT and server-side session."""
    user = db.query(User).filter(User.username == creds.username).first()
    client_ip = request.client.host if request.client else "127.0.0.1"

    if not user:
        SecurityAuditService.log_event(
            db=db,
            event_type="LOGIN_FAILURE",
            status="FAILURE",
            username=creds.username,
            ip_address=client_ip,
            details={"reason": "User not found"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # 1. Check account lockout
    locked, remaining_seconds = SessionManager.is_account_locked(user)
    if locked:
        SecurityAuditService.log_event(
            db=db,
            event_type="LOGIN_ATTEMPT_WHILE_LOCKED",
            status="BLOCKED",
            user_id=user.id,
            username=user.username,
            ip_address=client_ip,
            details={"remaining_seconds": remaining_seconds}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked due to repeated failed logins. Try again in {remaining_seconds} seconds."
        )

    # 2. Check active status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account has been deactivated."
        )

    # 3. Verify password
    if not verify_password(creds.password, user.hashed_password):
        is_locked_now, msg = SessionManager.record_login_failure(db, user, ip_address=client_ip)
        if is_locked_now:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)

    # 4. Login success: create server session
    user_agent = request.headers.get("user-agent", "Unknown")
    session = SessionManager.record_login_success(db, user, ip_address=client_ip, user_agent=user_agent)

    # Resolve permissions
    permissions = []
    if user.role == "admin":
        permissions = [p[0] for p in SYSTEM_PERMISSIONS]
    else:
        role = db.query(Role).filter(Role.name == user.role).first()
        if role:
            rps = db.query(RolePermission).join(Permission).filter(RolePermission.role_id == role.id).all()
            permissions = [rp.permission.code for rp in rps]
        if not permissions:
            permissions = list(DEFAULT_ROLE_PERMISSIONS.get(user.role, []))

    token = create_access_token(data={
        "sub": user.username,
        "role": user.role,
        "id": user.id,
        "session_token": session.session_token
    })

    return TokenResponse(
        access_token=token,
        session_token=session.session_token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        department_id=user.department_id,
        permissions=permissions
    )


@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes active server-side session."""
    session_token = request.headers.get("X-Session-Token")
    if session_token:
        SessionManager.revoke_session(db, session_token)
    SecurityAuditService.log_event(
        db=db,
        event_type="LOGOUT",
        status="SUCCESS",
        user_id=current_user.id,
        username=current_user.username
    )
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns current user profile, assigned capabilities, and database access."""
    # Resolve permissions
    if current_user.role == "admin":
        perms = [p[0] for p in SYSTEM_PERMISSIONS]
    else:
        role = db.query(Role).filter(Role.name == current_user.role).first()
        if role:
            rps = db.query(RolePermission).join(Permission).filter(RolePermission.role_id == role.id).all()
            perms = [rp.permission.code for rp in rps]
        else:
            perms = list(DEFAULT_ROLE_PERMISSIONS.get(current_user.role, []))

    # Accessible databases
    db_access = []
    if current_user.role == "admin":
        db_access = ["*"]
    else:
        grants = db.query(UserDatabaseAccess).filter(UserDatabaseAccess.user_id == current_user.id).all()
        db_access = [g.database_id for g in grants]
        if "sqlite_hr_default" not in db_access:
            db_access.append("sqlite_hr_default")

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "department_id": current_user.department_id,
        "is_active": current_user.is_active,
        "permissions": perms,
        "databases": db_access
    }


@router.get("/users")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all users (Requires admin or manager role)."""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    users = db.query(User).all()
    results = []
    for u in users:
        locked, sec = SessionManager.is_account_locked(u)
        results.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "department_id": u.department_id,
            "is_active": u.is_active,
            "is_locked": locked,
            "lockout_remaining_seconds": sec,
            "failed_login_attempts": u.failed_login_attempts,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })
    return {"users": results}


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(
    req: CreateUserRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Admin creates a new user with password policy check."""
    # Check if username/email exists
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    is_valid, msg = validate_password_strength(req.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Weak password: {msg}")

    new_user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=req.role,
        department_id=req.department_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    SecurityAuditService.log_event(
        db=db,
        event_type="USER_CREATED",
        status="SUCCESS",
        user_id=current_user.id,
        username=current_user.username,
        details={"created_user_id": new_user.id, "created_username": new_user.username, "role": new_user.role}
    )

    return {"message": "User created successfully", "user_id": new_user.id, "username": new_user.username}


@router.post("/users/{user_id}/unlock")
def unlock_user(
    user_id: int,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Admin manually clears lockout for a user."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.failed_login_attempts = 0
    target_user.locked_until = None
    db.commit()

    SecurityAuditService.log_event(
        db=db,
        event_type="ACCOUNT_UNLOCKED",
        status="SUCCESS",
        user_id=current_user.id,
        username=current_user.username,
        details={"unlocked_user_id": target_user.id, "unlocked_username": target_user.username}
    )
    return {"message": f"Account for {target_user.username} unlocked successfully."}


@router.get("/roles")
def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists roles and associated permissions."""
    roles = db.query(Role).all()
    results = []
    for r in roles:
        perms = [rp.permission.code for rp in r.permissions]
        results.append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
            "permissions": perms
        })
    return {"roles": results}


@router.get("/permissions")
def list_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all available system permissions."""
    perms = db.query(Permission).all()
    return {
        "permissions": [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "category": p.category,
                "description": p.description
            }
            for p in perms
        ]
    }


@router.get("/database-access")
def list_database_access(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Lists explicit database access rules."""
    grants = db.query(UserDatabaseAccess).all()
    return {
        "database_access": [
            {
                "id": g.id,
                "user_id": g.user_id,
                "database_id": g.database_id,
                "can_read": g.can_read,
                "can_write": g.can_write,
                "can_execute": g.can_execute,
                "granted_by": g.granted_by,
                "granted_at": g.granted_at.isoformat() if g.granted_at else None
            }
            for g in grants
        ]
    }


@router.post("/database-access")
def grant_database_access(
    req: DatabaseAccessRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Grants or updates user database access."""
    existing = db.query(UserDatabaseAccess).filter(
        UserDatabaseAccess.user_id == req.user_id,
        UserDatabaseAccess.database_id == req.database_id
    ).first()

    if existing:
        existing.can_read = req.can_read
        existing.can_write = req.can_write
        existing.can_execute = req.can_execute
        existing.granted_by = current_user.username
        existing.granted_at = datetime.datetime.now(datetime.UTC)
    else:
        new_grant = UserDatabaseAccess(
            user_id=req.user_id,
            database_id=req.database_id,
            can_read=req.can_read,
            can_write=req.can_write,
            can_execute=req.can_execute,
            granted_by=current_user.username
        )
        db.add(new_grant)

    db.commit()
    SecurityAuditService.log_event(
        db=db,
        event_type="DATABASE_ACCESS_GRANTED",
        status="SUCCESS",
        user_id=current_user.id,
        username=current_user.username,
        details=req.dict()
    )
    return {"message": "Database access updated successfully"}


@router.get("/column-permissions")
def list_column_permissions(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Lists column-level security and masking policies."""
    rules = db.query(ColumnPermission).all()
    return {
        "column_permissions": [
            {
                "id": r.id,
                "role_id": r.role_id,
                "user_id": r.user_id,
                "database_id": r.database_id,
                "table_name": r.table_name,
                "column_name": r.column_name,
                "is_allowed": r.is_allowed,
                "is_masked": r.is_masked,
                "mask_type": r.mask_type
            }
            for r in rules
        ]
    }


@router.post("/column-permissions")
def create_column_permission(
    req: ColumnPermissionRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Configures column-level security rule."""
    cp = ColumnPermission(
        database_id=req.database_id,
        table_name=req.table_name,
        column_name=req.column_name,
        role_id=req.role_id,
        user_id=req.user_id,
        is_allowed=req.is_allowed,
        is_masked=req.is_masked,
        mask_type=req.mask_type
    )
    db.add(cp)
    db.commit()
    return {"message": "Column permission rule created", "id": cp.id}


@router.get("/row-rules")
def list_row_rules(
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Lists row-level security predicates."""
    rules = db.query(RowAccessRule).all()
    return {
        "row_rules": [
            {
                "id": r.id,
                "role_id": r.role_id,
                "user_id": r.user_id,
                "database_id": r.database_id,
                "table_name": r.table_name,
                "filter_expression": r.filter_expression,
                "description": r.description,
                "is_active": r.is_active
            }
            for r in rules
        ]
    }


@router.post("/row-rules")
def create_row_rule(
    req: RowAccessRuleRequest,
    current_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Configures a row-level security predicate."""
    rule = RowAccessRule(
        database_id=req.database_id,
        table_name=req.table_name,
        filter_expression=req.filter_expression,
        description=req.description,
        role_id=req.role_id,
        user_id=req.user_id,
        is_active=True
    )
    db.add(rule)
    db.commit()
    return {"message": "Row access rule created", "id": rule.id}


@router.get("/audit")
def get_security_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_permission("admin:audit")),
    db: Session = Depends(get_db)
):
    """Returns security audit event trail."""
    logs = db.query(SecurityAuditLog).order_by(SecurityAuditLog.created_at.desc()).limit(limit).all()
    return {
        "audit_logs": [
            {
                "id": l.id,
                "event_type": l.event_type,
                "user_id": l.user_id,
                "username": l.username,
                "ip_address": l.ip_address,
                "status": l.status,
                "details": l.details,
                "created_at": l.created_at.isoformat() if l.created_at else None
            }
            for l in logs
        ]
    }
