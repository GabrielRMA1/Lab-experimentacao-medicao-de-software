"""Validação manual (amostra-ouro) — seção 6 do enunciado.

Fluxo (cada passo é uma etapa do ``python -m src.pipeline``):

1. ``amostra-ouro``  — sorteia 60 repositórios (semente fixa) e gera o pacote
   de rotulagem + modelos de planilha (SEM a saída da heurística).
2. cada integrante rotula sozinho (``tools/rotulador.html`` ou planilha) e
   commita **só o seu** ``rotulos_<nome>_*.csv``.
3. ``concordancia``  — kappa de Fleiss + consenso (maioria; 1-1-1 vai para
   ``desempate.csv``).
4. ``heuristica``    — precisão/recall/F1 de cada versão da heurística.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # pasta "Lab 3"
VALIDACAO_DIR = ROOT / "data" / "validacao"

SEED = 42
N_REPOS = 60
N_RELEASES_POR_REPO = 5

TIPOS_PROJETO = (
    "biblioteca_framework",
    "aplicacao_servico",
    "ferramenta_cli",
    "outro",
)
ENTREGAS_REAIS = ("sim", "nao", "incerto")
CORRETIVA = ("sim", "nao")

# Dimensão -> (arquivo de rótulos, coluna, valores válidos)
DIMENSOES = {
    "tipo_projeto": ("repos", "tipo_projeto", TIPOS_PROJETO),
    "entregas_reais": ("repos", "entregas_reais", ENTREGAS_REAIS),
    "corretiva": ("releases", "corretiva", CORRETIVA),
}
