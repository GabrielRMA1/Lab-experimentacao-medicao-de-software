# Relatório de validação dos dados

Arquivo: `..\..\dados\raw_full.csv`  |  linhas: 80

## Verificações

- [OK] 80 linhas (esperado 80)
- [OK] sem valores ausentes nas métricas
- [OK] todos os processos do Blender terminaram com código 0
- [OK] todos os tempos de render > 0
- [OK] sem execuções duplicadas
- [OK] a versão real do Blender confere com o rótulo em todas as linhas
- [OK] parâmetro 'samples' constante (64)
- [OK] parâmetro 'threads' constante (4)
- [OK] parâmetro 'resolution' constante (640x360)
- [OK] Blender 4.5/diffuse: 20 execuções
- [OK] Blender 4.5/glass: 20 execuções
- [OK] Blender 5.2/diffuse: 20 execuções
- [OK] Blender 5.2/glass: 20 execuções

## Mesma cena nas duas versões? (brilho médio da imagem renderizada)

O Cycles usa a mesma semente, então a imagem deve ser muito parecida entre versões. Uma diferença grande indica que as versões não estão renderizando a mesma coisa.

| Carga | média 4.5 | média 5.2 | diferença relativa |
|---|---|---|---|
| diffuse | 0.6450 | 0.6419 | 0.49% |
| glass | 0.6147 | 0.6110 | 0.60% |

## Variabilidade e outliers por célula (tempo de render, s)

| Versão | Carga | n | média | desvio | CV% | outliers (regra 1,5·IQR) |
|---|---|---|---|---|---|---|
| 4.5 | diffuse | 20 | 13.40 | 0.70 | 5.2 | 2 |
| 4.5 | glass | 20 | 15.14 | 0.84 | 5.6 | 2 |
| 5.2 | diffuse | 20 | 11.91 | 0.33 | 2.8 | 1 |
| 5.2 | glass | 20 | 13.34 | 0.54 | 4.1 | 1 |

## Deriva temporal (tempo de render x ordem global de execução)

Correlação de Spearman entre a ordem de execução e o tempo de render, por célula. |rho| alto sugere aquecimento ou degradação do computador ao longo da coleta.

- Blender 4.5/diffuse: rho = 0.20 (p = 0.409)
- Blender 4.5/glass: rho = 0.39 (p = 0.092)
- Blender 5.2/diffuse: rho = 0.21 (p = 0.376)
- Blender 5.2/glass: rho = -0.01 (p = 0.970)

## Conclusão

Nenhum problema encontrado. Dados aptos para análise.
