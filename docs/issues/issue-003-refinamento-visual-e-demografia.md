# ISSUE-003: Refinamento Visual Paper Desktop 1:1 & Heurísticas Demográficas Locais (v2.0.0)

* **Status:** Done
* **Responsável:** Claude Code
* **Fase:** Fase 2 — Meio (Execução de Micro-Issue)
* **Arquivos-Alvo:**
  - `src/app.py` (Injeção de CSS sob medida e Bento Grid 10/10)
  - `src/features/analise/demographics.py` (Motor de inferência de gênero e DDDs)
  - `tests/test_demographics.py`
* **Dependências:** ISSUE-002 concluída

---

## 1. Objetivo da Issue
1. **Polimento Visual 10/10 (Paper Desktop):** Elevar a interface do Streamlit (`src/app.py`) para o padrão editorial premium do Paper Desktop via injeção de CSS limpo e modular, aplicando os tokens do Design System Dodô.
2. **Motor de Demografia Local (`demographics.py`):** Processar nomes de comentaristas contra a base do IBGE (`data/names_seed.json`) para estimar distribuição de gênero (% Feminino / % Masculino / % Indeterminado com cobertura explícita) e cruzar DDDs contra `data/ddd_uf.json` para regionalização por estado.

---

## 2. Requisitos Técnicos e Implementação

### 2.1 Refinamento Visual & CSS Injection (`src/app.py`):
- **Fundo & Superfície:** Background geral Cannoli (`#F5F4EC`), cards com fundo branco suave (`#FFFFFF` ou `#FAF9F5`), bordas `1px solid #E5E0D8`, `border-radius: 12px`, padding harmonioso e sombras sutis (`0 2px 8px rgba(0,0,0,0.04)`).
- **Cores de Ação:** Botões primários e destaques em Vermelho Haute (`#810100`) com texto branco `#FFFFFF`.
- **Tipografia:** Importar e aplicar via Google Fonts:
  * Títulos e Cabeçalhos: *Work Sans* (pesos 600 e 700).
  * Textos Corridos e Legendas: *Elms Sans* / *Inter* (pesos 400 e 500).
  * Números e Identificadores Técnicos: *IBM Plex Mono*.
- **Estrutura Bento Grid Polida:**
  * Header com avatares circulares bem alinhados (criadora + marca), badge de status "Janela 90 dias".
  * Top Cards de Métricas com micro-tipografia limpa, indicadores numéricos nítidos e badges contextuais.
  * Card de Parecer Editorial destacado com borda sutil e hierarquia tipográfica impecável.
  * Botões de exportação (PDF e CSV) no rodapé com estilo minimalista.

### 2.2 Motor de Demografia Local (`src/features/analise/demographics.py`):
- **Gênero por Nomes (IBGE):**
  * Carregar `data/names_seed.json` (1.984 nomes normalizados em maiúsculas sem acentos).
  * Função `estimate_gender_distribution(names_list)`: extrai o primeiro nome de cada usuário, faz o matching na base e calcula a porcentagem de gênero feminino, masculino e indeterminado.
  * Retornar contrato JSON com cobertura: `{"female_pct": 82.5, "male_pct": 12.0, "unknown_pct": 5.5, "coverage_pct": 94.5}`.
- **Regionalização por DDD (`data/ddd_uf.json`):**
  * Função `estimate_location_by_ddd(text_samples_list)`: busca menções de padrões de DDD `(XX)` ou `XX` em bios e comentários, cruza com a tabela de estados e ranqueia o Top 3 Estados/Regiões mais frequentes.
- **Isolamento de Responsabilidade:** O arquivo `demographics.py` é puramente algorítmico, sem dependências de rede ou banco.

### 2.3 Integração na View (`src/app.py`):
- Conectar a chamada de `demographics.py` ao estado do Streamlit para alimentar o card de Demografia no Bento Grid.

---

## 3. Restrições Negativas (DUMMY.md)
- **PROIBIDO** acoplar queries SQL ou requests HTTP em `src/app.py`.
- **PROIBIDO** gerar zeros silenciosos: se a amostra não tiver nomes reconhecidos, exibir explicitamente status "Indisponível / Cobertura Insuficiente".
- **PROIBIDO** usar frameworks CSS externos pesados (usar CSS nativo sanitizado via `st.markdown`).

---

## 4. Critérios de Aceite & Validação
1. **Fidelidade Visual:** A interface em `streamlit run src/app.py` deve estar idêntica na composição e estilo ao Paper Desktop.
2. **Performance Demográfica:** Processamento de 500 nomes em menos de 50ms via matching local no JSON.
3. **Testes Unitários:** `pytest tests/test_demographics.py` com 100% de sucesso validando nomes comuns femininos/masculinos e casos limítrofes.
