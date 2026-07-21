-- ============================================================
-- Seed de datos de prueba — Sistema Lavandería Industrial
-- Ejecutar contra db_lavanderia
-- Usa INSERT IGNORE para ser idempotente (seguro de re-ejecutar)
-- ============================================================

USE db_lavanderia;

-- ------------------------------------------------------------
-- Tipos de prenda (5 categorías)
-- ------------------------------------------------------------
INSERT INTO tiposPrendas (nombre_tipo) VALUES
    ('Camisa'),
    ('Pantalón'),
    ('Chaqueta'),
    ('Polera'),
    ('Overol');

-- ------------------------------------------------------------
-- Tallas (5 tallas estándar)
-- ------------------------------------------------------------
INSERT INTO tallas (nombre_talla) VALUES
    ('XS'),
    ('S'),
    ('M'),
    ('L'),
    ('XL');

INSERT INTO empresa (nombre_empresa)
VALUES ("Carlos Cramer Productos Aromáticos S.A.C.I."),
("Sabores y Fragancias");


-- ------------------------------------------------------------
-- Inventario (~50 prendas con distribución variada)
-- TipoID: Camisa=1, Pantalón=2, Chaqueta=3, Polera=4, Overol=5
-- TallaID: XS=1, S=2, M=3, L=4, XL=5
-- EstadoDisponible: 1=disponible, 0=en uso
-- TagEPC: NULL = sin RFID vinculado
-- NOTA: Los IDs asignados por AUTO_INCREMENT pueden variar.
--       Este seed usa subqueries para obtener IDs reales.
-- ------------------------------------------------------------

-- Camisas (12 unidades: 8 disponibles, 4 en uso)
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-S-001', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   1, 'EPC001CAMIISA001' FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-S-002', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   1, 'EPC002CAMISA002' FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-M-003', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, 'EPC003CAMISA003' FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-M-004', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-M-005', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-L-006', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   1, 'EPC006CAMISA006' FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-L-007', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-XL-008', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='XL'), 1, NULL FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-S-009', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   0, 'EPC009CAMISA009' FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-M-010', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   0, 'EPC010CAMISA010' FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-L-011', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   0, 'EPC011CAMISA011' FROM tiposPrendas WHERE nombreTipo='Camisa';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CAM-XL-012', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='XL'), 0, 'EPC012CAMISA012' FROM tiposPrendas WHERE nombreTipo='Camisa';

-- Pantalones (11 unidades: 7 disponibles, 4 en uso)
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-XS-001', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='XS'), 1, 'EPC101PANTAL001' FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-S-002', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   1, 'EPC102PANTAL002' FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-M-003', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, 'EPC103PANTAL003' FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-M-004', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-L-005', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-L-006', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   1, 'EPC106PANTAL006' FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-XL-007', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='XL'), 1, NULL FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-S-008', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   0, 'EPC108PANTAL008' FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-M-009', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   0, 'EPC109PANTAL009' FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-L-010', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   0, 'EPC110PANTAL010' FROM tiposPrendas WHERE nombreTipo='Pantalón';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'PAN-XL-011', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='XL'), 0, 'EPC111PANTAL011' FROM tiposPrendas WHERE nombreTipo='Pantalón';

-- Chaquetas (9 unidades: 6 disponibles, 3 en uso)
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CHA-S-001', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   1, 'EPC201CHAQET001' FROM tiposPrendas WHERE nombreTipo='Chaqueta';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CHA-M-002', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, 'EPC202CHAQET002' FROM tiposPrendas WHERE nombreTipo='Chaqueta';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CHA-M-003', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Chaqueta';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CHA-L-004', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   1, 'EPC204CHAQET004' FROM tiposPrendas WHERE nombreTipo='Chaqueta';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CHA-L-005', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Chaqueta';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CHA-XL-006', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='XL'), 1, NULL FROM tiposPrendas WHERE nombreTipo='Chaqueta';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CHA-S-007', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   0, 'EPC207CHAQET007' FROM tiposPrendas WHERE nombreTipo='Chaqueta';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CHA-M-008', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   0, 'EPC208CHAQET008' FROM tiposPrendas WHERE nombreTipo='Chaqueta';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'CHA-L-009', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   0, 'EPC209CHAQET009' FROM tiposPrendas WHERE nombreTipo='Chaqueta';

-- Poleras (10 unidades: 7 disponibles, 3 en uso)
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-XS-001', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='XS'), 1, 'EPC301POLERA001' FROM tiposPrendas WHERE nombreTipo='Polera';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-S-002', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   1, 'EPC302POLERA002' FROM tiposPrendas WHERE nombreTipo='Polera';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-M-003', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, 'EPC303POLERA003' FROM tiposPrendas WHERE nombreTipo='Polera';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-M-004', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Polera';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-L-005', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Polera';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-L-006', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   1, 'EPC306POLERA006' FROM tiposPrendas WHERE nombreTipo='Polera';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-XL-007', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='XL'), 1, NULL FROM tiposPrendas WHERE nombreTipo='Polera';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-S-008', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   0, 'EPC308POLERA008' FROM tiposPrendas WHERE nombreTipo='Polera';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-M-009', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   0, 'EPC309POLERA009' FROM tiposPrendas WHERE nombreTipo='Polera';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'POL-L-010', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   0, 'EPC310POLERA010' FROM tiposPrendas WHERE nombreTipo='Polera';

-- Overoles (8 unidades: 5 disponibles, 3 en uso)
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'OVE-S-001', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   1, 'EPC401OVERO1001' FROM tiposPrendas WHERE nombreTipo='Overol';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'OVE-M-002', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, 'EPC402OVERO1002' FROM tiposPrendas WHERE nombreTipo='Overol';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'OVE-M-003', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   1, NULL FROM tiposPrendas WHERE nombreTipo='Overol';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'OVE-L-004', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   1, 'EPC404OVERO1004' FROM tiposPrendas WHERE nombreTipo='Overol';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'OVE-XL-005', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='XL'), 1, NULL FROM tiposPrendas WHERE nombreTipo='Overol';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'OVE-S-006', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='S'),   0, 'EPC406OVERO1006' FROM tiposPrendas WHERE nombreTipo='Overol';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'OVE-M-007', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='M'),   0, 'EPC407OVERO1007' FROM tiposPrendas WHERE nombreTipo='Overol';
INSERT IGNORE INTO inventario (SKU, TipoID, TallaID, EstadoDisponible, TagEPC)
SELECT 'OVE-L-008', TipoID, (SELECT TallaID FROM tallas WHERE nombreTalla='L'),   0, 'EPC408OVERO1008' FROM tiposPrendas WHERE nombreTipo='Overol';

-- ============================================================
-- Resumen esperado tras el seed:
--   Total prendas : 50
--   Disponibles   : 33
--   En uso        : 17
--   Con RFID      : 35
--   Sin RFID      : 15
--
--   Por tipo:
--     Camisa   : 12  Pantalón : 11  Chaqueta : 9
--     Polera   : 10  Overol   : 8
--
--   Por talla (aprox):
--     XS: 3  S: 10  M: 17  L: 14  XL: 6
-- ============================================================
