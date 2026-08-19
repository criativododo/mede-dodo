# 🦤 métricaDODÔ (MedeDodo) — v2.0.0

> [!IMPORTANT]
> **DIRETRIZ DE ONBOARDING PARA AGENTES DE IA (Claude Code / Gemini Spark / Manus):**
> Antes de realizar qualquer varredura de código-fonte, inspeção de arquivos ou refatoração neste repositório, você deve obrigatoriamente ler o arquivo **`DUMMY.md`** na raiz. Ele contém o mapa físico real do projeto, as travas de segurança e as restrições negativas ("O que NÃO fazer") que regem este software.

---

## 📍 Status e Fase Ativa

* **Fase Atual:** Fase 1 — Início (Fundação & Estabilização da v2.0.0)
* **Estado:** Inicialização estrutural, purge histórico concluído e governança ativa.
* **Regra de Bloqueio:** É terminantemente proibido avançar para o desenvolvimento de novas features ou gerar código de produção sem que a SPEC e as fórmulas autorais de métricas estejam explicitamente aprovadas pelo Dani e fatiadas no `docs/issues/manifest.json`.

---

## 🛠️ Comandos de Governança e Sincronização

Este repositório é governado por comandos globais executados no terminal do assistente:

* **`/inicio`**: Ativa a Fase 1 (Fundação). Lê o documento `01-INICIO.md` para iniciar o diagnóstico de briefings, captura de pensamentos, cruzamento de documentação interna e estruturação da nova SPEC técnica antes de qualquer código.
* **`/fim`**: Ativa a Fase 3 (Encerramento). Lê o documento `03-FIM.md` para consolidar o pacote de entrega factual da sprint em 11 itens rígidos, baseados estritamente em evidências físicas e logs de testes.
* **`/drive`**: Comando explícito de sincronização. Realiza o upload e a sobrescrita unidirecional de **todos os arquivos `.md` ativos locais** para a pasta correspondente no Google Drive. Este comando deve ser acionado manualmente para atualizar a base de conhecimento do Gemini Spark.

---

## 📁 Estrutura de Pastas (Feature-Based Folders)

Para economizar tokens de contexto, a estrutura isola responsabilidades físicas por funcionalidade:

```text
/
├── specs/             # Especificações técnicas ativas (Verdade Normativa)
├── decisions/         # Registros de Decisão Arquitetural (ADRs)
├── legado/            # Histórico das Sprints 001-004 (IGNORADO por padrão; consulta APENAS sob pedido explícito do Dani)
├── docs/
│   ├── finders/       # Benchmarks, receitas de código e APIs de reuso (ex: FINDER-001.md)
│   └── issues/        # Slices atômicos (issue-XXXX.md) e o manifest.json
├── data/              # Bases locais ativas (names_seed.json, ddd_uf.json, cache.db)
├── src/               # Código-fonte ativo da v2.0.0
│   ├── app.py         # View Pura do Streamlit (apenas renderização de UI, sem I/O ou banco)
│   └── features/      # Módulos isolados: coleta/, analise/ e relatorios/
├── DUMMY.md           # Safety Shield e regras inquebráveis de engenharia
├── PROGRESS.md        # Termômetro Físico de entrega e evidências auditáveis
└── README.md          # Roteador de Contexto e Onboarding da IA

```

---

## 🔄 Sincronização `/drive` com o Gemini Spark

A sincronização é **unidirecional e seletiva**: o checkout local envia somente documentos normativos, especificações, decisões, issues e benchmarks para o espelho do Google Drive. O comando não baixa alterações do Drive.

```text
drive_url: https://drive.google.com/drive/folders/1ytT3dHcVfqnSeggYqPB-VINlndJHInV4?usp=drive_link
local_path: /Users/danielperrut/Library/CloudStorage/GoogleDrive-criativododo@gmail.com/Meu Drive/0. SISTEMA D/sub-projects/mede-dodo
mode: local_to_drive / selective_whitelist
```

A whitelist inclui `README.md`, `DUMMY.md`, `PROGRESS.md`, `FINDER-001.md`, `specs/`, `decisions/`, `docs/issues/` e `BENCHMARK-METRICS-*.md`. A blacklist inclui `/legado/`, `/data/`, `.env`, sessões do Instaloader e diretórios de sistema.
