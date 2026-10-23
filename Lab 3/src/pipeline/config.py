"""Configuração do pipeline (variáveis de ambiente / ``.env``)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]  # pasta "Lab 3"
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

# Janela de observação oficial do grupo: 12 meses (02/10/2025 a 02/10/2026),
# aprovada pelo professor. Pode ser sobrescrita por OBSERVATION_START /
# OBSERVATION_END, mas os três integrantes DEVEM usar exatamente a mesma.
DEFAULT_OBSERVATION_START = "2025-10-02T00:00:00Z"
DEFAULT_OBSERVATION_END = "2026-10-02T23:59:59Z"


@dataclass
class Config:
    query: str = "stars:>1000"
    candidates_target: int = 3000  # sobra de candidatos: a coleta para ao atingir a cota
    sample_target: int = 400  # teto da amostra final (mínimo exigido: 300)
    min_sample: int = 300
    min_releases: int = 5
    min_runs: int = 50
    workers: int = 4
    observation_start: str = DEFAULT_OBSERVATION_START
    observation_end: str = DEFAULT_OBSERVATION_END
    heuristica_versao: str | None = None  # None -> usa a escolhida na validação
    data_dir: Path = field(default_factory=lambda: ROOT / "data")
    docs_dir: Path = field(default_factory=lambda: ROOT / "docs")

    @property
    def candidates_path(self) -> Path:
        return self.data_dir / "candidates.json"

    @property
    def dataset_dir(self) -> Path:
        return self.data_dir / "dataset"

    @property
    def validacao_dir(self) -> Path:
        return self.data_dir / "validacao"

    @classmethod
    def from_env(cls) -> "Config":
        env = os.getenv
        return cls(
            query=env("GITHUB_REPO_QUERY", cls.query),
            candidates_target=int(env("CANDIDATES_TARGET", cls.candidates_target)),
            sample_target=int(env("SAMPLE_TARGET", cls.sample_target)),
            min_sample=int(env("MIN_SAMPLE", cls.min_sample)),
            workers=int(env("WORKERS", cls.workers)),
            observation_start=env("OBSERVATION_START", DEFAULT_OBSERVATION_START),
            observation_end=env("OBSERVATION_END", DEFAULT_OBSERVATION_END),
            heuristica_versao=env("HEURISTICA_VERSAO") or None,
            data_dir=Path(env("LAB3_DATA_DIR") or ROOT / "data"),
            docs_dir=Path(env("LAB3_DOCS_DIR") or ROOT / "docs"),
        )

    def window_signature(self) -> list:
        return [
            self.observation_start,
            self.observation_end,
            self.min_releases,
            self.min_runs,
        ]
