import argparse
import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

ESPERADOS = [
    "dados/raw_pilot.csv", "dados/raw_full.csv", "dados/env_snapshot.txt",
    "dados/raw_full.sha256", "dados/relatorio_validacao.md",
    "scripts/blender_scene_render.py",
    "scripts/blender_bench.py", "/scripts/validate_data.py",
    "scripts/analyze.py",
    "resultados/resultados_auto.md", "resultados/testes.csv",
    "resultados/estatisticas_descritivas.csv",
    "resultados/boxplot_render.png", "resultados/boxplot_total.png",
    "resultados/render_por_execucao.png",
]


def ler_texto(path: Path) -> str:
    """Lê texto em UTF-8 ou UTF-16 (o PowerShell grava '>' em UTF-16)."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def sha256_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def hash_registrado(path: Path):
    """Pega o primeiro token de 64 hex (formato sha256sum, shasum ou certutil)."""
    texto = ler_texto(path).replace(" ", "")
    m = re.search(r"\b[0-9a-fA-F]{64}\b", ler_texto(path)) or re.search(r"[0-9a-fA-F]{64}", texto)
    return m.group(0).lower() if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dados", default="../../dados", help="pasta dados/")
    ap.add_argument("--raiz", default="../..", help="raiz do repositório")
    ap.add_argument("--expected-reps", type=int, default=20)
    ap.add_argument("--versions", nargs=2, default=["4.5", "5.2"])
    a = ap.parse_args()

    dados, raiz = Path(a.dados), Path(a.raiz)
    falhas = []

    def ok(msg): print(f"[OK]    {msg}")
    def erro(msg):
        print(f"[ERRO]  {msg}")
        falhas.append(msg)

    csv_path, sha_path = dados / "raw_full.csv", dados / "raw_full.sha256"

    # 1. checksum
    if not csv_path.exists() or not sha_path.exists():
        erro("raw_full.csv ou raw_full.sha256 não encontrado")
    else:
        real, reg = sha256_arquivo(csv_path), hash_registrado(sha_path)
        if reg is None:
            erro("não achei um hash SHA-256 em raw_full.sha256")
        elif real == reg:
            ok(f"SHA-256 de raw_full.csv confere ({real[:16]}...)")
        else:
            erro("SHA-256 diferente do registrado. Se o CSV passou pelo Git no Windows, "
                 "confira o .gitattributes (dados/*.csv -text)")

    # 2 e 3. conteúdo
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            linhas = list(csv.DictReader(f))
        esperado = a.expected_reps * 4
        (ok if len(linhas) == esperado else erro)(f"{len(linhas)} linhas (esperado {esperado})")
        celulas = Counter((r["version"], r["workload"]) for r in linhas)
        for (v, w), n in sorted(celulas.items()):
            (ok if n == a.expected_reps else erro)(f"célula {v}/{w}: {n} execuções")
        if len(celulas) != 4:
            erro(f"esperava 4 células, achei {len(celulas)}")
        ruins = [r for r in linhas if r["returncode"] != "0"]
        (erro(f"{len(ruins)} execuções com código de saída diferente de 0") if ruins
         else ok("todas as execuções com código de saída 0"))
        for r in linhas:
            if not r["blender_version"].startswith(r["version"]):
                erro(f"versão inconsistente: rótulo {r['version']} x {r['blender_version']}")
                break
        else:
            ok("versão do Blender coerente com o rótulo em todas as linhas")
        usados = {v for v, _ in celulas}
        (ok if usados == set(a.versions) else erro)(f"versões no CSV: {sorted(usados)}")

    # 4. arquivos da integração
    for rel in ESPERADOS:
        (ok if (raiz / rel).exists() else erro)(f"existe {rel}")
    logs = dados / "logs"
    n_logs = len(list(logs.glob("*.log"))) if logs.exists() else 0
    print(f"[INFO]  dados/logs: {n_logs} arquivos .log (opcional)")

    print()
    if falhas:
        print(f"{len(falhas)} problema(s). Corrija antes de entregar.")
        sys.exit(1)
    print("Tudo certo.")


if __name__ == "__main__":
    main()
