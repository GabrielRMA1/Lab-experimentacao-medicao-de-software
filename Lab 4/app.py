import os
from pathlib import Path

import streamlit as st


# Define a pasta do projeto como diretório de execução.
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

from graficos import (
    carregar_dados,
    grafico_g1,
    grafico_g2
)


# Configuração da página
st.set_page_config(
    page_title="LAB04 - Testes de Hipótese",
    page_icon="📊",
    layout="wide"
)


# Carregamento dos dados
reais, simulados, resultados = carregar_dados()

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
    projetos com e sem o uso de um bot de revisão.
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


# Limitações
st.divider()

st.subheader("Limitações dos dados")

st.markdown(
    """
    Os grupos foram coletados em períodos diferentes, o que pode
    influenciar os resultados. Mudanças na equipe, no projeto ou
    no processo de desenvolvimento podem explicar parte das diferenças
    observadas, e não necessariamente o uso do bot.

    Além disso, o estudo é observacional e a coleta foi limitada
    a 30 Pull Requests por grupo. Portanto, não é possível afirmar
    que o bot seja a causa de uma eventual diferença no tempo de merge.
    """
)

st.caption(
    "LAB04 — Laboratório de Experimentação de Software | Sprint 1"
)