# LAB04: t de Welch × Mann-Whitney

Comparação de dois testes de hipótese no tempo até o merge de Pull Requests (PRs), com e sem bot de revisão.

## Origem dos dados

| Item | Informação |
| --- | --- |
| Repositório analisado | [langflow-ai/langflow](https://github.com/langflow-ai/langflow) |
| Bot de revisão | CodeRabbit (`coderabbitai`) |
| Data da coleta | 04/11/2026 |
| Ferramenta usada | GitHub CLI (`gh`) |
| Grupo `sem_bot` | PRs integrados de 01/02/2025 a 30/04/2025, sem revisão do bot |
| Grupo `com_bot` | PRs integrados de 01/07/2025 a 30/09/2025, com revisão do bot |
| Tamanho da amostra | 30 PRs por grupo, 60 no total |
| Medida coletada | Tempo até o merge, em horas (`mergedAt - createdAt`) |

Os períodos de maio e junho de 2025 ficaram de fora porque foram tratados como uma transição para o uso do bot.

## Como os dados foram coletados

Os PRs foram baixados com os comandos abaixo, executados no PowerShell:

```powershell
gh pr list --repo langflow-ai/langflow --state merged --limit 300 --search "merged:2025-02-01..2025-04-30" --json number,createdAt,mergedAt,author,reviews | Out-File -Encoding utf8 data\prs_antes.json

gh pr list --repo langflow-ai/langflow --state merged --limit 300 --search "merged:2025-07-01..2025-09-30" --json number,createdAt,mergedAt,author,reviews | Out-File -Encoding utf8 data\prs_depois.json
```

Depois, o script `preparar_dados.py` gerou o arquivo `data/prs.csv`:

```powershell
python preparar_dados.py
```

## Regra de escolha dos PRs

1. Foram baixados até 300 PRs integrados de cada período.
2. PRs criados por bots foram removidos.
3. No período anterior, ficaram apenas os PRs sem revisão do `coderabbitai`.
4. No período posterior, ficaram apenas os PRs com revisão do `coderabbitai`.
5. Foram sorteados 30 PRs de cada grupo, com `random_state=42`.

O sorteio evita escolher PRs olhando seus tempos e permite repetir a mesma amostra.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `data/prs_antes.json` | PRs baixados do período sem bot |
| `data/prs_depois.json` | PRs baixados do período com bot |
| `data/prs.csv` | Amostra final, com as colunas `pr`, `grupo` e `tempo_merge_horas` |
| `preparar_dados.py` | Script que filtra os PRs, calcula as horas e sorteia a amostra |

## Limitações

- **Períodos diferentes:** os grupos são de períodos diferentes. A diferença de tempo pode ter outras causas além do bot, como mudanças na equipe ou no projeto.
- **Limite do download:** o comando baixa no máximo 300 PRs por período, não necessariamente todos os PRs integrados.
- **Estudo observacional:** os dados vêm do histórico do projeto, sem sorteio de quais PRs receberiam o bot. Por isso, o estudo não prova que o bot causou uma diferença.
