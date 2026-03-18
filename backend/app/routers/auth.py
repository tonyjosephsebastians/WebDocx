from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models import Membership, User
from app.schemas.auth import LoginRequest, MessageResponse, RegisterRequest, TokenResponse
from app.services.documents import build_auth_user, create_workspace_for_user


router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _user_with_workspaces_query():
    return select(User).options(joinedload(User.memberships).joinedload(Membership.workspace))


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
    user = db.scalar(_user_with_workspaces_query().where(User.id == payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    workspace_name = payload.workspace_name.strip() if payload.workspace_name else f"{payload.name.split()[0]}'s workspace"
    create_workspace_for_user(db, user, workspace_name)
    db.commit()
    user = db.scalar(_user_with_workspaces_query().where(User.id == user.id))
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=build_auth_user(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(_user_with_workspaces_query().where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=build_auth_user(user))


@router.post("/logout", response_model=MessageResponse)
def logout() -> MessageResponse:
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=TokenResponse)
def me(current_user: User = Depends(get_current_user)) -> TokenResponse:
    token = create_access_token(current_user.id)
    return TokenResponse(access_token=token, user=build_auth_user(current_user))
