## 1. Protocolo da coleta completa

1. Mesmo computador e mesmas condições do piloto (Windows 11, Cycles em CPU).
2. `check` rodado antes, com estimativa de ~31 min para a coleta completa.
3. Coleta executada com `blender_bench.py full` (80 renders: 4 células × 20 repetições), com os parâmetros do piloto, sem alteração:
   ```bash
   cd /scripts
   python blender_bench.py full --blender "4.5=<caminho do blender.exe 4.5.17>" --blender "5.2=<caminho do blender.exe 5.2.4>"
   ```
4. A coleta terminou sem interrupção. Pelos registros do CSV, os renders foram de 13:57:35 UTC a 14:20:56 UTC (cerca de 23,5 min, abaixo da estimativa), sem contar o aquecimento.
5. Validação executada:
   ```bash
   python validate_data.py --csv ../../dados/raw_full.csv --expected-reps 20 \
       --versions 4.5 5.2 --out ../../dados/relatorio_validacao.md
   ```

## 2. O que a validação confere (`validate_data.py`)

- Total de linhas (80) e 20 execuções por célula, sem duplicatas.
- Sem valores ausentes; todos os processos do Blender com código de saída 0; tempos > 0.
- `blender_version` consistente com o rótulo (4.5.x e 5.2.x).
- Parâmetros constantes em toda a coleta (amostras, threads, resolução).
- **Mesma cena nas duas versões:** diferença do brilho médio da imagem entre versões abaixo de 3%.
- CV% do tempo de render por célula (limite de aceitação: 10%) e outliers pela regra de 1,5·IQR.
- Correlação de Spearman entre a ordem de execução e o tempo de render (deriva térmica).

## 3. Resultado da validação

O relatório completo está em `dados/relatorio_validacao.md`. Conclusão do script: **"Nenhum problema encontrado. Dados aptos para análise."**

| Verificação | Resultado |
|---|---|
| Linhas / execuções por célula | 80 linhas; 20 execuções em cada uma das 4 células (4.5/diffuse, 4.5/glass, 5.2/diffuse, 5.2/glass) |
| Valores ausentes, duplicatas, erros de execução | Nenhum. Todos os 80 processos terminaram com código 0 |
| Versões exatas do Blender (`blender_version`) | 4.5.17 LTS e 5.2.4 LTS, conforme o rótulo em todas as linhas |
| Parâmetros constantes | 64 amostras, 4 threads, 640×360 em todas as execuções |
| Brilho médio entre versões (mesma cena?) | diffuse: 0,6450 (4.5) × 0,6419 (5.2), diferença de 0,49%. glass: 0,6147 × 0,6110, diferença de 0,60%. Ambas abaixo do limite de 3% |
| CV% do tempo de render por célula | 4.5/diffuse 5,2%; 4.5/glass 5,6%; 5.2/diffuse 2,8%; 5.2/glass 4,1% (todos abaixo de 10%) |
| Outliers (regra 1,5·IQR) | 6 no total: 4.5/diffuse 2, 4.5/glass 2, 5.2/diffuse 1, 5.2/glass 1. **Todos nas repetições 11 e 12** (ver seção 4) |
| Deriva temporal (rho de Spearman, tempo × ordem) | 4.5/diffuse 0,20 (p = 0,41); 4.5/glass 0,39 (p = 0,09); 5.2/diffuse 0,21 (p = 0,38); 5.2/glass −0,01 (p = 0,97). Nenhuma significativa a 5% |

**Decisão sobre outliers:** **nenhuma execução foi removida.** Os seis outliers estão todos nas repetições 11 e 12 (14:09 a 14:11 UTC) e nas duas versões, o que aponta para uma perturbação momentânea do computador, e não para falha de uma versão. Como não há causa confirmada e documentada, mantemos todos os dados na análise principal, como previsto no plano. A análise sem as repetições 11 e 12 aparece como análise de sensibilidade em `/S2_analise_dos_resultados.md` (seção 5).

## 4. Desvios do plano

| Desvio | Causa | Impacto |
|---|---|---|
| Perturbação momentânea nas repetições 11 e 12 (14:09:14 a ~14:11 UTC, 11:09 a ~11:11 no horário de Brasília): nas execuções afetadas, tempos de cerca de 8% a 20% acima da média das demais repetições | **Causa não confirmada.** O computador não foi usado durante a coleta. É possível que uma notificação ou uma tarefa em segundo plano do Windows tenha consumido CPU nesse intervalo, mas isso não foi verificado e nada nos dados permite afirmar | Atingiu as duas versões, mas a ordem embaralhada fez com que 4 dos 6 outliers fossem do 4.5. Isso favorece levemente o 5.2 na análise principal. Sem as repetições 11 e 12, a diferença entre versões cai de cerca de 11% para cerca de 10% a 11%, e a conclusão não muda |
| Nenhum outro desvio | | A coleta rodou com os parâmetros do piloto e sem interrupção |

## 5. Versionamento dos dados

Estrutura no repositório:

```
dados/
  raw_pilot.csv
  raw_full.csv
  env_snapshot.txt
  relatorio_validacao.md
  raw_full.sha256
  logs/            (saída bruta do Blender de cada execução)
```

- Commit dos dados **antes** da análise, com mensagem do tipo `dados: coleta completa Blender 4.5 x 5.2 (20 reps/célula)`.
- Checksum do CSV (Windows): `certutil -hashfile dados\raw_full.csv SHA256 > dados\raw_full.sha256`. No Linux, `sha256sum dados/raw_full.csv > dados/raw_full.sha256`; no macOS, `shasum -a 256 dados/raw_full.csv > dados/raw_full.sha256`.
- Criar a tag `lab05-s2-dados` no commit.
