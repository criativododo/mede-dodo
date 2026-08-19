# 🛡️ DUMMY.md — Safety Shield & Regras Inquebráveis

> [!CAUTION]
> **REGRA DE NÃO-CONTRADIÇÃO SOBERANA:** Se este arquivo divergir do código-fonte ou dos testes físicos ativos, o código e os testes prevalecem sempre. Encontrar divergência significa apenas que este documento necessita de atualização síncrona. Nunca use uma regra deste arquivo para justificar uma implementação que a SPEC atual proíbe.

---

## 📝 1. Visão Geral e Sincronização

* **O que o projeto faz:** O **métricaDODÔ** é uma aplicação de inteligência de influência e auditoria de criadores para marcas de moda feminina, operando com arquitetura econômica de IA (heurística local + Gemini 2.5 Flash) e métricas autorais sob o Design System Dodô.
* **Sincronização de Inteligência:** Este arquivo é um documento `.md` de governança. Sempre que for alterado após uma sprint ou comando `/fim`, execute `/drive` no terminal para sincronizar o contexto protetor com o Google Drive do Gemini Spark.

---

## 💻 2. Stack Real de Engenharia

* **Linguagem/Runtime:** Python 3.12+ (Ambiente local macOS)
* **Interface (View):** Streamlit (atuando estritamente como View Pura/Burra)
* **Scraper/Coleta:** Instaloader (sessão local autenticada em `~/.config/instaloader/session-elafashiomkt`)
* **Motores de IA:** Heurística local + Google GenAI SDK (`google.genai` / Gemini 2.5 Flash); Claude/Anthropic não faz parte da v2.0.0
* **Persistência & Cache:** SQLite local em `data/cache.db` (TTL 24h)
* **Exportação:** `fpdf2` (PDF editorial autocontido) e CSV tabular limpo

---

## 📁 3. Mapa de Pastas e Permissões Ativas

* `/src/app.py`: View Pura de interface Streamlit. *(Permitido editar apenas UI/estados reativos)*
* `/src/features/coleta/`: Scraper, parsing e sessão Instaloader. *(Permitido editar)*
* `/src/features/analise/`: Motores de IA, heurísticas IBGE/DDD e métricas autorais. *(Permitido editar)*
* `/src/features/relatorios/`: Geradores de PDF (fpdf2) e CSV. *(Permitido editar)*
* `/specs/`: Especificações técnicas ativas. *(PROIBIDO alterar via código sem aprovação explícita)*
* `/legado/`: Histórico inativo das Sprints 001-004. *(PROIBIDO varrer automaticamente; leitura apenas sob consulta explícita do Dani)*

---

## ⚡ 4. Fluxo Principal de Dados

`src/app.py` (Input do usuário) ➔ `features/coleta/` (Instaloader + Cache SQLite) ➔ `features/analise/` (Heurística local + triagem/parecer Gemini Flash + Demografia) ➔ `features/relatorios/` (PDF / CSV) ➔ `src/app.py` (Renderização na tela).

---

## 🚫 5. Restrições Negativas ("O que NÃO fazer sob pena de quebra")

* **Credenciais & Chaves:** NUNCA escreva chaves de API (`GEMINI_API_KEY`) ou senhas hardcoded no código. Não criar chave Anthropic na v2.0.0. Use estritamente o `.env`/segredos.
* **View Impura:** É TERMINANTEMENTE PROIBIDO conter chamadas HTTP diretas, comandos SQL ou manipulação direta de arquivos de disco dentro de `src/app.py`. A View apenas exibe estado e renderiza componentes.
* **Métricas Padrão de Mercado:** NUNCA aplique fórmulas genéricas de engajamento do mercado. Todas as contas, pesos e índices devem ser co-criados e expressamente autorizados pelo Dani.
* **Proteção Anti-Ban (Instaloader):** NUNCA altere o pacing, sleeps ou lógica de rate-limit da sessão do Instaloader.
* **Proatividade Excessiva (YAGNI):** Não crie recursos multi-tenant, autenticações complexas na nuvem ou abstrações não solicitadas na issue ativa.
* **Acesso ao Legado:** NUNCA carregue ou varra a pasta `/legado/` automaticamente. Ela só é acessada quando o Dani solicitar explicitamente um resgate histórico.

---

## ⚠️ 6. Matriz de Riscos do Repositório

* **Risco 1 (Instaloader Rate Limit):** Se muitas consultas forem disparadas sem cache, o Instagram pode invalidar a sessão. *Mitigação:* Cache SQLite com TTL de 24h obrigatório antes de qualquer requisição externa.
* **Risco 2 (Gemini API Rate Limit):** Esgotamento de cota ou indisponibilidade do Gemini Flash. *Mitigação:* Pré-triagem local, fallback heurístico explícito e estado `indisponivel` quando faltarem dados; não há fallback para outro provedor.
* **Risco 3 (Quebra de Layout Streamlit):** Injeção de CSS não sanitizado pode desalinhar o Design System Dodô. *Mitigação:* Manter tokens CSS centralizados e constantes na paleta Cannoli (`#F5F4EC`) e Vermelho Haute (`#810100`).

---

## 🔬 7. Dados e Validação

* **Bases Locais:** `data/names_seed.json` (1.984 nomes IBGE) e `data/ddd_uf.json` (Mapeamento DDD).
* **Validação Obrigatória:** Toda alteração de lógica deve ser comprovada com logs factuais ou testes em `tests/` antes de ser considerada concluída.

---

## 🛑 8. Desconhecidos e Bloqueios (Hipóteses da v2.0.0)

* [ ] **UNKNOWN-01:** Calibração final das fórmulas autorais de Engajamento Real e Índice de Pods/Autenticidade com o Dani.
* [ ] **UNKNOWN-02:** Janelas temporais de sazonalidade específicas para nichos de moda íntima e fitness.

---

## 🔄 9. Sincronização seletiva com o Google Drive

A rotina `/drive` é **unidirecional, local → Drive e seletiva**. Sua única finalidade é alimentar o contexto normativo do Gemini Spark com documentos de governança, especificação, decisão, issues e benchmark.

* **Drive URL:** https://drive.google.com/drive/folders/1ytT3dHcVfqnSeggYqPB-VINlndJHInV4?usp=drive_link
* **Espelho local:** `/Users/danielperrut/Library/CloudStorage/GoogleDrive-criativododo@gmail.com/Meu Drive/0. SISTEMA D/sub-projects/mede-dodo`
* **Whitelist:** `README.md`, `DUMMY.md`, `PROGRESS.md`, `FINDER-001.md`, todos os arquivos de `specs/`, `decisions/`, `docs/issues/` e `BENCHMARK-METRICS-*.md`.
* **Blacklist:** `/legado/`, `/data/`, `.env`, sessões do Instaloader, `.git/`, `__pycache__/`, `.pytest_cache/`, `venv/`, `.DS_Store` e quaisquer credenciais, caches ou dados brutos locais.

Nunca sincronizar arquivos da blacklist, mesmo que estejam dentro de uma pasta ativa. O próprio `CLAUDE.md` permanece local e fora da whitelist.
