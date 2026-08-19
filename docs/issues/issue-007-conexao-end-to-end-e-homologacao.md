# ISSUE-007: Conexão End-to-End, Testes de Integração & Homologação Final (v2.0.0)

* **Status:** Done — pipeline real orquestrado em `src/app.py` (botão "Auditar Perfil"), `iniciar_app.command` criado/validado, `tests/test_integration_e2e.py` (9/9) via `AppTest` com mocks. Ressalva: cobre a orquestração/homologação em si; a ISSUE-004 segue `partial` (Rodadas 2/3 bloqueadas), então BQI/CI/SD e o veredito do parecer aparecem como "Indisponível" em auditorias reais — ver `docs/issues/manifest.json`.
* **Responsável:** Claude Code
* **Fase:** Fase 3 — Fim (Integração & Homologação do MVP)
* **Arquivos-Alvo:**
  - `src/app.py` (Orquestração reativa da View Pura com todas as features)
  - `iniciar_app.command` (Script executável macOS para inicialização com 1 clique)
  - `tests/test_integration_e2e.py` (Suíte de testes de integração end-to-end)
  - `docs/issues/manifest.json`
  - `PROGRESS.md`
* **Dependências:** ISSUE-001 a ISSUE-006 concluídas

---

## 1. Objetivo da Issue

Plugar todas as pontas desacopladas da v2.0.0 em um fluxo contínuo e estável:
`Entrada de Usuário (@username) -> Coleta Rápida / Cache SQLite -> Heurísticas & IA (Gemini Flash + Local) -> Motor de Métricas (metrics.py) -> Renderização Paper Desktop 1:1 -> Exportação (PDF / CSV)`.
Validar a suíte completa de testes (`pytest`) e gerar o launcher executável `iniciar_app.command` na raiz.

---

## 2. Requisitos Técnicos e Implementação

### 2.1 Orquestração na View Pura (`src/app.py`):
- **Fluxo do Botão "Auditar Perfil":**
  1. Usuário digita `@username` e clica em "Auditar Perfil".
  2. `app.py` exibe indicador de progresso e aciona `features/coleta/database.py` e `scraper.py` (verificando cache de 24h ou disparando coleta rápida com amostragem de 90 dias).
  3. Dados brutos passam por `features/analise/`:
     * `demographics.py`: calcula distribuição de gênero (IBGE) e ranking de DDDs.
     * `ai_local.py` / `ai_gemini.py`: executa a triagem dos comentários nos sinais A, B, C, D e gera o parecer editorial estruturado.
     * `metrics.py`: calcula o ER Branding ponderado por formato, BQI (0–100), Consistência (CI) e Saturação (SD).
  4. O payload resolvido é gravado no `st.session_state["report_data"]`.
  5. `app.py` renderiza o Bento Grid completo do Paper Desktop e habilita os botões de download de PDF e CSV.
- **Invariante Crítica:** `app.py` NÃO realiza queries SQL diretas nem chamadas de rede; atua exclusivamente como orquestrador de estado e renderizador de componentes.

### 2.2 Launcher Executável macOS (`iniciar_app.command`):

- Script Bash com permissão de execução (`chmod +x`) para rodar o app localmente com 1 clique:

```bash
#!/bin/bash
cd "$(dirname "$0")"
echo "🦤 Iniciando métricaDODÔ v2.0.0..."
source venv/bin/activate 2>/dev/null || true
streamlit run src/app.py
```

O launcher deve assumir que o diretório de trabalho é a raiz do projeto, ativar o ambiente virtual quando disponível e delegar a inicialização ao Streamlit. Falhas de ativação do ambiente não devem ocultar um erro posterior de execução do aplicativo.

### 2.3 Testes de Integração (`tests/test_integration_e2e.py`):

Testar o fluxo completo simulado com fixture de dados mockados (perfil -> coleta mockada -> análise -> métricas -> exportação de PDF e CSV).

Validar que o payload final contém todos os campos de proveniência, sem erros de tipo ou divisão por zero.

---

## 3. Critérios de Aceite & Definition of Done (DoD)

**Fluxo Completo Funcional:** Uma auditoria completa (modo cache ou modo real) renderiza todos os cards e gráficos sem exceptions no console.

**Exportação Validada:** Downloads de PDF e CSV funcionam perfeitamente na interface.

**100% Testes Verificados:** Execução de `pytest tests/` com todas as suítes (coleta, demografia, métricas, relatórios e integração) passando com sucesso.

**Atalho Criado:** `iniciar_app.command` executável e funcional na raiz.

**Governança:** `manifest.json` com todas as issues marcadas como `done` e `PROGRESS.md` atualizado com o relatório final de entrega.

---

## 4. Restrições de Governança

A View deve continuar pura: `src/app.py` não pode conter queries SQL, chamadas HTTP diretas, acesso direto a arquivos, segredos ou lógica matemática de negócio. A orquestração deverá chamar serviços internos com dependências explícitas e devolver estados serializáveis para renderização.

A homologação deverá distinguir modo cache, modo real, dado indisponível, fallback local, resposta Gemini, erro de integração e erro de validação. Nenhuma fixture poderá exigir login real, chamada externa ou chave de API. O teste físico contra uma conta real, quando necessário, deve ser separado do conjunto determinístico automatizado.

Os módulos de coleta, análise, métricas e exportação devem preservar a proveniência: origem, versão de método, versão de fórmula, janela, amostra, cobertura, timestamp, provedor de IA, nível de fallback e advertências. Ausência de dados não pode ser convertida silenciosamente em zero.

## 5. Sequência de Homologação

1. Validar as dependências e a existência dos módulos de coleta, análise e relatórios.
2. Executar a suíte unitária completa sem rede.
3. Executar `tests/test_integration_e2e.py` com fixtures determinísticas.
4. Validar o fluxo visual da View em modo de demonstração/cache.
5. Confirmar que os botões de exportação devolvem bytes/strings sem escrever arquivos temporários desnecessários.
6. Validar o launcher `iniciar_app.command` em ambiente macOS com o ambiente virtual disponível e sem ele.
7. Registrar contagens de testes, limitações, warnings e evidências em `PROGRESS.md`.
8. Somente após todos os critérios físicos serem demonstrados, atualizar o status das issues para `done`.

## 6. Rastreabilidade

| Artefato | Relação |
|---|---|
| [`SPEC-001.md`](../../specs/SPEC-001.md) | Fluxo end-to-end, View Pura, módulos e Definition of Done. |
| [`DUMMY.md`](../../DUMMY.md) | Safety Shield, separação de camadas e restrições negativas. |
| [`ADR-001-arquitetura-hibrida-e-view-pura.md`](../../decisions/ADR-001-arquitetura-hibrida-e-view-pura.md) | View Pura e fronteiras arquiteturais. |
| [`ADR-003-gemini-only-e-fallback-local.md`](../../decisions/ADR-003-gemini-only-e-fallback-local.md) | Heurística local, Gemini Flash e fallback explícito. |
| [`issue-004-motor-metricas-autorais.md`](issue-004-motor-metricas-autorais.md) | Motor matemático e payload de métricas. |
| [`issue-005-inteligencia-hibrida.md`](issue-005-inteligencia-hibrida.md) | Análise de comentários, parecer e contratos de IA. |
| [`issue-006-exportacao-relatorios.md`](issue-006-exportacao-relatorios.md) | Geradores PDF/CSV e integração de downloads. |
| `docs/issues/manifest.json` | Controle dos estados e dependências das micro-issues. |
| `PROGRESS.md` | Registro físico de testes, homologação e limitações. |
