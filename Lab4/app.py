import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


# Define a pasta do projeto como diretório de execução.
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

from graficos import (
    carregar_dados,
    carregar_simulacoes,
    grafico_g1,
    grafico_g2,
    grafico_g3,
    grafico_g4,
    grafico_poder_por_n,
)

# Link exigido no topo do dashboard
LINK_REPOSITORIO = "https://github.com/GabrielRMA1/Lab-experimentacao-medicao-de-software"
LINK_DASHBOARD = "https://experimentacao-medicao-de-software-lab4.streamlit.app"


# Configuração da página
st.set_page_config(
    page_title="LAB04 - Testes de Hipótese",
    page_icon="📊",
    layout="wide"
)


# Gera os dados se ainda não existirem (permite abrir tudo com um único comando)
@st.cache_resource(show_spinner="Gerando simulações (10.000 repetições)...")
def garantir_dados():
    pasta = BASE_DIR / "data"
    if not (pasta / "simulados.csv").exists() or not (pasta / "resultados.json").exists():
        import simulacao
        simulacao.main()
    if not all((pasta / f).exists() for f in ("simulacoes.csv", "poder_por_n.csv", "reais_resultados.json")):
        import simulacoes
        simulacoes.main()
    return True


garantir_dados()

# Carregamento dos dados
reais, simulados, resultados = carregar_dados()
simulacoes, poder_n, reais_res = carregar_simulacoes()


def pct(valor, casas=1):
    return f"{valor * 100:.{casas}f}%".replace(".", ",")


def num(valor, casas=2):
    return f"{valor:.{casas}f}".replace(".", ",")


def taxa(situacao, teste, reducao=0.0, alfa=0.05):
    filtro = (
        (simulacoes["situacao"] == situacao)
        & (simulacoes["teste"] == teste)
        & (np.isclose(simulacoes["reducao_mediana"], reducao))
        & (np.isclose(simulacoes["alfa"], alfa))
    )
    return float(simulacoes.loc[filtro, "taxa_rejeicao"].iloc[0])

n_com = (reais["grupo"] == "com_bot").sum()
n_sem = (reais["grupo"] == "sem_bot").sum()

dados_com = reais.loc[
    reais["grupo"] == "com_bot",
    "tempo_merge_horas"
]

dados_sem = reais.loc[
    reais["grupo"] == "sem_bot",
    "tempo_merge_horas"
]


# Cabeçalho
st.title("LAB04: t de Welch x Mann-Whitney")

st.markdown(
    """
    **Laboratório de Experimentação de Software**

    Análise do tempo até o merge de Pull Requests, comparando
    PRs com e sem o uso de um bot de revisão.
    """
)

st.markdown(
    f"""
    - **Repositório / GitHub Projects:** {LINK_REPOSITORIO}
    - **Dashboard:** {LINK_DASHBOARD}
    """
)

st.divider()


# 1. Cenário
st.header("1. Cenário")

st.markdown(
    """
    **Pergunta:** o bot de revisão altera o tempo até o merge dos PRs?

    O estudo utiliza dados do repositório público
    [langflow-ai/langflow](https://github.com/langflow-ai/langflow),
    comparando Pull Requests que receberam revisão do CodeRabbit
    com aqueles que não receberam.
    
    Foram coletadas amostras de dois períodos diferentes:
    fevereiro a abril de 2025, para o grupo sem bot, e julho a
    setembro de 2025, para o grupo com bot. Cada grupo possui
    30 observações, totalizando 60 Pull Requests.
    """
)

st.subheader("Hipóteses")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**t de Welch**")
    st.markdown(
        """
        - **H₀:** a média do tempo até o merge é igual nos dois grupos.
        - **H₁:** a média do tempo até o merge é diferente entre os grupos.
        """
    )

with col2:
    st.markdown("**Mann-Whitney**")
    st.markdown(
        """
        - **H₀:** um PR de um grupo tem a mesma chance de apresentar
          um tempo de merge maior ou menor que um PR do outro grupo.
        - **H₁:** essa chance não é igual entre os grupos.
        """
    )

st.info(
    "Os dois testes são bicaudais, pois queremos identificar se o bot "
    "altera o tempo de merge, independentemente de acelerar ou atrasar o processo."
)


# 2. Os dados
st.header("2. Os dados")

st.markdown(
    """
    O primeiro gráfico compara a distribuição dos tempos de merge
    dos dados reais com os dados gerados pela simulação. A escala
    logarítmica foi utilizada para facilitar a visualização dos
    valores, que apresentam grande diferença de magnitude.
    """
)

st.pyplot(grafico_g1(reais, simulados))

st.markdown(
    f"""
    Nos dados reais, os dois grupos apresentam assimetria à direita,
    pois a média dos tempos de merge é maior que a mediana. Isso indica
    a presença de PRs que demoraram consideravelmente mais para serem
    integrados, caracterizando valores extremos.

    Por esse motivo, escolhemos a distribuição lognormal para gerar
    os dados simulados. Ela permite representar essa assimetria,
    utilizando a mediana e o desvio-padrão dos logaritmos observados
    nos dados reais como parâmetros.

    - **Com bot:** mediana de 6,61 horas e sigma de 1,89.
    - **Sem bot:** mediana de 18,45 horas e sigma de 2,61.

    Foram geradas 30 observações simuladas para cada grupo, utilizando
    a semente aleatória 42 para garantir a reprodução dos resultados.
    """
)


# 3. Como os testes funcionam
st.header("3. Como os testes funcionam")

st.markdown(
    """
    O gráfico abaixo apresenta a distribuição esperada das estatísticas
    de cada teste quando a hipótese nula (H₀) é verdadeira. As regiões
    sombreadas indicam os valores que levam à rejeição de H₀, considerando
    um nível de significância de 5%.
    """
)

st.pyplot(grafico_g2(resultados))

st.markdown(
    f"""
    O **t de Welch** compara as médias dos dois grupos, sem exigir que
    eles tenham variâncias iguais. Sua estatística segue uma distribuição
    t, e os valores muito distantes de zero ficam nas regiões de rejeição.

    Já o **Mann-Whitney** compara as posições (ranks) dos valores dos
    grupos, sendo uma alternativa que não depende da comparação direta
    das médias. Sua estatística U possui uma distribuição aproximada
    normal sob H₀, e valores muito distantes de sua média ficam nas
    regiões de rejeição.

    O p-valor representa a probabilidade de observar um resultado tão
    extremo quanto o encontrado, ou mais extremo, supondo que H₀ seja
    verdadeira. Quanto menor o p-valor, maior a evidência contra H₀.
    """
)

st.subheader("Resultados da simulação")

st.markdown(
    f"""
    O nível de significância adotado foi **α = {resultados['alfa']:.2f}**.
    Os testes foram aplicados ao mesmo conjunto de dados simulados,
    com 30 observações em cada grupo.
    """
)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "p-valor — t de Welch",
        f"{resultados['welch_p']:.4f}"
    )

    st.write(
        f"Estatística t: {resultados['welch_t']:.4f}"
    )

    st.write(
        f"Graus de liberdade: {resultados['welch_gl']:.2f}"
    )

    if resultados["welch_p"] < resultados["alfa"]:
        st.success("Rejeitamos H₀.")
    else:
        st.warning("Não rejeitamos H₀.")

with col2:
    st.metric(
        "p-valor — Mann-Whitney",
        f"{resultados['mw_p']:.4f}"
    )

    st.write(
        f"Estatística U: {resultados['mw_u']:.2f}"
    )

    if resultados["mw_p"] < resultados["alfa"]:
        st.success("Rejeitamos H₀.")
    else:
        st.warning("Não rejeitamos H₀.")

st.subheader("Interpretação")

st.markdown(
    """
    O teste t de Welch apresentou p-valor de **0,1668**. Como esse
    valor é maior que 0,05, não rejeitamos H₀. Portanto, nesta simulação,
    não encontramos evidência estatística suficiente de diferença
    entre as médias dos grupos.

    Já o teste de Mann-Whitney apresentou p-valor de **0,0176**.
    Como esse valor é menor que 0,05, rejeitamos H₀. Nesse caso,
    encontramos evidência estatística de diferença entre os grupos,
    considerando a comparação de suas posições.

    Os testes chegaram a decisões diferentes porque analisam aspectos
    distintos dos dados: o t de Welch compara médias, enquanto o
    Mann-Whitney utiliza os postos das observações. Essa diferença
    não representa um erro, mas mostra como a escolha do teste pode
    influenciar a interpretação dos resultados.
    """
)

st.warning(
    "Como os resultados apresentados nesta etapa foram obtidos com "
    "dados simulados, eles não comprovam que o CodeRabbit altera o "
    "tempo de merge dos Pull Requests reais."
)


# Seletor de α (pergunta 12 da apresentação)
st.divider()
alfa_escolhido = st.radio(
    "Nível de significância usado nos gráficos G3 e G4",
    options=[0.05, 0.01],
    format_func=lambda a: f"α = {a}".replace(".", ","),
    horizontal=True,
)

st.caption(
    f"Cenários simulados: cada situação tem {int(reais_res['repeticoes']):,} repetições".replace(",", ".")
    + f" por tamanho de efeito, semente {reais_res['semente']}. Base: mediana do grupo sem bot "
    f"({num(reais_res['mediana_base_simulacao'])} h) e sigma combinado dos logaritmos "
    f"({num(reais_res['sigma_base_simulacao'])}), ambos tirados dos dados reais. "
    "O efeito é a redução da mediana no grupo com bot, mantendo o mesmo sigma."
)

with st.expander("As quatro situações simuladas"):
    st.markdown(
        """
        | Situação | Como os dados são gerados | Por que foi incluída |
        | --- | --- | --- |
        | **A. Normal (log do tempo)** | log das horas da lognormal, n = 30 | Pressupostos do t atendidos: serve de referência |
        | **B. Lognormal (horas)** | tempo em horas, n = 30 | Forma dos dados reais: muito assimétrica |
        | **C. Amostra pequena** | tempo em horas, n = 10 | Assimetria + poucos PRs (o TCL ajuda menos) |
        | **D. Outliers extremos** | como B, mas 5% dos PRs ganham +2.000 h (PRs "esquecidos") | Valores extremos que puxam a média |
        """
    )


# 4. Erro tipo I
st.header("4. Erro tipo I")

st.pyplot(grafico_g3(simulacoes, alfa_escolhido))

a = alfa_escolhido
ca = 1 if a == 0.05 else 2
taxas_mw = [taxa(sid, "Mann-Whitney", alfa=a) for sid in "ABCD"]
st.markdown(
    f"""
    O gráfico mostra, para cada situação com H₀ verdadeira, a proporção das 10.000 simulações
    em que o teste rejeitou H₀ (as barras pretas são o intervalo de 95% da estimativa).
    O **Mann-Whitney ficou perto do nominal em todas as situações**
    ({pct(min(taxas_mw), ca)} a {pct(max(taxas_mw), ca)}).
    O **t de Welch só acertou o nível na situação A** ({pct(taxa('A', 't de Welch', alfa=a), ca)});
    com dados assimétricos ele ficou **conservador**: {pct(taxa('B', 't de Welch', alfa=a), ca)} em B,
    {pct(taxa('C', 't de Welch', alfa=a), ca)} com n = 10 e {pct(taxa('D', 't de Welch', alfa=a), ca)} com outliers.
    Isso acontece porque os valores extremos inflam muito a variância estimada,
    o denominador do t cresce e a estatística raramente fica grande o bastante para rejeitar.
    Ser conservador parece "seguro", mas o preço aparece no poder (seção 5).
    """
)


# 5. Poder
st.header("5. Poder")

st.pyplot(grafico_g4(simulacoes, alfa_escolhido))

st.markdown(
    f"""
    Cada curva mostra com que frequência o teste detecta uma redução real da mediana.
    Na **situação A** (dados normais), os dois testes são praticamente iguais e o **t de Welch tem
    uma pequena vantagem** (a 80% de redução: {pct(taxa('A', 't de Welch', 0.8, a))} contra
    {pct(taxa('A', 'Mann-Whitney', 0.8, a))}), como prevê a teoria (eficiência de ~95% do
    Mann-Whitney sob normalidade). **Assim que os dados ficam assimétricos, a vantagem muda de lado**:
    na situação B, para a mesma redução de 80%, o Mann-Whitney detecta o efeito em
    {pct(taxa('B', 'Mann-Whitney', 0.8, a))} das vezes e o Welch em só {pct(taxa('B', 't de Welch', 0.8, a))}.
    Com n = 10 (C) os dois perdem poder, mas o Welch quase nunca rejeita; com outliers (D)
    o Welch fica praticamente cego ({pct(taxa('D', 't de Welch', 0.9, a))} mesmo com 90% de redução).
    Outro achado: como o tempo de merge varia muito (sigma ≈ {num(reais_res['sigma_base_simulacao'])}
    no log), até o melhor teste precisa de uma redução de ~80% da mediana para chegar a 80% de poder com 30 PRs.
    """
)

if alfa_escolhido == 0.01:
    st.info(
        "Com α = 0,01 a linha de referência do G3 desce para 1% e todas as curvas do G4 ficam mais baixas: "
        "há menos erro tipo I, mas mais erro tipo II. O padrão entre os testes se mantém: "
        f"o Welch fica ainda mais conservador (B: {pct(taxa('B', 't de Welch', 0, 0.01), 2)}) "
        f"e seu poder em B cai para {pct(taxa('B', 't de Welch', 0.9, 0.01))} mesmo com 90% de redução."
    )


# 6. Dados reais
st.header("6. Dados reais")

r = reais_res
tabela = pd.DataFrame([
    {
        "Teste": "t de Welch (horas)",
        "Estatística": f"t = {num(r['welch_t'])} (gl = {num(r['welch_gl'], 1)})",
        "p-valor": num(r["welch_p"], 3),
        "Tamanho do efeito": f"g de Hedges = {num(r['hedges_g'])}; diferença de médias = {num(r['diferenca_medias_h'], 1)} h",
        "Conclusão (α = 0,05)": "Rejeita H₀" if r["welch_p"] < 0.05 else "Não rejeita H₀",
    },
    {
        "Teste": "Mann-Whitney (horas)",
        "Estatística": f"U = {num(r['mw_u'], 0)}",
        "p-valor": num(r["mw_p"], 3),
        "Tamanho do efeito": f"rank-biserial = {num(r['rank_biserial'], 3)}; Hodges-Lehmann = {num(r['hodges_lehmann_h'])} h",
        "Conclusão (α = 0,05)": "Rejeita H₀" if r["mw_p"] < 0.05 else "Não rejeita H₀",
    },
    {
        "Teste": "Complementar: t de Welch no log(tempo)",
        "Estatística": f"t = {num(r['welch_log_t'])}",
        "p-valor": num(r["welch_log_p"], 3),
        "Tamanho do efeito": f"razão de médias geométricas = {num(r['razao_medias_geometricas'])}",
        "Conclusão (α = 0,05)": "Rejeita H₀" if r["welch_log_p"] < 0.05 else "Não rejeita H₀",
    },
])
st.dataframe(tabela, hide_index=True, width="stretch")

col1, col2, col3 = st.columns(3)
col1.metric("Mediana com bot", f"{num(r['mediana_com_bot'], 1)} h")
col2.metric("Mediana sem bot", f"{num(r['mediana_sem_bot'], 1)} h")
col3.metric("Médias (com × sem)", f"{num(r['media_com_bot'], 1)} × {num(r['media_sem_bot'], 1)} h")

st.markdown(
    f"""
    Nos 60 PRs reais, **os dois testes chegam à mesma conclusão: não rejeitam H₀**
    (Welch p = {num(r['welch_p'], 2)}; Mann-Whitney p = {num(r['mw_p'], 2)}).
    Os tamanhos de efeito são praticamente nulos: g = {num(r['hedges_g'])} e rank-biserial =
    {num(r['rank_biserial'], 3)} (a chance de um PR com bot demorar mais que um sem bot é ~50%).
    A diferença de medianas (6,6 h × 18,5 h) parece grande, mas é frágil: o grupo sem bot é mais
    disperso (tem tanto PRs de minutos quanto de semanas), e o deslocamento "típico" estimado pelo
    Hodges-Lehmann é de só {num(r['hodges_lehmann_h'])} h. Ou seja, **não há efeito com importância prática
    detectável** nesta amostra.
    """
)

with st.expander("Para discutir: tamanho da amostra (extra)"):
    st.pyplot(grafico_poder_por_n(poder_n, r["razao_medias_geometricas"]))
    p30 = poder_n[(poder_n["n"] == 30) & (poder_n["teste"] == "Mann-Whitney")]["poder"].iloc[0]
    st.markdown(
        f"""
        Se o efeito verdadeiro fosse igual ao observado (razão de médias geométricas de
        {num(r['razao_medias_geometricas'])}), o Mann-Whitney teria só **{pct(p30)} de poder** com 30 PRs por grupo,
        e seriam precisos **cerca de 2.000 PRs por grupo** para chegar a 80%. Isso é inviável num único
        repositório e período. Portanto, o resultado não significativo **não prova que o bot não tem
        efeito**: mostra que, se existe, é pequeno demais para esta amostra. Com amostras enormes, o
        contrário vale: até diferenças minúsculas ficam significativas, e aí o que importa é o tamanho do efeito.
        A vantagem do Mann-Whitney não some com n grande nesse cenário (o Welch chega a só
        {pct(poder_n[(poder_n['n'] == 2000) & (poder_n['teste'] == 't de Welch')]['poder'].iloc[0])} com 2.000 PRs),
        porque a cauda pesada da lognormal com sigma ≈ 2,3 continua dominando a variância.
        """
    )


# 7. Conclusão
st.header("7. Conclusão")

st.markdown(
    f"""
    **O que esperávamos:** que o Mann-Whitney se saísse melhor, porque o tempo de merge tem valores extremos.

    **O que encontramos:** a expectativa se confirmou, e com uma diferença maior do que imaginávamos.
    Nos dados com a forma real (assimétricos), o Mann-Whitney manteve o erro tipo I perto de 5% e teve
    poder até ~3 vezes maior que o Welch. O que não esperávamos é que o Welch ficasse **conservador** (e não
    liberal) com assimetria e outliers, e que ele **vencesse por pouco** quando os dados são normais (situação A).
    Ou seja, o não paramétrico não ganha sempre: ganha quando os pressupostos do t são violados.

    **Recomendação:** para comparar o tempo até o merge em horas, usar o **Mann-Whitney**.
    A escolha mudaria (1) se os tempos fossem analisados em escala logarítmica, ou forem aproximadamente
    normais, caso em que o t de Welch é equivalente ou levemente melhor; e (2) se a pergunta fosse sobre a
    **média** em horas (ex.: custo total de espera), que só o t responde, desde que com amostras bem maiores.

    **Limitações:** os grupos vêm de períodos diferentes (fev–abr × jul–set de 2025), então outras mudanças no
    projeto podem explicar diferenças; o estudo é observacional; só 30 PRs por grupo; e a simulação assume o mesmo
    sigma nos dois grupos, enquanto nos dados reais o grupo sem bot é mais disperso. Quando as dispersões diferem,
    o Mann-Whitney deixa de comparar só a "posição" dos grupos, o que deve ser considerado na interpretação.
    """
)

st.caption("LAB04 — Laboratório de Experimentação de Software | Sprint 2 + Entrega final")
