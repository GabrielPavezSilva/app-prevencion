-- Stock de EPP por recinto (Las Encinas, Lucerna, Malloco).
-- Diseño: docs/plans/2026-09-09-stock-por-recinto-design.md
--
-- No hay sistema de migraciones: esto se corre a mano, una vez por ambiente.
-- `create_all` crea tablas que faltan pero NUNCA agrega columnas a una tabla
-- existente, así que el modelo ORM no basta.
--
--   docker compose exec -it postgres psql -U prevencion -d db_prevencion \
--       -f /migrations/2026-09-09_stock_por_recinto.sql
--
-- ── ADVERTENCIA ──────────────────────────────────────────────────────────────
-- El paso 1 BORRA todo el dominio EPP: stock, movimientos, entregas y actas.
-- Es deliberado (decisión D5 del diseño): lo cargado era de prueba y el stock
-- existente no tenía recinto al que atribuirse. En un ambiente con datos
-- reales, NO correr el paso 1 sin decidir antes a qué recinto va cada fila.
-- ─────────────────────────────────────────────────────────────────────────────

BEGIN;

-- 1. Borrón del dominio EPP. Hijos antes que padres.
--    `entregas_epp.entrega_reemplazada_id` es autorreferencial, pero un DELETE
--    de la tabla completa no necesita orden interno.
DELETE FROM actas_entrega;
DELETE FROM entregas_epp;
DELETE FROM movimientos_stock;
DELETE FROM stock_epp;

-- 2. Recintos. Sin CRUD: un cuarto recinto es un INSERT acá.
CREATE TABLE IF NOT EXISTS recintos (
    recinto_id     SERIAL PRIMARY KEY,
    nombre_recinto VARCHAR(60) NOT NULL UNIQUE,
    activo         BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO recintos (nombre_recinto) VALUES
    ('Las Encinas'), ('Lucerna'), ('Malloco')
ON CONFLICT (nombre_recinto) DO NOTHING;

-- 3. Columnas nuevas. Las tres primeras tablas quedaron vacías en el paso 1,
--    así que NOT NULL entra sin necesidad de un default que después habría que
--    quitar. `usuarios.recinto_id` es NULL a propósito: los roles de
--    FULL_ACCESS_ROLES no tienen recinto y eligen el suyo en cada operación.
ALTER TABLE stock_epp         ADD COLUMN recinto_id INTEGER NOT NULL REFERENCES recintos(recinto_id);
ALTER TABLE movimientos_stock ADD COLUMN recinto_id INTEGER NOT NULL REFERENCES recintos(recinto_id);
ALTER TABLE entregas_epp      ADD COLUMN recinto_id INTEGER NOT NULL REFERENCES recintos(recinto_id);
ALTER TABLE usuarios          ADD COLUMN recinto_id INTEGER          REFERENCES recintos(recinto_id);

-- 4. La identidad de una fila de stock pasa a ser (producto, talla, recinto):
--    el mismo casco talla L tiene que poder existir en los tres recintos.
ALTER TABLE stock_epp DROP CONSTRAINT uq_stock_producto_talla;
ALTER TABLE stock_epp ADD  CONSTRAINT uq_stock_producto_talla_recinto
    UNIQUE (producto_id, talla_id, recinto_id);

-- 5. El listado de stock filtra y ordena por recinto en cada carga.
CREATE INDEX IF NOT EXISTS ix_stock_epp_recinto        ON stock_epp (recinto_id);
CREATE INDEX IF NOT EXISTS ix_movimientos_stock_recinto ON movimientos_stock (recinto_id);
CREATE INDEX IF NOT EXISTS ix_entregas_epp_recinto      ON entregas_epp (recinto_id);

COMMIT;

-- Verificación:
--   SELECT * FROM recintos;
--   \d stock_epp
--   SELECT count(*) FROM stock_epp;   -- 0
