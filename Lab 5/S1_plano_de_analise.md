# Lab05 · Sprint 1 · Plano de análise
**Responsável:** Pedro Henrique (Análise e Impacto)  
**Software:** Blender 4.5 LTS × 5.2 LTS (Cycles em CPU)

---

## 1. Dados e escalas das métricas

| Métrica | Papel | Escala | Estatísticas permitidas |
|---|---|---|---|
| **Tempo de render** (s) | Primária | Razão | Média, desvio, mediana, razão entre valores, testes paramétricos e não paramétricos |
| **Tempo total do processo** (s) | Secundária (exploratória) | Razão | Idem |
| CV% do tempo de render | Qualidade da medição | Razão | Descritiva |
| Brilho médio da imagem | Controle (mesma cena?) | Razão | Descritiva |
| Versão (4.5, 5.2) | Fator | Nominal | Contagem, agrupamento |
| Carga (diffuse, glass) | Bloco | Nominal | Contagem, agrupamento |

Unidade de análise: **uma execução** do Blender (80 no total, 20 por célula). **Menor tempo é melhor**, então uma diferença percentual negativa significa que a versão 5.2 é mais rápida.

## 2. Plano de análise

Comparação **4.5 × 5.2, separadamente para cada carga** (as cargas medem coisas diferentes e não devem ser misturadas).

1. **Estatística descritiva** por célula: n, média, desvio, mediana, quartis, mínimo, máximo, CV%.
2. **Gráficos:** boxplot com pontos individuais por carga (tempo de render e tempo total) e tempo de render por ordem de execução (checagem de deriva).
3. **Teste de hipótese (tempo de render, 2 testes):**
   - Shapiro-Wilk em cada grupo (α = 0,05).
   - Se os dois grupos forem compatíveis com a normal → **t de Welch** (não assume variâncias iguais).
   - Caso contrário → **Mann-Whitney U**.
   - Bilateral. **α ajustado por Bonferroni: 0,05 / 2 = 0,025**, porque são duas comparações primárias.
4. **Tempo total:** mesmo procedimento, mas declarado **exploratório** (α = 0,05, sem correção).
5. **Tamanho do efeito:**
   - **g de Hedges**, classes: < 0,2 desprezível, < 0,5 pequeno, < 0,8 médio, ≥ 0,8 grande.
   - **δ de Cliff** (não paramétrico), classes: < 0,147 desprezível, < 0,33 pequeno, < 0,474 médio, ≥ 0,474 grande.
   - **IC 95% bootstrap (10.000 reamostragens)** da diferença percentual de médias (5.2 vs 4.5).
6. **Erro tipo I e poder (reaproveita o Lab04):** simulação com o desvio observado e n = 20 por grupo, estimando (a) a taxa de falsos positivos sob H0 e (b) o poder para detectar a diferença observada e uma diferença de 3%.

**Por que Welch e não t de Student:** não precisamos assumir variâncias iguais entre versões, e o custo em poder é desprezível.

**Por que esta família de testes e não ANOVA:** o interesse está na comparação entre duas versões dentro de cada carga. Se o grupo quiser testar interação versão × carga, a opção é ANOVA fatorial 2×2 (ou equivalente robusto). Fica como extensão.

## 3. Regras para evitar armadilhas

- **Não escolher o teste depois de ver o resultado.** A regra de decisão acima é fixa.
- **Não remover outliers para "melhorar" o p-valor.** Só com causa documentada e mostrando a análise com e sem.
- **Não concluir "sem diferença" a partir de p > α.** Consultar o IC e o poder.
- **Reportar sempre** p-valor, tamanho do efeito e IC, e não só "significativo".
- **Se a validação indicar que as imagens diferem entre versões**, a comparação de tempos perde sentido e isso precisa ser dito antes de qualquer conclusão.

## 4. Estimativa de impacto (plano para a S3)

Converter a diferença medida em algo palpável, deixando as premissas explícitas:

```
variação relativa do tempo de render   = Δ%   (IC 95%)
horas de render por mês (cenário)      = H      <- PREMISSA DECLARADA, não é fato
horas economizadas por mês             = H × (−Δ%)
```

Dados públicos para contextualizar **o alcance** do programa: cerca de 18 milhões de downloads em 2023 no blender.org (Blender Foundation Annual Report 2023, pp. 96-97). **Atenção:** download não é quantidade de renders nem de usuários ativos, então não multiplicar Δ% por 18 milhões. O número de horas H precisa vir de um cenário declarado ("um estúdio pequeno que renderiza 500 horas de CPU por mês…") ou de uma fonte pública sobre uso real. A conclusão será dada como **estimativa condicional**, nunca como fato geral sobre todos os usuários do Blender.

## 5. Ferramentas

- `scripts/analyze.py`: roda tudo acima a partir de `dados/raw_full.csv` e grava tabelas e figuras em `resultados/`.
- Bibliotecas: `pandas`, `numpy`, `scipy`, `matplotlib` (`pip install pandas numpy scipy matplotlib`).
- Comando: `python3 analyze.py --csv ../../dados/raw_full.csv --versions 4.5 5.2 --out ../../resultados`.

**O script foi testado apenas com dados sintéticos** (para checar o código). Nenhum tempo de render real do Blender foi produzido ainda.