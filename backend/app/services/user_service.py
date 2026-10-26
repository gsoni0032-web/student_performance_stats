"""User administration."""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, conflict, not_found
from app.core.security import hash_password
from app.models import Class, TeacherClass, User
from app.models.enums import Role
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserOut, UserUpdate


def to_out(session: Session, user: User) -> UserOut:
    """Serialise a user together with the ids of their assigned classes."""
    class_ids = list(
        session.scalars(select(TeacherClass.class_id).where(TeacherClass.teacher_id == user.id))
    )
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,  # type: ignore[arg-type]
        is_active=user.is_active,
        created_at=user.created_at,
        class_ids=sorted(class_ids),
    )


def _set_classes(session: Session, user: User, class_ids: list[int]) -> None:
    unique_ids = sorted(set(class_ids))
    if unique_ids:
        found = set(session.scalars(select(Class.id).where(Class.id.in_(unique_ids))))
        missing = [cid for cid in unique_ids if cid not in found]
        if missing:
            raise bad_request(f"Unknown class id(s): {', '.join(map(str, missing))}")
    session.execute(delete(TeacherClass).where(TeacherClass.teacher_id == user.id))
    session.add_all([TeacherClass(teacher_id=user.id, class_id=cid) for cid in unique_ids])


def _active_admin_count(session: Session) -> int:
    return session.scalar(
        select(func.count(User.id)).where(User.role == Role.ADMIN.value, User.is_active.is_(True))
    ) or 0


def list_users(session: Session, page: int, page_size: int, search: str | None) -> Page[UserOut]:
    """Paginated users, optionally filtered by name or email."""
    conditions = []
    if search:
        pattern = f"%{search.lower()}%"
        conditions.append(func.lower(User.name).like(pattern) | func.lower(User.email).like(pattern))
    total = session.scalar(select(func.count(User.id)).where(*conditions)) or 0
    users = session.scalars(
        select(User).where(*conditions).order_by(User.name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page.of([to_out(session, u) for u in users], total, page, page_size)


def get_user(session: Session, user_id: int) -> User:
    """Fetch a user or raise 404."""
    user = session.get(User, user_id)
    if user is None:
        raise not_found("User")
    return user


def create_user(session: Session, payload: UserCreate) -> UserOut:
    """Create an account; emails are unique and stored lower-case."""
    email = payload.email.lower()
    if session.scalar(select(User.id).where(User.email == email)) is not None:
        raise conflict("An account with this email already exists")
    user = User(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    session.flush()
    if payload.role == Role.TEACHER.value:
        _set_classes(session, user, payload.class_ids)
    session.commit()
    return to_out(session, user)


def update_user(session: Session, acting: User, user_id: int, payload: UserUpdate) -> UserOut:
    """Update an account, never leaving the system without an active administrator."""
    user = get_user(session, user_id)
    demoting = payload.role is not None and payload.role != Role.ADMIN.value
    deactivating = payload.is_active is False
    if user.role == Role.ADMIN.value and user.is_active and (demoting or deactivating):
        if user.id == acting.id:
            raise conflict("You cannot remove your own administrator access or deactivate yourself")
        if _active_admin_count(session) <= 1:
            raise conflict("At least one active administrator is required")
    if payload.name is not None:
        user.name = payload.name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.class_ids is not None:
        _set_classes(session, user, payload.class_ids if user.role == Role.TEACHER.value else [])
    session.commit()
    return to_out(session, user)


def delete_user(session: Session, acting: User, user_id: int) -> None:
    """Delete an account (not your own, and not the last administrator)."""
    user = get_user(session, user_id)
    if user.id == acting.id:
        raise conflict("You cannot delete your own account")
    if user.role == Role.ADMIN.value and user.is_active and _active_admin_count(session) <= 1:
        raise conflict("At least one active administrator is required")
    session.delete(user)
    session.commit()
