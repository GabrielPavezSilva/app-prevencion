"""
DAG: backup_lavanderia_db
Descripción: Backup diario de la BD PostgreSQL de lavandería.
             Guarda el dump comprimido en /opt/airflow/backups/lavanderia/
             y elimina backups con más de 30 días.

Requisitos previos:
  1. El contenedor de Airflow debe estar conectado a la red Docker 'lavanderia_network'.
  2. pg_dump disponible en el contenedor de Airflow
     (instalar con: apt-get install -y postgresql-client).
  3. Airflow Connection configurada:
       Conn Id:   lavanderia_postgres
       Conn Type: Postgres
       Host:      postgres
       Schema:    db_lavanderia
       Login:     lavanderia
       Password:  <POSTGRES_PASSWORD del .env>
       Port:      5432
  4. Carpeta de backups montada en el contenedor de Airflow:
       volumes:
         - /opt/airflow/backups:/opt/airflow/backups
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.hooks.base import BaseHook
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

BACKUP_DIR = "/opt/airflow/backups/lavanderia"
RETENTION_DAYS = 30
CONN_ID = "lavanderia_postgres"

default_args = {
    "owner": "airflow",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def get_pg_dump_command() -> str:
    """Construye el comando pg_dump leyendo la Connection de Airflow."""
    conn = BaseHook.get_connection(CONN_ID)
    timestamp = "$(date +%Y%m%d_%H%M%S)"
    filename = f"db_lavanderia_{timestamp}.sql.gz"
    return (
        f"mkdir -p {BACKUP_DIR} && "
        f"PGPASSWORD='{conn.password}' pg_dump "
        f"-h {conn.host} "
        f"-p {conn.port or 5432} "
        f"-U {conn.login} "
        f"-d {conn.schema} "
        f"| gzip > {BACKUP_DIR}/{filename} && "
        f"echo \"Backup completado: {filename}\" && "
        f"du -h {BACKUP_DIR}/{filename}"
    )


def purge_old_backups():
    """Elimina backups con más de RETENTION_DAYS días."""
    backup_path = Path(BACKUP_DIR)
    if not backup_path.exists():
        return
    cutoff = datetime.now().timestamp() - (RETENTION_DAYS * 86400)
    deleted = []
    for f in backup_path.glob("db_lavanderia_*.sql.gz"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            deleted.append(f.name)
    if deleted:
        print(f"Eliminados {len(deleted)} backups antiguos: {deleted}")
    else:
        print("No hay backups antiguos para eliminar.")


with DAG(
    dag_id="backup_lavanderia_db",
    default_args=default_args,
    description="Backup diario de PostgreSQL — lavandería",
    schedule="0 3 * * *",  # Todos los días a las 3:00 AM
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["backup", "lavanderia", "postgres"],
) as dag:

    hacer_backup = BashOperator(
        task_id="pg_dump",
        bash_command="{{ task_instance.xcom_pull(task_ids='build_command') }}",
        do_xcom_push=False,
    )

    build_cmd = PythonOperator(
        task_id="build_command",
        python_callable=get_pg_dump_command,
        do_xcom_push=True,
    )

    limpiar_viejos = PythonOperator(
        task_id="purge_old_backups",
        python_callable=purge_old_backups,
    )

    build_cmd >> hacer_backup >> limpiar_viejos
