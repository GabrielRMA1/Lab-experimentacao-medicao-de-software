# Resultados da análise: Blender 4.5 (referência) x 5.2 (gerado por analyze.py)

Execuções analisadas: 80 (fase `full`). Alfa = 0.05; para a métrica primária (tempo de render), alfa ajustado por Bonferroni = 0.025. **Menor tempo é melhor: diferença negativa significa que o Blender 5.2 é mais rápido.**

## Cena difusa (4 rebatimentos)

### Estatística descritiva

| Métrica | Versão | n | Média | Desvio | Mediana | Q1 | Q3 | Mín | Máx | CV% |
|---|---|---|---|---|---|---|---|---|---|---|
| render_s | 4.5 | 20 | 13.402 | 0.701 | 13.179 | 13.024 | 13.464 | 12.707 | 15.817 | 5.2 |
| render_s | 5.2 | 20 | 11.908 | 0.328 | 11.910 | 11.628 | 12.096 | 11.391 | 12.842 | 2.8 |
| total_s | 4.5 | 20 | 14.556 | 0.776 | 14.298 | 14.150 | 14.585 | 13.893 | 17.259 | 5.3 |
| total_s | 5.2 | 20 | 13.358 | 0.349 | 13.344 | 13.074 | 13.534 | 12.851 | 14.396 | 2.6 |

### Testes de hipótese e tamanho do efeito

| Métrica | Tipo | Teste | p | Limiar | Signif. | Dif. % (5.2 vs 4.5) | IC95% (bootstrap) | Hedges g | Cliff δ |
|---|---|---|---|---|---|---|---|---|---|
| render_s | primária | Mann-Whitney U | 7.898e-08 | 0.025 | sim | -11.14% | [-13.54%; -9.10%] | -2.68 (grande) | -0.99 (grande) |
| total_s | secundária | Mann-Whitney U | 3.416e-07 | 0.050 | sim | -8.23% | [-10.71%; -6.12%] | -1.95 (grande) | -0.94 (grande) |

## Cena com vidro e metal (12 rebatimentos)

### Estatística descritiva

| Métrica | Versão | n | Média | Desvio | Mediana | Q1 | Q3 | Mín | Máx | CV% |
|---|---|---|---|---|---|---|---|---|---|---|
| render_s | 4.5 | 20 | 15.144 | 0.843 | 14.891 | 14.579 | 15.218 | 14.453 | 17.694 | 5.6 |
| render_s | 5.2 | 20 | 13.344 | 0.540 | 13.282 | 13.001 | 13.559 | 12.605 | 15.194 | 4.1 |
| total_s | 4.5 | 20 | 16.302 | 0.904 | 16.031 | 15.711 | 16.340 | 15.576 | 19.064 | 5.5 |
| total_s | 5.2 | 20 | 14.797 | 0.569 | 14.701 | 14.494 | 14.992 | 14.102 | 16.868 | 3.8 |

### Testes de hipótese e tamanho do efeito

| Métrica | Tipo | Teste | p | Limiar | Signif. | Dif. % (5.2 vs 4.5) | IC95% (bootstrap) | Hedges g | Cliff δ |
|---|---|---|---|---|---|---|---|---|---|
| render_s | primária | Mann-Whitney U | 6.015e-07 | 0.025 | sim | -11.89% | [-14.51%; -9.31%] | -2.49 (grande) | -0.93 (grande) |
| total_s | secundária | Mann-Whitney U | 7.948e-07 | 0.050 | sim | -9.23% | [-11.92%; -6.66%] | -1.95 (grande) | -0.92 (grande) |

## Simulação de erro tipo I e poder (tempo de render)

| Carga | n/grupo | Desvio comum (s) | Erro tipo I simulado | Poder (dif. observada) | Poder (dif. 3%) |
|---|---|---|---|---|---|
| diffuse | 20 | 0.547 | 0.057 | 1.00 | 0.61 |
| glass | 20 | 0.708 | 0.057 | 1.00 | 0.49 |

Figuras: `boxplot_render.png`, `render_por_execucao.png`, `boxplot_total.png`.
