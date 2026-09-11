# Desenho do Experimento Controlado (S01)

**Disciplina:** Laboratório de Experimentação de Software  
**Professor:** Danilo Maia  
**Trabalho:** Assistentes de IA vs. codificação manual  

---

## 1. GQM (Goal-Question-Metric)

* **Goal:** Analisar o uso de assistentes de IA generativa (Claude 3.5 Sonnet / GitHub Copilot) na resolução de tarefas de programação, com o propósito de comparar seu efeito frente à codificação manual, com respeito a tempo de resolução, qualidade funcional (defeitos) e qualidade estrutural do código produzido, do ponto de vista do grupo pesquisador, no contexto de katas de dificuldade equivalente resolvidos por estudantes de graduação sob condições controladas (crossover within-subject, time-boxed de 35 minutos).
* **Questions:**
  * **RQ1:** O uso de assistente de IA reduz o tempo necessário para resolver uma tarefa de programação?
  * **RQ2:** O uso de assistente de IA reduz a quantidade de defeitos (testes que falham) no código produzido?
  * **RQ3:** O uso de assistente de IA altera a complexidade ciclomática ou a duplicação do código produzido?

---

## 2. Detalhamento do Experimento (Itens A–H)

### (A) Hipóteses Nula ($H_0$) e Alternativa ($H_1$)

* **RQ1 (Tempo):**
  * $H_{0,1}$: Não há diferença na mediana do tempo até passar em todos os testes (`time-to-green`) entre o uso de IA e a codificação manual. ($MD_{IA} = MD_{Manual}$)
  * $H_{1,1}$: O uso de IA reduz a mediana do tempo `time-to-green` em comparação à codificação manual. ($MD_{IA} < MD_{Manual}$)

* **RQ2 (Defeitos / Qualidade Funcional):**
  * $H_{0,2}$: Não há diferença na taxa de sucesso (% de testes passando ao final do time-box) entre as soluções com IA e manuais.
  * $H_{1,2}$: A taxa de sucesso das soluções produzidas com IA é maior do que as produzidas manualmente.

* **RQ3 (Estrutura do Código):**
  * $H_{0,3a}$: Não há diferença na Complexidade Ciclomática / WMC (via CK) do código gerado com IA vs. manual.
  * $H_{1,3a}$: O código gerado com IA apresenta maior ou menor complexidade em relação ao manual.
  * $H_{0,3b}$: Não há diferença na porcentagem de linhas duplicadas (via PMD CPD) do código gerado com IA vs. manual.
  * $H_{1,3b}$: O uso de IA altera o nível de duplicação de código.

---

### (B) Variáveis Dependentes e Métricas

1. **Tempo até passar nos testes (`time-to-green`):** Medido em segundos via script `timer.py`. Casos que estourarem o time-box de 35 minutos serão marcados como **censurados em 2100s (35 min)**.
2. **Taxa de Sucesso (% de testes passando):** $\frac{\text{Testes Passando}}{\text{Total de Testes do Kata}} \times 100$ ao término do tempo.
3. **Complexidade Ciclomática / WMC:** Extraída via ferramenta **CK** (`ck.jar`).
4. **Duplicação de Código:** Medida em tokens/linhas duplicadas via **PMD CPD**.
5. **Métrica de Controle (LOC):** Contagem total de linhas de código (extraída via CK) para normalizar métricas de complexidade e duplicação.

---

### (C) Variável Independente

* **Uso de Assistente de IA Generativa** durante o desenvolvimento da solução do kata.

---

### (D) Tratamentos

1. **Tratamento $T_{IA}$ (Com IA):** Desenvolvimento com auxílio do assistente de IA selecionado (Claude / Copilot).
2. **Tratamento $T_{MANUAL}$ (Sem IA):** Desenvolvimento 100% manual, utilizando apenas documentação oficial da linguagem e IDE sem recursos autocompletar inteligentes por LLM.

---

### (E) Objetos Experimentais (6 Katas Java)

Seis katas em Java 17 com testes automatizados pré-existentes via **JUnit 5**:
1. **Kata 1:** *Roman Numerals Converter* (Conversão de arábicos para romanos)
2. **Kata 2:** *Bowling Game Score* (Cálculo de pontuação de boliche)
3. **Kata 3:** *Custom FizzBuzz Builder* (FizzBuzz com regras dinâmicas parametrizáveis)
4. **Kata 4:** *String Calculator* (Calculadora de strings com delimitadores customizados)
5. **Kata 5:** *Poker Hand Evaluator* (Classificação de mãos de poker)
6. **Kata 6:** *Luhn Algorithm Validator* (Validação e geração de dígito verificador de cartão)

---

### (F) Projeto Experimental

* **Design:** *Crossover within-subject*, contrabalanceado.
* Todos os 3 integrantes do grupo realizarão **todos os 6 katas**, garantindo controle sobre variação individual de habilidade.

---

### (G) Quantidade de Medições e Esquema de Contrabalanceamento

* **Total de Trials:** $3 \text{ participantes} \times 6 \text{ katas} = \mathbf{18 \text{ trials}}$.
* Matriz de distribuição dos tratamentos (Square-like Crossover):

| Participante | Kata 1 | Kata 2 | Kata 3 | Kata 4 | Kata 5 | Kata 6 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **P1** | Com IA | Sem IA | Com IA | Sem IA | Com IA | Sem IA |
| **P2** | Sem IA | Com IA | Sem IA | Com IA | Sem IA | Com IA |
| **P3** | Com IA | Com IA | Sem IA | Sem IA | Com IA | Sem IA |

*Cada participante fará exatamente 3 katas Com IA e 3 katas Sem IA.*

---

### (H) Ameaças à Validade e Mitigações

1. **Efeito de Aprendizado (Learning Effect):**
   * *Ameaça:* Resolver o mesmo kata pela segunda vez causa viés de aprendizado.
   * *Mitigação:* O desenho é *within-subject* entre katas diferentes, mas cada participante resolve cada kata **uma única vez** no tratamento sorteado na tabela acima.
2. **Memorização das IAs (Data Leakage / Training Bias):**
   * *Ameaça:* Katas muito famosos (ex: LeetCode Easy clássico) podem ter a solução idêntica na base de treino da IA.
   * *Mitigação:* As katas foram adaptadas/customizadas com assinaturas e requisitos levemente modificados em relação aos enunciados padrões.
3. **Familiaridade Prévia dos Integrantes:**
   * *Ameaça:* Um integrante ser muito mais rápido com a ferramenta de IA ou com Java.
   * *Mitigação:* Utilização do modelo *within-subject* com análise pareada não paramétrica (Teste de Wilcoxon).
4. **Censura de Tempo (Time-box):**
   * *Ameaça:* Descartar trials incompletos distorce os resultados a favor do tratamento com mais falhas.
   * *Mitigação:* Manutenção rígida do time-box de 35 min e registro formal como dados censurados.