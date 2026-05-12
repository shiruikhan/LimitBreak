"""
utils/logger.py — configuração centralizada de logging para o LimitBreak.

Uso:
    from utils.logger import logger

    logger.info("Mensagem informativa")
    logger.warning("Algo inesperado mas recuperável")
    logger.error("Falha em operação crítica: {}", str(e))
    logger.exception("Exceção com traceback completo")  # dentro de except
"""

import sys
from loguru import logger

# Remove o handler padrão do loguru (stderr sem formato)
logger.remove()

# Handler de console: legível em desenvolvimento e nos logs do Streamlit Cloud
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    ),
    level="INFO",
    colorize=True,
    backtrace=True,   # mostra traceback completo em exceptions
    diagnose=False,   # desliga valores de variáveis (segurança em produção)
)

__all__ = ["logger"]
