import csv

import pytest

from src.validacao.concordancia import (
    build_consensus,
    fleiss_kappa_from_ratings,
    interpret_kappa,
    load_rater_files,
    majority,
    percent_agreement,
    write_results,
)

# Exemplo clássico de Fleiss (1971), reproduzido na Wikipedia:
# 10 itens, 14 avaliadores, 5 categorias -> kappa = 0,210.
FLEISS_1971 = [
    [0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0],
    [2, 2, 8, 1, 1], [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2],
    [6, 5, 2, 1, 0], [0, 2, 2, 3, 7],
]


def expand(counts):
    return [[str(cat) for cat, n in enumerate(row) for _ in range(n)] for row in counts]


def manual_fleiss(ratings):
    """Fórmula de Fleiss escrita à mão, independente do statsmodels."""
    cats = sorted({x for r in ratings for x in r})
    n, N = len(ratings[0]), len(ratings)
    counts = [[r.count(c) for c in cats] for r in ratings]
    p_i = [(sum(x * x for x in row) - n) / (n * (n - 1)) for row in counts]
    p_j = [sum(row[j] for row in counts) / (N * n) for j in range(len(cats))]
    p_bar, p_e = sum(p_i) / N, sum(p * p for p in p_j)
    return (p_bar - p_e) / (1 - p_e)


def test_kappa_bate_com_o_valor_publicado_de_fleiss():
    assert fleiss_kappa_from_ratings(expand(FLEISS_1971)) == pytest.approx(0.210, abs=0.001)


def test_kappa_bate_com_formula_manual_para_3_avaliadores():
    ratings = [["sim", "sim", "nao"], ["nao", "nao", "nao"], ["sim", "sim", "sim"],
               ["nao", "sim", "nao"], ["sim", "nao", "nao"], ["nao", "nao", "sim"]]
    assert fleiss_kappa_from_ratings(ratings) == pytest.approx(manual_fleiss(ratings))


def test_concordancia_perfeita_com_variabilidade_da_kappa_1():
    ratings = [["a"] * 3, ["b"] * 3, ["a"] * 3, ["b"] * 3]
    assert fleiss_kappa_from_ratings(ratings) == pytest.approx(1.0)
    assert percent_agreement(ratings) == 1.0


def test_sem_variabilidade_kappa_e_indefinido_none():
    assert fleiss_kappa_from_ratings([["sim"] * 3] * 5) is None
    assert fleiss_kappa_from_ratings([]) is None


def test_discordancia_total_da_kappa_negativo_ou_zero():
    ratings = [["a", "b", "c"]] * 6
    assert fleiss_kappa_from_ratings(ratings) < 0


@pytest.mark.parametrize("k,label", [(-0.1, "pobre"), (0.1, "leve"), (0.3, "razoável"),
                                     (0.5, "moderada"), (0.7, "substancial"),
                                     (0.9, "quase perfeita"), (None, None)])
def test_landis_koch(k, label):
    assert interpret_kappa(k) == label


def test_majority():
    assert majority(["a", "a", "b"]) == "a"
    assert majority(["a", "b", "c"]) is None
    assert majority(["a", "a", "a"]) == "a"


# ---------------------------------------------------------------- arquivos

def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(header)
        w.writerows(rows)


def make_rater(directory, name, tipos, entregas, corretivas):
    write_csv(directory / f"rotulos_{name}_repos.csv",
              ["full_name", "url", "tipo_projeto", "entregas_reais"],
              [[f"o/r{i}", "u", tipos[i], entregas[i]] for i in range(len(tipos))])
    write_csv(directory / f"rotulos_{name}_releases.csv",
              ["full_name", "tag_name", "release_url", "corretiva"],
              [[f"o/r{i // 2}", f"v{i}", "u", corretivas[i]] for i in range(len(corretivas))])


@pytest.fixture
def raters_dir(tmp_path):
    T, E = "biblioteca_framework", "sim"
    make_rater(tmp_path, "leo", [T, "aplicacao_servico", T, T], [E, "nao", E, "incerto"], ["sim", "nao", "nao", "sim"])
    make_rater(tmp_path, "gabriel", [T, "aplicacao_servico", "ferramenta_cli", T], [E, "nao", E, "sim"], ["sim", "nao", "sim", "nao"])
    make_rater(tmp_path, "pedro", [T, "aplicacao_servico", "outro", "ferramenta_cli"], [E, "nao", "nao", "nao"], ["sim", "sim", "nao", "sim"])
    return tmp_path


def test_consenso_maioria_unanimidade_e_pendente(raters_dir):
    result = build_consensus(load_rater_files(raters_dir), raters_dir)
    repos = {r["full_name"]: r for r in result["consensus"]["repos"]}
    assert repos["o/r0"]["tipo_projeto"] == "biblioteca_framework"
    assert repos["o/r0"]["tipo_projeto_metodo"] == "unanimidade"
    assert repos["o/r2"]["tipo_projeto"] == ""          # T / cli / outro: 1-1-1
    assert repos["o/r2"]["tipo_projeto_metodo"] == "pendente"
    assert repos["o/r2"]["entregas_reais_metodo"] == "maioria"   # sim/sim/nao
    assert result["report"]["pendentes_desempate"] == 2          # r2 (tipo 1-1-1) e r3 (entregas sim/nao/incerto)
    assert {p["chave"] for p in result["pending"]} >= {"o/r2"}
    assert result["report"]["consenso_completo"] is False
    assert set(result["report"]["dimensoes"]) == {"tipo_projeto", "entregas_reais", "corretiva"}


def test_desempate_preenchido_e_preservado_ao_rodar_de_novo(raters_dir):
    first = build_consensus(load_rater_files(raters_dir), raters_dir)
    write_results(first, raters_dir)
    rows = list(csv.DictReader((raters_dir / "desempate.csv").open(encoding="utf-8")))
    for row in rows:
        row["rotulo_final"] = "outro" if row["dimensao"] == "tipo_projeto" else "sim"
        row["justificativa"] = "decidido em reunião"
    write_csv(raters_dir / "desempate.csv", list(rows[0]), [list(r.values()) for r in rows])

    second = build_consensus(load_rater_files(raters_dir), raters_dir)
    assert second["report"]["pendentes_desempate"] == 0
    assert second["report"]["consenso_completo"] is True
    write_results(second, raters_dir)   # não pode apagar os desempates decididos
    again = list(csv.DictReader((raters_dir / "desempate.csv").open(encoding="utf-8")))
    assert all(r["rotulo_final"] and r["justificativa"] for r in again)
    consenso = list(csv.DictReader((raters_dir / "consenso_repos.csv").open(encoding="utf-8")))
    assert {r["tipo_projeto_metodo"] for r in consenso} >= {"desempate"}


def test_kappa_calculado_nas_tres_dimensoes(raters_dir):
    report = build_consensus(load_rater_files(raters_dir), raters_dir)["report"]
    for dim in report["dimensoes"].values():
        assert dim["n_itens"] in (4,)
        assert dim["concordancia_total"] is not None


def test_valor_invalido_e_rejeitado_com_mensagem_clara(raters_dir):
    path = raters_dir / "rotulos_leo_repos.csv"
    path.write_text(path.read_text(encoding="utf-8").replace("aplicacao_servico", "app"), encoding="utf-8")
    with pytest.raises(ValueError, match="valor inválido.*tipo_projeto"):
        build_consensus(load_rater_files(raters_dir), raters_dir)


def test_exige_tres_avaliadores(raters_dir):
    for f in raters_dir.glob("rotulos_pedro_*"):
        f.unlink()
    with pytest.raises(ValueError, match="3 avaliadores"):
        build_consensus(load_rater_files(raters_dir), raters_dir)


def test_avaliador_que_nao_cobre_os_mesmos_itens(raters_dir):
    path = raters_dir / "rotulos_gabriel_releases.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mesmos itens"):
        build_consensus(load_rater_files(raters_dir), raters_dir)


def test_arquivo_faltando_do_mesmo_avaliador(raters_dir):
    (raters_dir / "rotulos_pedro_releases.csv").unlink()
    with pytest.raises(FileNotFoundError, match="pedro"):
        load_rater_files(raters_dir)


def test_templates_nao_sao_lidos_como_avaliador(raters_dir):
    write_csv(raters_dir / "rotulos_repos_TEMPLATE.csv", ["full_name"], [["x"]])
    assert set(load_rater_files(raters_dir)) == {"leo", "gabriel", "pedro"}


def test_modo_parcial_ignora_itens_sem_os_tres_rotulos(raters_dir):
    path = raters_dir / "rotulos_pedro_releases.csv"
    rows = list(csv.reader(path.open(encoding="utf-8")))
    rows[-1][3] = ""                       # Pedro ainda não rotulou a última release
    write_csv(path, rows[0], rows[1:])
    with pytest.raises(ValueError, match="valor inválido"):
        build_consensus(load_rater_files(raters_dir), raters_dir)        # modo estrito recusa
    result = build_consensus(load_rater_files(raters_dir), raters_dir, partial=True)
    info = result["report"]["dimensoes"]["corretiva"]
    assert result["report"]["parcial"] is True
    assert info["n_itens"] == 3 and info["n_itens_sem_rotulo_completo"] == 1
    last = result["consensus"]["releases"][-1]
    assert last["corretiva_metodo"] == "nao_rotulado" and last["corretiva"] == ""
