-- Migración: agregar columna uuid para idempotencia offline
-- Ejecutar una sola vez sobre DBs existentes.
-- Las tablas nuevas ya reciben la columna vía Base.metadata.create_all al iniciar el backend.
--
-- Para DBs en producción (VPS) ejecutar:
--   docker compose exec backend psql -U lavanderia -d db_lavanderia -f /app/migrations/add_uuid_to_tables.sql
--
-- Para DBs locales:
--   psql -U <usuario> -d <nombre_db> -f add_uuid_to_tables.sql

-- Inventario: cada prenda puede tener un UUID de la operación que la creó
ALTER TABLE lecturas_rfid
    ADD COLUMN IF NOT EXISTS uuid VARCHAR(36);

CREATE UNIQUE INDEX IF NOT EXISTS ix_lecturas_rfid_uuid
    ON lecturas_rfid (uuid)
    WHERE uuid IS NOT NULL;

-- Asignaciones: cada asignación puede tener un UUID de la operación que la originó
ALTER TABLE asignaciones
    ADD COLUMN IF NOT EXISTS uuid VARCHAR(36);

CREATE UNIQUE INDEX IF NOT EXISTS ix_asignaciones_uuid
    ON asignaciones (uuid)
    WHERE uuid IS NOT NULL;
