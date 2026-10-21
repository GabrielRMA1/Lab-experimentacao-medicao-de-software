"""Ponto de entrada: ``python -m src.pipeline <comando>`` (a partir de ``Lab 3``)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.pipeline.config import Config

COMMANDS = {
    "search": "busca candidatos (estrelas fatiadas) -> data/candidates.json",
    "collect": "coleta com cache/retomada (use --shard I/N para dividir)",
    "merge-cache": "junta caches de outras máquinas: merge-cache PASTA [PASTA ...]",
    "consolidate": "funil + dataset_repos.csv + dicionário de dados",
    "amostra-ouro": "sorteia 60 repositórios e gera o material de rotulagem",
    "concordancia": "kappa de Fleiss + consenso dos 3 avaliadores",
    "heuristica": "precisão/recall/F1 de cada versão da heurística corretiva",
    "all": "search + collect + consolidate",
}


def cmd_search(cfg: Config, args) -> None:
    from src.collectors.repositories import GitHubClient, search_repositories_sliced
    from src.pipeline.selecao import save_candidates

    if cfg.candidates_path.exists() and not args.force:
        print(f"{cfg.candidates_path} já existe (use --force para refazer a busca).")
        return
    items = search_repositories_sliced(
        GitHubClient(), cfg.query, target=cfg.candidates_target
    )
    save_candidates(cfg.candidates_path, items, cfg.query)
    print(f"{len(items)} candidatos salvos em {cfg.candidates_path}")


def cmd_collect(cfg: Config, args) -> None:
    from src.collectors.repositories import GitHubClient
    from src.pipeline.selecao import collect, load_candidates, parse_shard

    candidates = load_candidates(cfg.candidates_path)
    stats = collect(GitHubClient(), candidates, cfg, parse_shard(args.shard))
    print("Resumo:", stats)


def cmd_merge_cache(cfg: Config, args) -> None:
    from src.collectors import repositories
    from src.pipeline.merge import merge_caches

    if not args.paths:
        raise SystemExit("Informe ao menos uma pasta: merge-cache PASTA [PASTA ...]")
    stats = merge_caches([Path(p) for p in args.paths], repositories.CACHE_DIR)
    print(f"Cache unificado em {repositories.CACHE_DIR}: {stats}")


def cmd_consolidate(cfg: Config, args) -> None:
    from src.collectors.repositories import load_cached_repository
    from src.pipeline.dataset import (
        build_dataset, chosen_heuristic_version, write_dataset,
        write_dictionary_files,
    )
    from src.pipeline.funil import build_funnel, write_funnel
    from src.pipeline.selecao import load_candidates, read_decisions

    candidates = load_candidates(cfg.candidates_path)
    decisions = read_decisions(
        candidates, lambda n: load_cached_repository(n, include_segments=False)
    )
    funnel = build_funnel(candidates, decisions, cfg)
    write_funnel(funnel, candidates, decisions, cfg.data_dir)
    print(open(cfg.data_dir / "funil.md", encoding="utf-8").read())

    names = funnel["repositorios_amostra_final"]
    if not names:
        print("Nenhum repositório aceito ainda; rode `collect`.")
        return
    version = chosen_heuristic_version(cfg)
    rows = build_dataset(names, load_cached_repository, cfg, version)
    path = write_dataset(rows, cfg.dataset_dir)
    write_dictionary_files(cfg.dataset_dir, cfg.docs_dir)
    print(f"Dataset: {path} ({len(rows)} repositórios; heurística {version})")
    if not funnel["atinge_minimo"]:
        print(f"ATENÇÃO: abaixo do mínimo de {cfg.min_sample}. "
              "Aumente CANDIDATES_TARGET e rode `search --force` + `collect`.")


def cmd_amostra_ouro(cfg: Config, args) -> None:
    import csv

    from src.collectors.repositories import load_cached_repository
    from src.validacao.amostra_ouro import build_package, sample_repositories, write_outputs

    dataset = cfg.dataset_dir / "dataset_repos.csv"
    with dataset.open(newline="", encoding="utf-8") as handle:
        names = [row["full_name"] for row in csv.DictReader(handle)]
    selected = sample_repositories(names)
    package = build_package(
        selected, load_cached_repository, cfg.observation_start, cfg.observation_end
    )
    paths = write_outputs(package, cfg.validacao_dir)
    print(f"{len(selected)} repositórios sorteados (semente 42). Arquivos:")
    for path in paths.values():
        print("  ", path)


def cmd_concordancia(cfg: Config, args) -> None:
    from src.validacao.concordancia import main as run
    run(cfg.validacao_dir, partial=args.parcial)


def cmd_heuristica(cfg: Config, args) -> None:
    from src.validacao.avaliar_heuristica import main as run
    run(cfg.validacao_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.pipeline")
    parser.add_argument("command", choices=list(COMMANDS), help="; ".join(
        f"{k}: {v}" for k, v in COMMANDS.items()))
    parser.add_argument("paths", nargs="*", help="pastas de cache (merge-cache)")
    parser.add_argument("--shard", help="I/N: processa só a fatia I de N (ex.: 2/3)")
    parser.add_argument("--parcial", action="store_true",
                        help="concordancia: usa só itens que os 3 já rotularam")
    parser.add_argument("--force", action="store_true", help="refaz a busca (search)")
    args = parser.parse_args(argv)
    cfg = Config.from_env()

    handlers = {
        "search": cmd_search, "collect": cmd_collect, "merge-cache": cmd_merge_cache,
        "consolidate": cmd_consolidate, "amostra-ouro": cmd_amostra_ouro,
        "concordancia": cmd_concordancia, "heuristica": cmd_heuristica,
    }
    if args.command == "all":
        for step in (cmd_search, cmd_collect, cmd_consolidate):
            step(cfg, args)
    else:
        handlers[args.command](cfg, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
