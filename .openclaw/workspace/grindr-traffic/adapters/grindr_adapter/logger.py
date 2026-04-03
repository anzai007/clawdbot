"""grindr_adapter 日志模块（骨架）。"""

from __future__ import annotations

import logging


LOGGER_NAME = "grindr_adapter"


def get_logger() -> logging.Logger:
    """返回统一 logger，后续可扩展文件输出与结构化日志。"""

    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
