"""Compatibilidade com a S01: ``python src/main.py`` roda o pipeline completo.

Prefira os comandos separados: ``python -m src.pipeline <search|collect|...>``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["all"]))
