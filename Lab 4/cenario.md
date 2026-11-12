# Cenário

**Pergunta:** o bot de revisão altera o tempo até o merge dos PRs?

**Tipo de teste:** bicaudal, porque o bot pode acelerar ou atrasar o merge.

## t de Welch
- **H₀:** a média do tempo até o merge é igual nos dois grupos.
- **H₁:** a média do tempo até o merge é diferente entre os grupos.

## Mann-Whitney
- **H₀:** um PR de um grupo tem a mesma chance de apresentar um tempo de merge maior ou menor que um PR do outro grupo.
- **H₁:** essa chance não é igual entre os grupos.

## Expectativa antes de simular
Esperamos que o Mann-Whitney se saia melhor, porque os tempos de merge costumam apresentar valores extremos (outliers). Esse teste trabalha com as posições dos valores, enquanto o t de Welch compara as médias.

## Como os dados são simulados
Os tempos reais apresentam assimetria à direita: em ambos os grupos, a média ficou acima da mediana. Por isso, usamos uma distribuição lognormal para gerar os tempos simulados, preservando a mediana e a dispersão dos logaritmos observadas nos dados reais.

- **Com bot:** mediana de 6,61 h e sigma de 1,89.
- **Sem bot:** mediana de 18,45 h e sigma de 2,61.

Foram geradas 30 observações simuladas para cada grupo, com semente aleatória 42, para permitir a reprodução dos resultados. O nível de significância adotado foi α = 0,05.

## Interpretação dos resultados
Com α = 0,05, o **t de Welch** apresentou p = 0,1668. Como p ≥ 0,05, **não rejeitamos H₀**. Nesta simulação, não houve evidência estatística suficiente de diferença entre as médias dos grupos.

O **Mann-Whitney** apresentou p = 0,0176. Como p < 0,05, **rejeitamos H₀**. Nesta simulação, houve evidência estatística de diferença entre os grupos segundo esse teste.

Os testes chegaram a decisões diferentes porque avaliam aspectos distintos dos dados: o t de Welch compara médias, enquanto o Mann-Whitney utiliza as posições (ranks) das observações. Essa divergência deve ser registrada, não tratada como erro. Como os dados analisados nesta etapa são simulados, essas conclusões não demonstram que o CodeRabbit altera o tempo de merge no repositório real.

## Limitações dos dados reais
Os grupos foram coletados em períodos diferentes (fevereiro a abril e julho a setembro de 2025). Assim, diferenças observadas podem estar relacionadas a mudanças na equipe, no projeto ou no processo de desenvolvimento, e não necessariamente ao uso do bot. Além disso, o estudo é observacional e a coleta foi limitada a até 300 PRs por período.
