-- Migración: añade catálogos secciones + temporadas y los vincula a lecturas_rfid.
-- IMPORTANTE: vacía lecturas_rfid y asignaciones (datos de prueba sin valor) para poder
-- agregar las nuevas columnas como NOT NULL sin backfill ambiguo.
-- Ejecutar UNA SOLA VEZ contra la base de datos PostgreSQL.

BEGIN;

-- 1) Vaciar tablas dependientes (orden importa por FKs)
TRUNCATE TABLE asignaciones RESTART IDENTITY CASCADE;
TRUNCATE TABLE lecturas_rfid RESTART IDENTITY CASCADE;

-- 2) Crear catálogos nuevos
CREATE TABLE IF NOT EXISTS secciones (
    seccion_id     SERIAL PRIMARY KEY,
    nombre_seccion VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS temporadas (
    temporada_id     SERIAL PRIMARY KEY,
    nombre_temporada VARCHAR(50) NOT NULL UNIQUE
);

-- 3) Añadir columnas a lecturas_rfid (NOT NULL, FK)
ALTER TABLE lecturas_rfid
    ADD COLUMN IF NOT EXISTS seccion_id   INT NOT NULL REFERENCES secciones(seccion_id),
    ADD COLUMN IF NOT EXISTS temporada_id INT NOT NULL REFERENCES temporadas(temporada_id);

COMMIT;
