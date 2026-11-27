# Lab05 · Sprint 2 · Análise dos resultados
**Responsável:** Pedro Henrique (Análise e Impacto)

**Resumo:** neste computador, no Cycles em CPU, o Blender 5.2.4 LTS renderizou as duas cenas em média **cerca de 11% mais rápido** que o 4.5.17 LTS, com efeito grande e diferença estatisticamente significativa nas duas cargas. O resultado se mantém ao retirar as repetições com perturbação (seção 5).

---

## 1. Como os resultados foram gerados

```bash
cd scripts
python analyze.py --csv ../../dados/raw_full.csv --versions 4.5 5.2 --out ../../resultados
```

Saídas em `resultados/`:

| Arquivo | Uso |
|---|---|
| `resultados_auto.md` | Tabelas (descritiva, testes, tamanho do efeito, simulação), copiadas na seção 3 |
| `estatisticas_descritivas.csv`, `testes.csv` | Dados das tabelas |
| `boxplot_render.png`, `boxplot_total.png` | Distribuições por versão e carga |
| `render_por_execucao.png` | Checagem de deriva temporal |

**Como ler o sinal:** menor tempo é melhor. Diferença percentual **negativa** = Blender 5.2 mais rápido que o 4.5.

## 2. Pré-condição

- [x] `dados/relatorio_validacao.md` sem problemas pendentes (80 linhas, 20 por célula, todos os processos com código 0, brilho médio entre versões com diferença de 0,5% e 0,6%).
- [ ] Análise rodada sobre o `raw_full.csv` já versionado (conferir o checksum de `dados/raw_full.sha256`).

## 3. Resultados

Execuções analisadas: 80 (20 por versão e carga). α = 0,05; para o tempo de render (métrica primária), α ajustado por Bonferroni = 0,025.

### 3.1 Cena difusa (4 rebatimentos)

**Descritiva (s):**

| Métrica | Versão | n | Média | Desvio | Mediana | Q1 | Q3 | Mín | Máx | CV% |
|---|---|---|---|---|---|---|---|---|---|---|
| Tempo de render | 4.5 | 20 | 13,402 | 0,701 | 13,179 | 13,024 | 13,464 | 12,707 | 15,817 | 5,2 |
| Tempo de render | 5.2 | 20 | 11,908 | 0,328 | 11,910 | 11,628 | 12,096 | 11,391 | 12,842 | 2,8 |
| Tempo total | 4.5 | 20 | 14,556 | 0,776 | 14,298 | 14,150 | 14,585 | 13,893 | 17,259 | 5,3 |
| Tempo total | 5.2 | 20 | 13,358 | 0,349 | 13,344 | 13,074 | 13,534 | 12,851 | 14,396 | 2,6 |

**Testes e efeito:**

| Métrica | Tipo | Teste | p | Limiar | Signif. | Dif. % (5.2 vs 4.5) | IC95% (bootstrap) | Hedges g | Cliff δ |
|---|---|---|---|---|---|---|---|---|---|
| Tempo de render | primária | Mann-Whitney U | 7,9e-08 | 0,025 | sim | −11,14% | [−13,54%; −9,10%] | −2,68 (grande) | −0,99 (grande) |
| Tempo total | secundária | Mann-Whitney U | 3,4e-07 | 0,050 | sim | −8,23% | [−10,71%; −6,12%] | −1,95 (grande) | −0,94 (grande) |

**Leitura:** na cena difusa, o Blender 5.2 levou em média 11,1% menos tempo para renderizar que o 4.5 (11,91 s contra 13,40 s; IC 95% da diferença: −13,5% a −9,1%). A diferença é significativa depois da correção de Bonferroni (p < 0,001) e o efeito é grande (g de Hedges = −2,68; δ de Cliff = −0,99, ou seja, quase todos os renders do 5.2 foram mais rápidos que quase todos os do 4.5).

### 3.2 Cena com vidro e metal (12 rebatimentos)

**Descritiva (s):**

| Métrica | Versão | n | Média | Desvio | Mediana | Q1 | Q3 | Mín | Máx | CV% |
|---|---|---|---|---|---|---|---|---|---|---|
| Tempo de render | 4.5 | 20 | 15,144 | 0,843 | 14,891 | 14,579 | 15,218 | 14,453 | 17,694 | 5,6 |
| Tempo de render | 5.2 | 20 | 13,344 | 0,540 | 13,282 | 13,001 | 13,559 | 12,605 | 15,194 | 4,1 |
| Tempo total | 4.5 | 20 | 16,302 | 0,904 | 16,031 | 15,711 | 16,340 | 15,576 | 19,064 | 5,5 |
| Tempo total | 5.2 | 20 | 14,797 | 0,569 | 14,701 | 14,494 | 14,992 | 14,102 | 16,868 | 3,8 |

**Testes e efeito:**

| Métrica | Tipo | Teste | p | Limiar | Signif. | Dif. % (5.2 vs 4.5) | IC95% (bootstrap) | Hedges g | Cliff δ |
|---|---|---|---|---|---|---|---|---|---|
| Tempo de render | primária | Mann-Whitney U | 6,0e-07 | 0,025 | sim | −11,89% | [−14,51%; −9,31%] | −2,49 (grande) | −0,93 (grande) |
| Tempo total | secundária | Mann-Whitney U | 7,9e-07 | 0,050 | sim | −9,23% | [−11,92%; −6,66%] | −1,95 (grande) | −0,92 (grande) |

**Leitura:** na cena com vidro e metal, o 5.2 levou em média 11,9% menos tempo que o 4.5 (13,34 s contra 15,14 s; IC 95%: −14,5% a −9,3%). A diferença é significativa (p < 0,001) e o efeito é grande (g = −2,49; δ = −0,93). O ganho é parecido com o da cena difusa, então neste experimento a diferença **não** parece depender do tipo de cena.

### 3.3 Tempo total do processo (exploratório)

O tempo total (abrir o Blender, montar a cena, renderizar e salvar) também foi menor no 5.2: −8,2% na cena difusa e −9,2% na de vidro e metal, ambos significativos (sem correção de múltiplas comparações, por ser métrica exploratória). O ganho é menor que o do render porque o 5.2 gasta mais tempo fora do render: a diferença entre tempo total e tempo de render (abertura, montagem da cena e gravação da imagem) foi de cerca de **1,45 s no 5.2 contra 1,15 s no 4.5**, aproximadamente 0,3 s a mais, de forma consistente nas duas cenas. Essa comparação de sobrecarga é descritiva, sem teste formal.

### 3.4 Erro tipo I e poder (tempo de render)

| Carga | n/grupo | Desvio comum (s) | Erro tipo I simulado | Poder (dif. observada) | Poder (dif. 3%) |
|---|---|---|---|---|---|
| diffuse | 20 | 0,547 | 0,057 | 1,00 | 0,61 |
| glass | 20 | 0,708 | 0,057 | 1,00 | 0,49 |

**Interpretação:** o erro tipo I simulado (0,057) ficou perto do nominal de 0,05, então o teste não gera falsos positivos em excesso. Com n = 20 por grupo o poder para detectar a diferença observada (cerca de 11%) é praticamente 1,00. Para uma diferença de apenas 3%, o poder seria de 0,49 a 0,61, ou seja, **diferenças dessa ordem poderiam passar despercebidas**. Esse limite não afeta a conclusão atual, já que a diferença encontrada é muito maior.

**Figuras:** `resultados/boxplot_render.png`, `resultados/boxplot_total.png` e `resultados/render_por_execucao.png`.

## 4. Respostas às perguntas do GQM

| Pergunta | Resposta com base nos dados |
|---|---|
| Q1. Qual versão renderiza mais rápido? | O **Blender 5.2.4 LTS**: −11,1% na cena difusa e −11,9% na cena de vidro e metal, ambos significativos, com efeito grande |
| Q2. A diferença muda o tempo total do processo? | Sim, mas menos: −8,2% e −9,2%. O 5.2 gasta cerca de 0,3 s a mais fora do render (abertura e montagem da cena) |
| Q3. A diferença depende do tipo de cena? | Não de forma relevante: os ganhos nas duas cenas são parecidos (−11,1% e −11,9%) e seus intervalos de confiança se sobrepõem. Não fizemos teste formal de interação |
| Q4. Os resultados são estáveis? (CV%) | Sim. CV% de 2,8% a 5,6% por célula, sempre abaixo do limite de 10%. A variação do 4.5 foi um pouco maior, em parte pela perturbação das repetições 11 e 12 |
| Q5. As duas versões renderizam a mesma imagem? (brilho médio) | Quase. A diferença de brilho médio foi de 0,49% e 0,60%, abaixo do limite de 3%. Ela é constante em todas as repetições, ou seja, as imagens das duas versões não são idênticas, e só checamos o brilho médio (ver ameaças à validade) |

## 5. Escolhas estatísticas e análise de sensibilidade

**Escolha do teste (conforme o plano, sem mudança).** O Shapiro-Wilk rejeitou a normalidade do tempo de render em três dos quatro grupos (4.5/diffuse p < 0,001; 4.5/glass p = 0,0001; 5.2/glass p = 0,0014; 5.2/diffuse passou, p = 0,092). Pela regra definida antes da análise, usamos **Mann-Whitney U** nas comparações. Nenhuma outra escolha foi alterada.

**Análise de sensibilidade (exploratória, feita depois de ver os dados).** Seis execuções foram outliers pela regra de 1,5·IQR, e todas estão nas repetições 11 e 12 (14:09 a 14:11 UTC), nas duas versões: o computador teve uma perturbação momentânea nesse intervalo. Como a ordem embaralhada fez com que 4 dos 6 outliers fossem do 4.5, essas repetições aumentam um pouco a vantagem aparente do 5.2. Para medir isso, repetimos a análise sem as repetições 11 e 12 (n = 18 por grupo). **A análise principal continua sendo a com todos os dados**, como previsto no plano.

| Carga | Dif. % de média, todos os dados (n = 20) | IC95% | Dif. % de média, sem reps 11 e 12 (n = 18) | IC95% |
|---|---|---|---|---|
| diffuse | −11,1% | [−13,5%; −9,1%] | −10,2% | [−11,3%; −9,0%] |
| glass | −11,9% | [−14,5%; −9,3%] | −11,3% | [−12,7%; −9,8%] |

Sem as repetições perturbadas, os tempos ficam mais estáveis (CV% de 2,0% a 2,6%), a normalidade deixa de ser rejeitada, o teste passa a ser t de Welch (pela mesma regra) e a diferença continua significativa (p < 0,001) com δ de Cliff = −1,00. **A conclusão não depende dessas repetições**: a vantagem do 5.2 fica entre cerca de 10% e 12% nas duas análises.