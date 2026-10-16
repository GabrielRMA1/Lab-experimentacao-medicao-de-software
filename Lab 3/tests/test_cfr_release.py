from src.metricas.cfr_release import commits_by_tag_from_cache, compute_cfr_release

START, END = "2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z"


def item(tag, published, corrective=False):
    return {"tag_name": tag, "published_at": published, "is_corrective": corrective}


def test_exemplo_do_enunciado():
    # v2.3.0 (10/05) é seguida por v2.3.1 (12/05, corretiva) -> falhou
    # v2.4.0 (01/06) é seguida por v2.5.0 (20/06) -> não falhou
    classified = [
        item("v2.3.0", "2026-05-10T12:00:00Z"),
        item("v2.3.1", "2026-05-12T12:00:00Z", True),
        item("v2.4.0", "2026-06-01T12:00:00Z"),
        item("v2.5.0", "2026-06-20T12:00:00Z"),
    ]
    result = compute_cfr_release(classified, START, END)
    # v2.3.0 falhou; v2.3.1, v2.4.0, v2.5.0 não (nenhuma corretiva depois delas)
    assert result["n_releases_avaliadas"] == 4
    assert result["n_releases_falha"] == 1
    assert result["cfr_entrega"] == 0.25
    assert result["n_releases_corretivas"] == 1
    assert result["rework_rate"] == 0.25


def test_corretiva_depois_de_7_dias_nao_conta():
    classified = [
        item("v1.0.0", "2026-03-01T00:00:00Z"),
        item("v1.0.1", "2026-03-08T00:00:01Z", True),  # 7 dias + 1 s
    ]
    assert compute_cfr_release(classified, START, END)["n_releases_falha"] == 0
    classified[1]["published_at"] = "2026-03-08T00:00:00Z"  # exatamente 7 dias
    assert compute_cfr_release(classified, START, END)["n_releases_falha"] == 1


def test_ultimos_7_dias_da_janela_sao_censurados():
    classified = [
        item("v1.0.0", "2026-12-20T00:00:00Z"),   # 11 dias antes do fim: avaliada
        item("v1.0.1", "2026-12-28T00:00:00Z", True),  # < 7 dias do fim: censurada
        item("v1.0.2", "2026-12-30T00:00:00Z"),   # censurada
    ]
    result = compute_cfr_release(classified, START, END)
    assert result["n_releases_censuradas"] == 2
    assert result["n_releases_avaliadas"] == 1
    assert result["n_releases_falha"] == 0  # v1.0.1 está a 8 dias de v1.0.0
    assert result["n_releases_janela"] == 3


def test_release_anterior_a_janela_pode_ser_alvo_mas_nao_entra_na_conta():
    classified = [
        item("v0.9.0", "2025-12-30T00:00:00Z"),
        item("v0.9.1", "2025-12-31T00:00:00Z", True),
        item("v1.0.0", "2026-02-01T00:00:00Z"),
    ]
    result = compute_cfr_release(classified, START, END)
    assert result["n_releases_janela"] == 1
    assert result["n_releases_falha"] == 0


def test_caso_de_borda_sem_releases_na_janela():
    result = compute_cfr_release([], START, END)
    assert result["cfr_entrega"] is None and result["rework_rate"] is None
    assert result["n_releases_avaliadas"] == 0


def test_uma_unica_release_nao_falha():
    result = compute_cfr_release([item("v1.0.0", "2026-03-01T00:00:00Z")], START, END)
    assert result["n_releases_avaliadas"] == 1
    assert result["cfr_entrega"] == 0.0


def test_commits_by_tag_from_cache_ignora_404():
    record = {
        "_pipeline_cache": {
            "compare_v1": {
                "2026-01-01T00:00:00Z|2026-02-01T00:00:00Z|v1.0.0...v1.1.0": {
                    "items": [{"sha": "a", "message": "fix: x"}], "complete": True},
                "2026-02-01T00:00:00Z|2026-03-01T00:00:00Z|v1.1.0...v1.2.0": {
                    "items": [], "complete": True, "not_found": True},
            }
        }
    }
    assert commits_by_tag_from_cache(record) == {"v1.1.0": [{"sha": "a", "message": "fix: x"}]}
