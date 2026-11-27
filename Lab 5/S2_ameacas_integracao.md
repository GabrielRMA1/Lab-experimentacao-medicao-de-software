# Lab05 · Sprint 2 · Ameaças à validade e integração
---

## 1. Ameaças à validade (quatro tipos) e mitigação

### 1.1 Validade de conclusão (a conclusão estatística é confiável?)

| Ameaça | Como aparece aqui | Mitigação |
|---|---|---|
| Baixo poder estatístico | Com n = 20 por grupo só se detectam diferenças moderadas. Diferenças de 1 a 3% podem passar despercebidas. | Simulação de poder em `analyze.py`; relatar o poder; se baixo, dizer que "não significativo" não é "sem diferença". |
| Violação das premissas do teste | O tempo de render pode não ser normal (cauda longa quando o computador "engasga"). | Shapiro-Wilk antes de escolher entre t de Welch e Mann-Whitney. |
| Múltiplas comparações | Duas cargas (e duas métricas). | Bonferroni na métrica primária; tempo total declarado exploratório. |
| Variabilidade alta | Ruído do sistema operacional e da CPU. | CV% por célula, regra de outliers e correlação com a ordem de execução (`validate_data.py`). |
| Confiar só no p-valor | p pequeno com efeito irrelevante. | Reportar tamanho do efeito (Hedges g, Cliff δ) e IC95% bootstrap da diferença percentual. |

### 1.2 Validade interna (a diferença se deve mesmo à versão?)

| Ameaça | Como aparece aqui | Mitigação |
|---|---|---|
| Aquecimento e redução de clock da CPU | Em notebooks, renders longos esquentam a CPU e ela reduz a frequência; quem roda por último é prejudicado. É a maior ameaça deste experimento. | Ordem das 4 células embaralhada a cada repetição (semente fixa); pausa entre execuções; computador na tomada; gráfico do tempo × ordem e correlação de Spearman. |
| Processos em segundo plano | Navegador, antivírus ou atualizações disputam a CPU. | Fechar programas; mesma máquina para toda a coleta; registrar desvios. |
| Primeira execução mais lenta | Cache de disco frio. | Aquecimento descartado de cada célula antes da coleta. |
| Imagem diferente entre versões | Padrões do Cycles ou nomes de parâmetros mudam entre versões e a cena renderizada deixa de ser a mesma. | Cena gerada por código, com parâmetros de qualidade explícitos; checagem do brilho médio da imagem entre versões (`validate_data.py`). |
| Número de threads | Padrão do Cycles muda com a máquina. | Threads fixas (`--threads`), iguais nas duas versões. |
| Reaproveitamento de dados na memória | O Blender mantém dados entre renders. | Cada execução é um processo novo do Blender, e a persistência de dados está desligada. |

### 1.3 Validade de construto (as métricas medem o que queremos?)

| Ameaça | Como aparece aqui | Mitigação |
|---|---|---|
| Tempo de render como proxy de "desempenho" | Não captura uso de memória, qualidade nem tempo de visualização na janela. | Medir também o tempo total do processo; declarar que outros atributos da ISO/IEC 25010 não foram avaliados. |
| Lei de Goodhart | Tempo menor pode vir de qualidade menor. | Todos os parâmetros de qualidade fixos; Q5 confere a imagem. O brilho médio é grosseiro e não percebe ruído, e isso é declarado. |
| Cena sintética | Uma grade de esferas não é uma cena de produção. | Duas cargas distintas (difusa e vidro e metal); limitação explícita. |
| Tempo dentro do Blender | O cronômetro mede o comando de render, sem a abertura do programa. | O tempo total do processo é medido à parte pelo script de coleta. |

### 1.4 Validade externa (o resultado vale além deste experimento?)

| Ameaça | Como aparece aqui | Mitigação |
|---|---|---|
| Um único computador | Outra CPU pode favorecer outra versão. | Registrar o hardware (notebook com Intel Core i7-10510U e 32 GB de RAM, em `env_snapshot.txt`) e **não** extrapolar tempos absolutos. Um processador de notebook pode se comportar de forma diferente de um desktop ou servidor. |
| Apenas CPU | A maior parte dos artistas renderiza em GPU (e usa Eevee também). | Limitar a conclusão ao Cycles em CPU. |
| Duas cenas, baixa resolução | Produção usa cenas e resoluções muito maiores, com texturas, volumes e simulações. | Declarar a limitação. |
| Duas versões específicas | O resultado vale para 4.5.x e 5.2.x testadas, e patches novos podem mudar. | Registrar a versão exata de cada execução (`blender_version` no CSV). |
| Impacto extrapolado | Converter a diferença medida em horas economizadas por todos os usuários. | Na S3, apresentar como estimativa condicional, com premissas explícitas. O número de downloads não mede quantas pessoas renderizam. |

## 2. Integração do pacote da S2

## 3. Revisão de coerência final

Revisão feita com o `relatorio_validacao.md`, o `resultados_auto.md` e os demais documentos do grupo.

- [x] **Os resultados respondem às perguntas Q1 a Q5 do GQM?** Sim: as respostas estão na seção 4 de `S2_analise_dos_resultados.md`.
- [x] **O teste usado corresponde ao plano?** Sim. O Shapiro-Wilk rejeitou a normalidade em 3 dos 4 grupos de tempo de render, e o plano mandava usar Mann-Whitney nesse caso. Nenhuma escolha estatística foi alterada depois de ver os dados. A análise sem as repetições 11 e 12 foi feita depois de ver os dados e está declarada como sensibilidade, não como análise principal.
- [x] **Alguma conclusão ultrapassa o que o desenho permite?** A conclusão abaixo fala de "neste computador, no Cycles em CPU, nestas duas cenas e nestas duas versões", e não afirma nada sobre GPU, outros computadores ou cenas de produção.
- [x] **"Não significativo" sem citar o poder?** Não se aplica: as duas comparações primárias foram significativas. O poder para uma diferença de 3% (0,49 a 0,61) está declarado como limite.
- [x] **A validação apontou algo que virou ameaça concreta?** Sim, quatro pontos (tabela abaixo).

### O que os dados mostraram sobre as ameaças previstas

| Ameaça (seção 1) | O que aconteceu |
|---|---|
| Aquecimento e redução de clock da CPU | Não houve deriva significativa: rho de Spearman entre −0,01 e 0,39, todos com p ≥ 0,09. A ordem embaralhada e a pausa de 3 s cumpriram o papel |
| Processos em segundo plano | Houve uma **perturbação momentânea nas repetições 11 e 12** (14:09 a 14:11 UTC): os 6 outliers estão todos lá, nas duas versões. Como a ordem é aleatória, 4 dos 6 caíram no 4.5, o que inflou levemente a vantagem do 5.2. Sem essas repetições a diferença vai de cerca de 11% para cerca de 10% a 11%, e a conclusão não muda. A causa não foi confirmada: o computador não foi usado nesse intervalo, e uma notificação ou tarefa de segundo plano do Windows é uma possibilidade não verificada |
| Imagem diferente entre versões | O brilho médio difere 0,5% (cena difusa) e 0,6% (vidro e metal), sempre igual em todas as repetições. Isso significa que as imagens **não são idênticas**. A diferença é pequena e abaixo do nosso limite de 3%, mas só checamos o brilho médio, que não detecta diferença de ruído nem de detalhe. Parte da diferença de tempo pode vir de mudanças no que o Cycles calcula, e não só de velocidade |
| Violação das premissas do teste | Confirmada: a normalidade foi rejeitada em 3 de 4 grupos, o que justificou o Mann-Whitney |

**Conclusão preliminar do grupo:** neste computador (Windows 11, Intel com 8 núcleos lógicos), no Cycles em CPU com 64 amostras e 4 threads, o Blender **5.2.4 LTS** renderizou as duas cenas de teste em média **cerca de 11% mais rápido** que o **4.5.17 LTS**: −11,1% na cena difusa (IC 95% [−13,5%; −9,1%]) e −11,9% na cena de vidro e metal (IC 95% [−14,5%; −9,3%]), com p < 0,001 após a correção de Bonferroni e efeito grande (g de Hedges de −2,7 e −2,5). O resultado se mantém (−10,2% e −11,3%) sem as repetições com perturbação. O tempo total do processo teve ganho menor (−8% a −9%), porque o 5.2 gasta cerca de 0,3 s a mais para abrir e montar a cena. Esses números valem para este computador, só para renderização em CPU e para estas duas cenas sintéticas, e não devem ser generalizados para GPU, outros computadores ou cenas de produção.

## 4. Código desta parte: verificação de integridade

`verificar_integridade.py` confere o pacote antes da análise e da entrega, usando só a biblioteca padrão do Python:

1. o SHA-256 de `dados/raw_full.csv` contra `dados/raw_full.sha256` (aceita o formato do `certutil`, do `sha256sum` e do `shasum`);
2. 80 linhas, 20 execuções em cada uma das 4 células, código de saída 0 e versões do Blender coerentes com o rótulo;
3. a existência dos arquivos que a integração da S2 exige (seção 2).

```bash
cd /scripts
python verificar_integridade.py --dados ../../dados --raiz ../.. --expected-reps 20 --versions 4.5 5.2
```

Ele termina com código 0 quando tudo confere e com código 1 quando algo falha. Rodado sobre o pacote final (dados da coleta e arquivos das três pessoas), todas as verificações passaram. Ao alterar o CSV de propósito, o script acusou a diferença de checksum e de número de linhas. Ele **não substitui** o `validate_data.py`, que checa a qualidade dos tempos (CV%, outliers, deriva): este só garante que o pacote está completo e não foi alterado.
