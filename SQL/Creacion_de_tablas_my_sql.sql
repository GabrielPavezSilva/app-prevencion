USE lavanderia_pruebas;

-- tabla de roles para los distintos usuarios de la aplicación
CREATE TABLE roles (
    rol_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_rol VARCHAR(50) NOT NULL UNIQUE
);

-- tabla para registrar a los diferentes usuarios habilitados
CREATE TABLE usuarios (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    correo VARCHAR(100) NOT NULL UNIQUE,
    contrasena VARCHAR(255) NOT NULL,
    rol_id INT NOT NULL,
    activo BIT DEFAULT 1,
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultimo_login DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (rol_id) REFERENCES roles(rol_id)
);

CREATE TABLE modulos (
    modulo_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_modulo VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE roles_modulos (
    rol_id INT NOT NULL,
    modulo_id INT NOT NULL,
    
    FOREIGN KEY (rol_id) REFERENCES roles(rol_id),
    FOREIGN KEY (modulo_id) REFERENCES modulos(modulo_id)
);

CREATE TABLE personal (
	rut VARCHAR(20) PRIMARY KEY,
    nombre_completo VARCHAR(100) NOT NULL, 
    empresa VARCHAR(100) NOT NULL, 
    cargo VARCHAR(50) NOT NULL, 
    area_id INT NOT NULL,
    subarea_id INT NOT NULL,
    talla_id INT NOT NULL,
    huella_digital LONGBLOB NULL
);

CREATE TABLE areas (
	area_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_area VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE subareas (
	subarea_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_subarea VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE empresa (
    empresa_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_empresa VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE tiposPrendas (
	tipo_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_tipo VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE tallas (
	talla_id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_talla VARCHAR(50) NOT NULL UNIQUE
);

-- Sólo y exclusivamente con "Modo Inventario"
-- El Sku no debe borrarse, ya que permite el seguimiento de cada prenda
-- Esta misma tabla se mostrará en el módulo de inventario, pero más acotada
CREATE TABLE lecturas_rfid (
    id_lectura INT AUTO_INCREMENT PRIMARY KEY,
    tag_epc VARCHAR(50) NOT NULL,
    sku VARCHAR(100) NOT NULL UNIQUE,
    tipo_id INT NOT NULL,
    talla_id INT NOT NULL,
    accion VARCHAR(50) NOT NULL,
    resultado VARCHAR(50) NOT NULL,
    estado_disponible BIT DEFAULT 1,
    empresa_id INT NOT NULL,
    hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (tipo_id) REFERENCES tiposPrendas(tipo_id),
    FOREIGN KEY (talla_id) REFERENCES tallas(talla_id),
    FOREIGN KEY (empresa_id) REFERENCES empresa(empresa_id)
);

-- el SKU no puede borrarse por ningún motivo. run
-- CREATE TABLE inventario (
-- id_lectura INT,
--    sku VARCHAR(50),
--    tipo_id INT NOT NULL,
  --  talla_id INT NOT NULL, 
  --  empresa_id INT NOT NULL,
  --  estado_disponible BIT DEFAULT 1,
    
  --  FOREIGN KEY (tipo_id) REFERENCES tiposPrendas(tipo_id),
  --  FOREIGN KEY (talla_id) REFERENCES tallas(talla_id),
  --  FOREIGN KEY (empresa_id) REFERENCES empresa(empresa_id),
  --  FOREIGN KEY (sku) REFERENCES lecturas_rfid(sku)
-- );

CREATE TABLE asignaciones (
	asignacion_id INT AUTO_INCREMENT PRIMARY KEY,
    rut VARCHAR(20) NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL, 
    sku VARCHAR(50) NOT NULL,
    tag_epc VARCHAR(50) NOT NULL,
    fecha_entrega DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_devolucion DATETIME NULL,
    
    FOREIGN KEY (rut) REFERENCES personal(rut)
);

-- Prendas predeterminadas por cargo y empresa
-- Mapea qué tipos de prenda corresponden a cada combinación cargo+empresa
CREATE TABLE prendas_predeterminadas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cargo VARCHAR(50) NOT NULL,
    empresa VARCHAR(100) NOT NULL,
    tipo_id INT NOT NULL,

    FOREIGN KEY (tipo_id) REFERENCES tiposPrendas(tipo_id),
    UNIQUE KEY uq_cargo_empresa_tipo (cargo, empresa, tipo_id)
);

