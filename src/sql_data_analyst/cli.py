from __future__ import annotations

from .config import AppConfig
from .ui import build_demo


def main() -> None:
    config = AppConfig()
    demo = build_demo(config)
    demo.launch(server_name=config.host, server_port=config.port)
