from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.app.base.utils.db import get_db
from src.app.user import crud, schemas
from src.config import settings
from src.config.social_app import oauth
from .jwt import create_access_token
from .schemas import Token, Msg, VerificationInDB
from .security import get_password_hash
from .send_email import send_reset_password_email
from .service import (
    registration_user,
    verify_registration_user,
    generate_password_reset_token,
    verify_password_reset_token,
)

auth_router = APIRouter()


@auth_router.route('/github-login')
async def login(request: Request):
    github = oauth.create_client("github")
    redirect_uri = request.url_for("authorize_github")
    return await github.authorize_redirect(request, redirect_uri)


@auth_router.route('/github-auth')
async def authorize_github(request: Request):
    token = await oauth.github.authorize_access_token(request)
    resp = await oauth.github.get("user", token=token)
    profile = resp.json()
    return JSONResponse(profile)


@auth_router.post('/login/access-token', response_model=Token)
def login_access_token(
        db: Session = Depends(get_db),
        form_data: OAuth2PasswordRequestForm = Depends()
):
    user = crud.user.authenticate(
        db,
        username=form_data.username,
        password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400,
                            detail="Incorrect username or password")
    elif not crud.user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            data={"user_id": user.id}, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@auth_router.post("/registration", response_model=Msg)
def user_registration(
        new_user: schemas.UserCreateInRegistration,
        db: Session = Depends(get_db)
):
    user_exists = registration_user(new_user, db)
    if user_exists:
        raise HTTPException(status_code=400, detail="User already exists")
    return {"msg": "Send email"}


@auth_router.post("/confirm-email", response_model=Msg)
def confirm_email(uuid: VerificationInDB, db: Session = Depends(get_db)):
    if not verify_registration_user(uuid, db):
        raise HTTPException(status_code=404, detail="Not found")
    return {"msg": "Success verify email"}


@auth_router.post("/password-recovery/{email}", response_model=Msg)
def recover_password(email: str, db: Session = Depends(get_db)):
    user = crud.user.get(db, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    send_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    return {"msg": "Password recovery email sent"}


@auth_router.post("/reset-password/", response_model=Msg)
def reset_password(
        token: str = Body(...),
        new_password: str = Body(...),
        db: Session = Depends(get_db)
):
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.user.get(db, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    elif not crud.user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    crud.user.change_password(db, user, new_password)
    return {"msg": "Password updated successfully"}
