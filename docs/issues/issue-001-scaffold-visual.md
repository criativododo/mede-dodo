# ISSUE-001: Scaffold Visual no Streamlit (View Pura e Paper Desktop 1:1)

* **Status:** In Progress
* **Responsável:** Claude Code
* **Fase:** Fase 2 — Meio (Execução de Micro-Issue)
* **Arquivos-Alvo:** `src/app.py`
* **Referência Visual:** Paper Desktop (https://app.paper.design/file/01M031HEGV5DY019PTPDDVX182/1-0)

---

## 1. Objetivo da Issue
Construir a casca visual completa e estática da interface do métricaDODÔ no Streamlit (`src/app.py`), espelhando rigorosamente em 1:1 a paleta, tipografia, Bento Grid e componentes do Paper Desktop, operando como **View Pura / Burra** com dados mockados em `st.session_state`.

---

## 2. Requisitos de UI & Tokens do Design System Dodô
- **Fundo:** Cannoli (`#F5F4EC`).
- **Destaque Primário / Botões:** Vermelho Haute (`#810100`) com texto branco (`#FFFFFF`).
- **Cards & Superfícies:** Fundo claro com borda sutil `1px solid #E5E0D8` e raio de canto `12px`.
- **Tipografia:** Work Sans (Títulos), Elms Sans (Corpo) e IBM Plex Mono (IDs e números técnicos).

---

## 3. Componentes Obrigatórios a Renderizar (com Mock Inicial)
1. **Header de Identidade:**
   - Input de texto para o `@username` do Instagram.
   - Selectbox / Input para seleção da marca contratante (ex: "Jescri Lingerie").
   - Avatares circulares: foto de perfil da criadora e logo da marca.
   - Badge de status: "Janela Trimestral (90 dias) | Modo Mock / Visual".
2. **Cards de Métricas Principais (Bento Grid Topo):**
   - Card 1: `ER Branding` (ex: 4.8% — contextualizado por porte).
   - Card 2: `BQI (Brand Quality Index)` (ex: 82/100 — badge "Excelente").
   - Card 3: `Consistência (CI)` (ex: 78% — badge "Consistente").
   - Card 4: `Saturação de Publis (SD)` (ex: 18% — badge "Saudável").
3. **Bloco Central de Gráficos e Distribuições:**
   - Gráfico/Barras de Distribuição de Formatos (Reels, Carrossel, Foto).
   - Distribuição de Tipologia A/B/C/D de comentários com barra de progresso do `V_AB` (ex: 52%).
   - Card de Demografia Estimada (Gênero % e Top 3 Estados por DDD).
4. **Card de Parecer Editorial da IA:**
   - Card em destaque com borda refinada, badge "Recomendada com Alta Afinidade", resumo de pontos fortes e notas para o briefing.
5. **Barra de Ações (Rodapé):**
   - Botão "Exportar Relatório PDF" e Botão "Download CSV" (estáticos/mockados).

---

## 4. Restrições Negativas & Invariantes (DUMMY.md)
- **PROIBIDO** importar `sqlite3`, `requests`, `urllib3` ou conectar com banco/rede no `src/app.py`.
- Todos os dados exibidos devem vir de um dicionário mockado estruturado em `st.session_state`.
- **PROIBIDO** usar componentes que quebrem o layout ou injetem CSS de terceiros fora dos tokens definidos.

---

## 5. Critérios de Aceite & Validação
- O comando `streamlit run src/app.py` deve iniciar sem erros de sintaxe.
- A interface deve exibir todos os 5 blocos visuais conforme o Paper Desktop.
- O código de `src/app.py` deve conter zero I/O de disco ou banco de dados.
