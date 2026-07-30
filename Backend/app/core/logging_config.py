"""
Configuración de logging para la aplicación
"""
import logging

# Configurar el logger principal
logger = logging.getLogger("prevencion")
logger.setLevel(logging.INFO)

# Handler para consola
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
