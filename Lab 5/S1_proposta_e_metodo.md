# Lab05 · Sprint 1 · Proposta e Método
**Responsável:** Leonardo (Planejamento e Método)  
**Grupo:** Leonardo, Gabriel, Pedro Henrique  
**Software:** Blender (modelagem, animação e renderização 3D de código aberto), versões **4.5 LTS × 5.2 LTS**

> Partes de Gabriel (plano de coleta e piloto) e de Pedro Henrique (plano de análise) estão nos arquivos deles e entram no pacote da S1 junto com este.

---

## 1. Software escolhido e evidências dos três critérios

**Blender**, programa livre e de código aberto (licença GPL) para modelagem, animação, simulação e renderização 3D. O objeto de pesquisa é o **programa em funcionamento**, rodando no computador do grupo. **Não** minerar commits, issues ou PRs, e não analisar o código-fonte. Os binários são baixados do site oficial (blender.org), e não do GitHub.

| Critério | Evidência | Fonte (acesso em 26/11/2026) |
|---|---|---|
| **Real** | Projeto com site oficial, manual e releases públicos mantidos pela Blender Foundation. | https://www.blender.org/ |
| **Em operação** | As versões LTS hoje mantidas são a **4.5 LTS** (patch 4.5.17, de 23/11/2026, correções críticas até 14/07/2027) e a **5.2 LTS** (patch 5.2.5, de 23/11/2026, correções críticas até 14/07/2028). Cada LTS recebe suporte por 2 anos. A 4.2 LTS já saiu de suporte (16/07/2026), por isso comparamos 4.5 e 5.2. | https://endoflife.date/blender · https://www.blender.org/download/lts/ |
| **Alto impacto** | Em 2023 o Blender foi baixado "quase 18 milhões de vezes" no blender.org, mais cerca de 2 milhões de vezes por Microsoft Store, Steam e Snap. Os sites do projeto recebem mais de 2 milhões de visitas por mês, com 30 milhões de visitantes únicos no ano. Chegou a quase 10 mil usuários simultâneos no Steam em dez/2023. Entre os apoiadores corporativos do Development Fund aparecem AMD, Apple, Meta, Intel e Nvidia. Em 2020, o mesmo relatório anual falava em "mais de 14 milhões" de downloads. | Blender Foundation Annual Report 2023 (publicado em jul/2024), pp. 96-97 e pp. 90-95: https://download.blender.org/foundation/Blender-Foundation-Annual-Report-2023.pdf · "Blender by the Numbers 2020": https://www.blender.org/?p=74959 |

**Ressalvas a escrever com honestidade no documento:**
- **Download não é usuário ativo.** O número mostra alcance, e não quantas pessoas renderizam de fato com o Blender.
- Os números acima são de **2023** (o relatório mais recente que abri). **Antes de entregar, procurar o relatório de 2024 ou posterior no site do Blender** e atualizar. Registrar a data de acesso de cada link.
- Os valores foram extraídos por mim da leitura do relatório e da página. **Conferir página por página no PDF** antes de citar.
- A data de fim de suporte das versões (4.5 e 5.2) vem do endoflife.date, um agregador. **Conferir também em blender.org/download/lts/.**

## 2. Pergunta de pesquisa e caminho

**Pergunta principal (PP):** Em um mesmo computador e com configuração de render idêntica, o **Blender 5.2 LTS** renderiza cenas no **Cycles (CPU)** em tempo diferente do **Blender 4.5 LTS**?

**Caminho:** *rodar o software no ambiente do grupo*, variando a **versão** (tratamento) e o **tipo de cena** (bloco), medindo o tempo de render. É o caminho "Rodar o software no ambiente do grupo" do enunciado, com versões mantidas, como em "Python 3.11 × 3.13" ou "Node.js 20 × 22".

**Quem se interessa pelo resultado:** artistas, estúdios e equipes de render que precisam decidir se migram da LTS 4.5 para a 5.2.

**Extensão prevista para a S3:** transformar a diferença medida em horas de render economizadas (ou perdidas), com cenário explícito e números públicos de uso (seção 5 do enunciado).

## 3. GQM (template de Basili)

**Objetivo (G1):** Analisar *as versões 4.5 LTS e 5.2 LTS do Blender* com o propósito de *comparar* em relação à *eficiência de desempenho (ISO/IEC 25010: comportamento temporal)* do ponto de vista de *artistas e estúdios que decidem sobre migração de versão*, no contexto de *renderizações no Cycles em CPU, em um computador do grupo com configuração fixa*.

| Pergunta | Métrica | Entidade / atributo | Tipo de medida | Escala |
|---|---|---|---|---|
| Q1. Qual versão renderiza mais rápido a mesma cena? | **Tempo de render** (s), medido dentro do Blender em volta do comando de render | Produto (programa); atributo externo (desempenho) | Direta | Razão |
| Q2. A diferença muda o tempo total de uso (abrir o programa, montar a cena e renderizar)? | **Tempo total do processo** (s) | Produto; atributo externo | Direta | Razão |
| Q3. A diferença depende do tipo de cena (difusa × vidro e metal)? | Tempo de render por carga | Produto × recurso (carga) | Derivada (comparação por carga) | Razão |
| Q4. Os resultados são estáveis entre repetições? | **CV%** do tempo de render por célula | Processo de medição | Derivada | Razão |
| Q5 (controle). As duas versões renderizam a mesma imagem? | **Brilho médio** da imagem renderizada | Produto (saída) | Direta | Razão |

**Armadilha de medição (Lei de Goodhart):** se o tempo de render virar a única meta, dá para "ganhar" reduzindo qualidade (ligar denoiser, amostragem adaptativa, baixar amostras). Por isso todos os parâmetros que afetam qualidade são **fixos e idênticos** nas duas versões, e a Q5 confere que a imagem final é equivalente. Essa checagem usa só o brilho médio, que é grosseira e não percebe diferença de ruído (ficará como limitação).  
**Falácia de McNamara:** o tempo de render de uma cena sintética em CPU não representa o uso real (cenas de produção, GPU). Isso entra como limitação de validade externa.

## 4. Hipóteses e variáveis

- **Variável independente (tratamento):** versão do Blender (4.5 LTS, 5.2 LTS).
- **Bloco / segunda variável:** carga de trabalho (`diffuse`: materiais difusos e 4 rebatimentos de luz; `glass`: vidro, metal e superfícies polidas, 12 rebatimentos).
- **Variáveis dependentes:** tempo de render (primária) e tempo total do processo (secundária).
- **Controladas:** computador, número de threads (fixo), cena (gerada por script, igual nas duas versões), amostras por pixel, resolução, denoiser desligado, amostragem adaptativa desligada, semente do Cycles, pausa entre execuções, aquecimento descartado.
- **Unidade experimental:** uma execução do Blender renderizando um quadro (20 por célula).

Para cada carga *c* ∈ {diffuse, glass}:
- **H0(c):** μtempo(5.2, c) = μtempo(4.5, c)
- **H1(c):** μtempo(5.2, c) ≠ μtempo(4.5, c) (bilateral; não assumimos de antemão que a nova é mais rápida)
- Para o tempo total, as hipóteses são análogas e tratadas como exploratórias.

Nível de significância 0,05, com correção de Bonferroni para as duas cargas na métrica primária (α = 0,025). O plano estatístico completo está no arquivo de Pedro Henrique.

## 5. As 7 categorias de pesquisa (primeira versão)

> Ajustar a nomenclatura exata ao vocabulário dos slides da Aula 8. As justificativas valem mesmo que o rótulo mude. A versão final sai revisada na S3.

| Categoria | Classificação | Justificativa |
|---|---|---|
| **Natureza** | Aplicada | O resultado serve a uma decisão prática: migrar ou não da LTS 4.5 para a 5.2 para renderizar. |
| **Objetivos** | Explicativa (com componente descritivo) | Busca relação de causa e efeito entre a versão e o tempo de render, além de descrever os tempos medidos. |
| **Abordagem** | Quantitativa | Métricas numéricas de razão e estatística inferencial. |
| **Procedimentos** | Experimental (experimento em laboratório) | A versão é manipulada pelo grupo e o ambiente é montado e controlado por nós. |
| **Tempo** | Transversal | A coleta acontece em uma janela curta, sem acompanhar o programa por semanas. |
| **Controle** | Experimento controlado | Tratamento manipulado, parâmetros fixos, ordem das execuções aleatorizada e reprodutível (semente registrada). |
| **Nível de evidência** | Alto para o ambiente testado; baixo para generalização | Experimento controlado dá boa validade interna, mas um único computador, só CPU e cenas sintéticas limitam a validade externa. |

## 6. Conceitos da disciplina teórica aplicados

- **GQM:** seção 3.
- **Entidades e atributos:** produto (programa), atributo externo (desempenho), medidas diretas (tempos) e derivadas (CV%, diferença percentual).
- **Escalas:** razão, o que permite média, desvio padrão e razão entre valores.
- **Métricas de produto:** ISO/IEC 25010, característica *eficiência de desempenho*.
- **Armadilhas:** Goodhart e McNamara (seção 3).
- **Ameaças à validade:** arquivo `S2_ameacas_validade_e_integracao.md`.

## 7. O que reaproveitamos dos laboratórios anteriores

| Lab | Reaproveitamento |
|---|---|
| Lab01 | Coleta automatizada de dados (script) e organização do trabalho no GitHub Projects. |
| Lab02 | Lógica de desenho de experimento: tratamentos, repetições e comparação entre grupos. |
| Lab04 | Escolha do teste de hipótese, simulação de erro tipo I e poder (no script `analyze.py`). |

## 8. Ética e licença

Todo o experimento roda **no computador do próprio grupo**. Não há teste de carga em sistema de terceiros, dados pessoais nem participantes humanos. A cena de teste é **criada por nós, por código**, sem usar modelos ou texturas de terceiros. O Blender é distribuído sob a licença GPL, e baixamos os executáveis oficiais do site do projeto.

