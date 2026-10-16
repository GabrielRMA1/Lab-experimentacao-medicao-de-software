import pytest

from src.metricas.heuristica import (
    VERSIONS,
    classify_releases,
    extract_features,
    fix_keyword_ratio,
    is_corrective,
    is_patch_bump,
    notes_have_keyword,
    parse_version,
)


def rel(tag, name=None, body=None):
    return {"tag_name": tag, "name": name, "body": body, "published_at": "2026-01-01T00:00:00Z"}


def msgs(*texts):
    return [{"sha": str(i), "message": t} for i, t in enumerate(texts)]


@pytest.mark.parametrize(
    "tag,expected",
    [
        ("v2.3.1", (2, 3, 1)),
        ("release-1.4", (1, 4, 0)),
        ("proj-10.0.2.5", (10, 0, 2)),
        ("2024.05.10", None),  # calendário: patch não é SemVer
        ("nightly", None),
        (None, None),
    ],
)
def test_parse_version(tag, expected):
    assert parse_version(tag) == expected


def test_patch_bump_exemplo_do_enunciado():
    assert is_patch_bump("v2.3.0", "v2.3.1") is True       # 2.3.0 -> 2.3.1
    assert is_patch_bump("v2.4.0", "v2.5.0") is False      # muda o minor
    assert is_patch_bump("v2.3.1", "v2.3.0") is False      # patch não pode cair
    assert is_patch_bump("v1.0.0", "v2.0.1") is False      # muda o major
    assert is_patch_bump(None, "v1.0.1") is False          # sem release anterior


def test_fix_keyword_ratio_e_casos_de_borda():
    assert fix_keyword_ratio([]) == 0.0
    ratio = fix_keyword_ratio(
        msgs("fix: crash ao abrir", 'Revert "feat: x"', "hotfix login", "docs: readme")
    )
    assert ratio == 0.75
    # "prefix" e "fixture" não são "fix"
    assert fix_keyword_ratio(msgs("add prefix option", "update fixture")) == 0.0


def test_notes_keyword_usa_titulo_e_inicio_das_notas():
    assert notes_have_keyword(rel("v1", name="Hotfix release")) is True
    assert notes_have_keyword(rel("v1", body="Fixes a regression in parser")) is True
    assert notes_have_keyword(rel("v1", body="x" * 400 + " hotfix")) is False  # só 300 chars
    assert notes_have_keyword(rel("v1", name="New features")) is False


def test_versoes_registradas_e_default_valido():
    from src.metricas.heuristica import DEFAULT_VERSION

    assert DEFAULT_VERSION in VERSIONS
    assert len(VERSIONS) >= 4


def test_exemplo_do_enunciado_v2_3_1_e_corretiva():
    # v2.3.1 só muda o patch e contém "fix: crash ao abrir arquivo"
    previous, current = rel("v2.3.0"), rel("v2.3.1")
    commits = msgs("fix: crash ao abrir arquivo")
    assert is_corrective(current, previous, commits, "v1_patch")
    assert is_corrective(current, previous, commits, "v2_palavras")
    assert is_corrective(current, previous, commits, "v3_patch_ou_palavras")
    assert is_corrective(current, previous, commits, "v4_patch_e_palavras")
    assert is_corrective(current, previous, commits, "v5_refinada")
    # v2.5.0 não é
    assert not is_corrective(rel("v2.5.0"), rel("v2.4.0"), msgs("feat: nova tela"), "v3_patch_ou_palavras")


def test_versoes_divergem_nos_casos_ambiguos():
    previous, current = rel("v1.0.0"), rel("v1.0.1")
    so_patch = msgs("chore: bump deps", "docs: changelog")
    assert is_corrective(current, previous, so_patch, "v1_patch")
    assert not is_corrective(current, previous, so_patch, "v4_patch_e_palavras")
    assert not is_corrective(current, previous, so_patch, "v2_palavras")

    # minor com maioria de fixes: palavras sim, patch não
    minor = rel("v1.1.0")
    fixes = msgs("fix a", "fix b", "docs")
    assert is_corrective(minor, previous, fixes, "v2_palavras")
    assert not is_corrective(minor, previous, fixes, "v1_patch")


def test_release_sem_commits_nao_quebra_e_primeira_release_nao_e_patch():
    assert not is_corrective(rel("v1.0.0"), None, [], "v3_patch_ou_palavras")
    features = extract_features(rel("v1.0.0"), None, [])
    assert features["patch_bump"] is False and features["n_commits"] == 0


def test_versao_desconhecida_levanta_erro_claro():
    with pytest.raises(KeyError, match="v99"):
        is_corrective(rel("v1"), None, [], "v99")


def test_classify_releases_usa_commits_da_propria_release():
    releases = [rel("v2.3.0"), rel("v2.3.1"), rel("v2.4.0")]
    commits = {"v2.3.1": msgs("fix: crash"), "v2.4.0": msgs("feat: algo")}
    result = classify_releases(releases, commits, "v3_patch_ou_palavras")
    assert [r["is_corrective"] for r in result] == [False, True, False]
    assert [r["tag_name"] for r in result] == ["v2.3.0", "v2.3.1", "v2.4.0"]
