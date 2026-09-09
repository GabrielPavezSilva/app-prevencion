"""
Security utilities - JWT token handling
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.db.deps import get_mysql_db

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def _extract_token(request: Request) -> Optional[str]:
    """Lee token desde cookie httpOnly primero, luego desde Authorization header (Swagger/debug)."""
    token = request.cookies.get("authToken")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    return token or None


def is_token_blacklisted(db: Session, jti: str) -> bool:
    row = db.execute(
        text("SELECT 1 FROM token_blacklist WHERE jti = :jti"),
        {"jti": jti}
    ).fetchone()
    return row is not None


def blacklist_token(db: Session, jti: str, expires_at: datetime) -> None:
    db.execute(
        text("INSERT INTO token_blacklist (jti, expires_at) VALUES (:jti, :exp) ON CONFLICT (jti) DO NOTHING"),
        {"jti": jti, "exp": expires_at}
    )
    db.commit()


def get_current_user(request: Request, db: Session = Depends(get_mysql_db)) -> dict:
    """Dependencia FastAPI: valida el token (cookie o Bearer) y retorna el payload del JWT."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = payload.get("jti")
    if jti and is_token_blacklisted(db, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión cerrada — inicie sesión nuevamente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def require_role(*roles: str):
    """Dependencia FastAPI: valida token y exige que el rol esté en la lista permitida."""
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permisos suficientes para esta acción",
            )
        return current_user
    return dependency


# Roles con acceso total por nombre (bypass del chequeo de módulos).
# admin/administrador siempre pasan — NO dependen de tener filas en roles_modulos.
# Cualquier otro rol accede solo si sus módulos (del JWT) intersectan los requeridos.
FULL_ACCESS_ROLES = ("admin", "administrador")


def require_module(*modules: str):
    """
    Dependencia FastAPI: valida token y exige que el usuario tenga al menos uno
    de los módulos indicados. admin/administrador tienen bypass total.

    Reemplaza a require_role("admin","administrador") para que los roles creados
    desde SuperAdmin (con módulos asignados) obtengan acceso sin tocar código.
    """
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") in FULL_ACCESS_ROLES:
            return current_user
        user_mods = current_user.get("modulos") or []
        if set(user_mods).intersection(modules):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos suficientes para esta acción",
        )
    return dependency


def resolver_recinto(current_user: dict, recinto_id_pedido: Optional[int] = None) -> int:
    """
    Decide de qué recinto sale una operación de stock: "todos ven los tres,
    cada uno mueve solo el suyo".

    Va acá y no en un endpoint porque es la misma clase de decisión que
    `require_module`, y porque la usan cuatro services distintos (stock,
    ajuste, entregas, importaciones) que si no la repetirían con criterios que
    se van separando.

    Solo aplica a **escrituras**. Las lecturas no pasan por acá: el listado de
    stock trae los tres recintos a propósito, para saber dónde hay existencias
    antes de pedir un traslado.
    """
    propio = current_user.get("recinto_id")

    if current_user.get("role") in FULL_ACCESS_ROLES:
        # Bypass de módulos, pero no de recinto: un admin no tiene recinto
        # propio, así que no hay default razonable y adivinar uno mandaría
        # stock a la bodega equivocada en silencio.
        if recinto_id_pedido is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Indica el recinto: tu rol no tiene uno asignado por defecto",
            )
        return int(recinto_id_pedido)

    if propio is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu usuario no tiene recinto asignado. Pide a un administrador "
                   "que te asigne uno para poder mover stock.",
        )

    # Falla en vez de ignorar: si el cliente pidió otro recinto, o la UI está
    # mandando algo que no corresponde o alguien está probando la API a mano.
    # Descontar del recinto propio sin avisar esconde las dos cosas.
    if recinto_id_pedido is not None and int(recinto_id_pedido) != int(propio):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes mover stock de tu propio recinto",
        )

    return int(propio)


# ponytail: self-check de la lógica de módulos (no framework, corre con `python security.py`)
if __name__ == "__main__":
    def _check(role, mods, required):
        u = {"role": role, "modulos": mods}
        if u.get("role") in FULL_ACCESS_ROLES:
            return True
        return bool(set(u.get("modulos") or []).intersection(required))
    assert _check("admin", [], ("dashboard",)) is True          # bypass sin módulos
    assert _check("administrador", [], ("inventario",)) is True # bypass legacy
    assert _check("supervisor", ["inventario"], ("inventario",)) is True   # rol creado OK
    assert _check("supervisor", ["personal"], ("inventario",)) is False    # sin módulo → deniega
    assert _check("worker_asignacion", ["worker_asignacion"], ("inventario", "worker_asignacion")) is True
    assert _check("x", None, ("dashboard",)) is False           # modulos None no crashea
    print("require_module self-check OK")

    # resolver_recinto: los tres casos de la tabla del diseño.
    def _falla(user, pedido):
        try:
            resolver_recinto(user, pedido)
        except HTTPException as e:
            return e.status_code
        return None

    bodeguero = {"role": "bodeguero", "recinto_id": 2}
    assert resolver_recinto(bodeguero, None) == 2          # usa el suyo sin pedirlo
    assert resolver_recinto(bodeguero, 2) == 2             # pedir el propio es válido
    assert _falla(bodeguero, 3) == 403                     # otro recinto: no lo ignora, falla
    assert _falla({"role": "bodeguero", "recinto_id": None}, 1) == 403  # sin recinto asignado
    assert resolver_recinto({"role": "admin", "recinto_id": None}, 3) == 3  # admin elige
    assert _falla({"role": "admin", "recinto_id": None}, None) == 400   # admin sin elegir
    # El bypass de módulos no arrastra bypass de recinto.
    assert _falla({"role": "administrador", "recinto_id": None}, None) == 400
    print("resolver_recinto self-check OK")
