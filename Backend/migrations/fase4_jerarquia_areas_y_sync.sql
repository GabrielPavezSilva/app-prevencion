-- ============================================================================
-- Fase 4 — Jerarquía real de catálogos organizacionales + soporte de sync
--
-- `Base.metadata.create_all` NO altera tablas existentes: esta migración es
-- necesaria en cualquier base creada antes de la Fase 4 (dev local, staging).
-- En una base nueva no hace falta — el modelo ya la refleja.
--
-- Motivo: en la fuente (rh_cramer) los nombres de área y subárea se repiten
-- entre empresas ("Administración" existe en 4 empresas; la subárea
-- "Ventas Fragancias" cuelga de 5 pares empresa+área). Con el UNIQUE viejo
-- sobre el nombre solo, esas unidades se fusionaban y el reporte por área
-- sumaba empresas distintas.
--
-- Idempotente: seguro re-ejecutar.
-- Ejecutar:  psql -d db_prevencion -f fase4_jerarquia_areas_y_sync.sql
-- ============================================================================

BEGIN;

-- ── empresa ────────────────────────────────────────────────────────────────
ALTER TABLE empresa ADD COLUMN IF NOT EXISTS origen_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'empresa_origen_id_key'
    ) THEN
        ALTER TABLE empresa ADD CONSTRAINT empresa_origen_id_key UNIQUE (origen_id);
    END IF;
END $$;

-- ── areas ──────────────────────────────────────────────────────────────────
ALTER TABLE areas ADD COLUMN IF NOT EXISTS empresa_id INTEGER;
ALTER TABLE areas ADD COLUMN IF NOT EXISTS origen_id  INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'areas_empresa_id_fkey'
    ) THEN
        ALTER TABLE areas
            ADD CONSTRAINT areas_empresa_id_fkey
            FOREIGN KEY (empresa_id) REFERENCES empresa(empresa_id);
    END IF;
END $$;

-- El UNIQUE viejo sobre el nombre solo es justamente lo que hay que soltar.
ALTER TABLE areas DROP CONSTRAINT IF EXISTS areas_nombre_area_key;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_areas_nombre_empresa'
    ) THEN
        ALTER TABLE areas
            ADD CONSTRAINT uq_areas_nombre_empresa UNIQUE (nombre_area, empresa_id);
    END IF;
END $$;

-- ── subareas ───────────────────────────────────────────────────────────────
ALTER TABLE subareas ADD COLUMN IF NOT EXISTS area_id   INTEGER;
ALTER TABLE subareas ADD COLUMN IF NOT EXISTS origen_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'subareas_area_id_fkey'
    ) THEN
        ALTER TABLE subareas
            ADD CONSTRAINT subareas_area_id_fkey
            FOREIGN KEY (area_id) REFERENCES areas(area_id);
    END IF;
END $$;

ALTER TABLE subareas DROP CONSTRAINT IF EXISTS subareas_nombre_subarea_key;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_subareas_nombre_area'
    ) THEN
        ALTER TABLE subareas
            ADD CONSTRAINT uq_subareas_nombre_area UNIQUE (nombre_subarea, area_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'subareas_origen_id_key'
    ) THEN
        ALTER TABLE subareas ADD CONSTRAINT subareas_origen_id_key UNIQUE (origen_id);
    END IF;
END $$;

-- ── personal ───────────────────────────────────────────────────────────────
-- `rh.employees.name_role` llega a 59 caracteres; la columna era VARCHAR(50).
ALTER TABLE personal ALTER COLUMN cargo TYPE VARCHAR(100);

-- Columnas de trazabilidad del sync (por si la base es anterior a la Fase 1).
ALTER TABLE personal ADD COLUMN IF NOT EXISTS buk_id  INTEGER;
ALTER TABLE personal ADD COLUMN IF NOT EXISTS sync_at TIMESTAMP;
ALTER TABLE personal ADD COLUMN IF NOT EXISTS activo  BOOLEAN DEFAULT TRUE;

COMMIT;
