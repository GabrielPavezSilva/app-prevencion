"""
Sincronización de `personal` desde RRHH — entrada por línea de comandos.

La usa el scheduler (Ofelia) a diario; llama al mismo service que el endpoint
`POST /api/personal/sync`, sin HTTP interno ni token.

Ejecutar:
    python sync_personal.py             # sincroniza
    python sync_personal.py --dry-run   # calcula y revierte, no escribe

Sale con código 1 si la corrida falla (para que el scheduler lo marque en rojo).
"""
import argparse
import sys

from app.core.logging_config import logger
from app.db.session import SessionLocal
from app.services.personal_sync_service import PersonalSyncService


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza personal desde la base de RRHH")
    parser.add_argument("--dry-run", action="store_true",
                        help="calcula el resultado sin escribir")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        resumen = PersonalSyncService(db).sincronizar(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Sync de personal FALLÓ: {type(e).__name__}: {e}")
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(
        f"Sync {'(dry-run) ' if resumen['dry_run'] else ''}OK — "
        f"leídos: {resumen['leidos']}, creados: {resumen['creados']}, "
        f"actualizados: {resumen['actualizados']}, sin cambios: {resumen['sin_cambios']}, "
        f"desactivados: {resumen['desactivados']}, errores: {len(resumen['errores'])}"
    )
    for err in resumen["errores"][:20]:
        print(f"  - {err}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
