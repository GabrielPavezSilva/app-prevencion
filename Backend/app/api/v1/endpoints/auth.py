from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth_service import AuthService
from app.db.deps import get_mysql_db
from app.core.config import settings
from app.core.security import decode_token, blacklist_token

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_COOKIE_MAX_AGE = settings.JWT_EXPIRE_MINUTES * 60  # segundos
_IS_PROD = settings.ENVIRONMENT == "production"


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, response: Response, db: Session = Depends(get_mysql_db)):
    """
    Autenticación de usuario. Setea cookie httpOnly con el JWT.
    """
    try:
        service = AuthService(db)
        result = service.authenticate_user(body.username, body.contrasena)
        response.set_cookie(
            key="authToken",
            value=result.token,
            httponly=True,
            secure=_IS_PROD,
            samesite="strict",
            max_age=_COOKIE_MAX_AGE,
            path="/",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_mysql_db)):
    """
    Logout de usuario. Invalida el token en DB y limpia la cookie.
    """
    token = request.cookies.get("authToken")
    if token:
        payload = decode_token(token)
        if payload:
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                blacklist_token(db, jti, datetime.utcfromtimestamp(exp))
    response.delete_cookie(key="authToken", path="/", httponly=True, samesite="strict")
    return {"message": "Sesión cerrada correctamente"}
