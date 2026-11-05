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
 