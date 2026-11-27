# Lab05 · Sprint 1 · Plano de coleta e coleta piloto
**Responsável:** Gabriel (Instrumentação e Operação)  
**Software:** Blender 4.5 LTS × 5.2 LTS, renderização no Cycles (CPU), no computador do grupo

---

## 1. Desenho da coleta

| Item | Definição |
|---|---|
| Tratamentos | Blender **4.5 LTS** (referência) e **5.2 LTS** |
| Cargas | `diffuse`: materiais difusos, 4 rebatimentos de luz. `glass`: vidro, metal e superfícies polidas, 12 rebatimentos |
| Cena | Chão com 30 esferas e 2 luzes de área, **gerada por código** (`blender_scene_render.py`, escrito por Leonardo e guardado em `leonardo/scripts/`; o `blender_bench.py` o encontra sozinho), idêntica nas duas versões |
| Células | 2 versões × 2 cargas = **4** |
| Repetições | Piloto: 3 por célula. Coleta completa: **20** por célula (80 renders) |
| Parâmetros fixos | Cycles em CPU, 64 amostras por pixel, 640×360, **4 threads fixas**, denoiser desligado, amostragem adaptativa desligada, semente do Cycles = 0 |
| Execução | Cada render roda em um **processo novo** do Blender. Há 1 render de aquecimento por célula (descartado) e pausa de 3 s entre execuções |
| Ordem | As 4 células são **embaralhadas a cada repetição**, com semente fixa (`--seed 2026`) |
| Métricas coletadas | Tempo de render (s, medido dentro do Blender), tempo total do processo (s), brilho médio da imagem (controle), tempo de montagem da cena |
| Duração | Depende do computador. O comando `check` estima o tempo do piloto e da coleta completa. Na maioria dos computadores fica entre 20 e 60 min |

**Por que aleatorizar a ordem:** se sempre rodássemos a 4.5 antes da 5.2, o aquecimento da CPU prejudicaria sempre a mesma versão. Embaralhando por repetição, esse efeito se espalha entre as versões.

## 2. Preparação (uma vez)

1. **Baixar as duas versões** em https://www.blender.org/download/lts/ . Escolha a LTS **4.5** e depois a **5.2**, e baixe o pacote do seu sistema. No Windows, prefira o **ZIP (portable)**, que não instala nada; basta extrair cada um em uma pasta diferente (ex.: `C:\blender\4.5` e `C:\blender\5.2`). Se só houver instalador, instale as duas em pastas diferentes. Anote a versão exata baixada (ex.: 4.5.17 e 5.2.5).
2. **Python 3** com `pandas`, `scipy`, `numpy` e `matplotlib` (`pip install pandas scipy numpy matplotlib`). Só o Pedro precisa de todas; o Gabriel precisa de `pandas`, `scipy` e `numpy` para validar.
3. **Anotar o caminho do executável** de cada versão:
   - Windows: `C:\blender\4.5\blender.exe`
   - macOS: `/Applications/Blender.app/Contents/MacOS/Blender` (se tiver as duas, renomeie o app de cada versão e use o caminho de cada uma)
   - Linux: `/caminho/blender-4.5.x-linux-x64/blender`
4. **Condições do computador** (mesmas durante toda a coleta): na tomada, modo de energia "melhor desempenho", suspensão desativada, programas pesados fechados, sem atualizações rodando, notebook em superfície que ventile.

## 3. Como rodar

No Windows use `python` (ou `py`) no lugar de `python3`. Os caminhos com espaço vão entre aspas.

```bash
cd gabriel/scripts

# 1) confere os dois Blenders, aquece e ESTIMA a duração
python3 blender_bench.py check --blender 4.5=/caminho/4.5/blender --blender 5.2=/caminho/5.2/blender

# 2) piloto (3 repetições por célula)
python3 blender_bench.py pilot --blender 4.5=/caminho/4.5/blender --blender 5.2=/caminho/5.2/blender
```

Parâmetros úteis (os mesmos nas duas versões e em toda a coleta): `--samples 64`, `--threads 4`, `--reps-full 20`, `--pause 3`. Se o `check` estimar mais de ~90 min para a coleta completa, reduza `--samples` para 32 (e declare isso no documento).

**Se o seu computador tem menos de 4 núcleos**, use `--threads` com o número de núcleos que ele tem e mantenha esse valor.

## 4. Saídas

| Arquivo | Conteúdo |
|---|---|
| `dados/env_snapshot.txt` | Sistema, CPU, núcleos, RAM, versão de cada Blender e parâmetros do experimento |
| `dados/raw_pilot.csv` / `dados/raw_full.csv` | Uma linha por render (campos em `COLUMNS` de `blender_bench.py`) |
| `dados/logs/*.log` | Saída bruta de cada execução do Blender |

## 5. Regras de ética e segurança

- Tudo roda no computador do grupo. **Nenhum teste de carga contra sistema de terceiros.**
- Nenhum dado pessoal e nenhum modelo ou textura de terceiros: a cena é gerada por código.
- Baixar os executáveis **só do site oficial** (blender.org).

## 6. Resultados do piloto

Piloto executado com `blender_bench.py pilot` (3 repetições por célula, 12 renders, mais 1 render de aquecimento por célula, descartado).

| Pergunta | Resposta |
|---|---|
| Os dois Blenders rodaram até o fim sem erro? | Sim. Os 12 renders do piloto terminaram sem erro, e o `check` anterior também passou nas 4 células. |
| Versões exatas usadas (do `env_snapshot.txt`) | Blender **4.5.17 LTS** e **5.2.4 LTS**, ambos Windows x64 (portable), baixados de blender.org. |
| Hardware (CPU, núcleos, RAM, notebook ou desktop) | **Notebook**, Windows 11 (10.0.26200), CPU **Intel Core i7-10510U @ 1,80 GHz** (8 núcleos lógicos, conforme `dados/env_snapshot.txt`), **32 GB de RAM** DDR4 (2667 MT/s). Estava **na tomada** durante o piloto e a coleta. |
| Quanto tempo levou o piloto? E a estimativa da coleta completa? | O piloto levou cerca de 4,5 min (do snapshot, 13:40:38 UTC, ao último render, 13:45:02 UTC, incluindo o aquecimento). Estimativa do `check` para a coleta completa (20 repetições por célula): ~31 min, com os parâmetros padrão. |
| Tempo de render médio por célula (diffuse e glass, 4.5 e 5.2) | Ver tabela abaixo. |
| Variação entre as 3 repetições é razoável (CV% < 10)? | Sim. O maior CV% foi 2,1% (Blender 5.2, cena difusa). |
| O brilho médio da imagem é parecido nas duas versões (diferença < 3%)? | Sim. No `check`, a diferença foi de 0,5% na cena difusa (0,645 × 0,642) e de 0,6% na cena de vidro (0,615 × 0,611). |
| Ajustes feitos depois do piloto (amostras, threads)? | Nenhum. Mantidos 64 amostras, 4 threads, 640×360, 3 s de pausa e semente 2026. |

**Tempo de render no piloto (segundos, n = 3 por célula):**

| Versão | Carga | Média (s) | Desvio (s) | CV% |
|---|---|---|---|---|
| 4.5 | diffuse | 12,91 | 0,07 | 0,5 |
| 5.2 | diffuse | 11,71 | 0,25 | 2,1 |
| 4.5 | glass | 14,36 | 0,12 | 0,8 |
| 5.2 | glass | 13,00 | 0,26 | 2,0 |

**Atenção:** com 3 repetições por célula, esses números servem só para verificar que a coleta funciona e é estável. **Não são resultado do estudo e não devem ser usados para concluir qual versão é mais rápida.** A comparação com teste estatístico é feita na Sprint 2, com 20 repetições por célula.

**Critério para seguir para a coleta completa:** todos os processos com código 0, CV% por célula abaixo de 10%, versões corretas no `blender_version` e brilho médio parecido entre versões. Se o CV% for alto, feche programas em segundo plano, confira a tomada e aumente `--samples` para 128 (renders mais longos diluem o ruído), e repita o piloto.

## 7. Checklist de entrega (Gabriel, S1)

- [ ] Versões 4.5 LTS e 5.2 LTS baixadas e caminhos anotados.
- [ ] `check` executado e `env_snapshot.txt` gerado.
- [ ] Piloto executado e `raw_pilot.csv` versionado no repositório.
- [ ] Tabela da seção 6 preenchida.
- [ ] Hardware do computador anotado.
