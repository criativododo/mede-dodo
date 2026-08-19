# ISSUE-002: Módulo de Coleta Rápida, Cache SQLite & Preparação para Cloud (v2.0.0)

* **Status:** Done
* **Responsável:** Claude Code
* **Fase:** Fase 2 — Meio (Execução de Micro-Issue)
* **Arquivos-Alvo:** 
  - `src/features/coleta/scraper.py`
  - `src/features/coleta/database.py`
  - `src/features/coleta/auth.py`
  - `.streamlit/secrets.toml.example`
  - `src/app.py` (Apenas acoplamento do Password Gatekeeper visual e meta robots)
  - `tests/test_coleta.py`
* **Dependências:** ISSUE-001 concluída

---

## 1. Objetivo da Issue
Implementar o motor de coleta do Instaloader otimizado para alta velocidade (amostragem estatística na janela de 90 dias com tempo de coleta entre 40–60 segundos), o cache local SQLite com TTL de 24 horas, o suporte híbrido de segredos (`st.secrets` com fallback para `.env`) e a trava de segurança por senha (Password Gatekeeper) na View.

---

## 2. Requisitos Técnicos e Implementação

### 2.1 Coletor Instaloader Otimizado (`src/features/coleta/scraper.py`):
- **Janela Trimestral:** Filtrar publicações dos últimos 90 dias (`datetime.now() - timedelta(days=90)`).
- **Amostragem Rápida (Anti-Timeout):**
  * Limitar a coleta aos **12 a 15 posts mais recentes/relevantes** da janela trimestral.
  * Extrair de **30 a 50 comentários por post** (amostra representativa para triagem estatística).
  * Salvar metadados completos do post: `post_id`, `format` (Reel, Carrossel, Foto), `published_at`, `likes`, `comments_count`, `caption`, `is_sponsored` (#publi/parceria).
- **Proteção Anti-Ban & Sessão:**
  * Carregar sessão persistida em `~/.config/instaloader/session-elafashiomkt` se disponível localmente.
  * Aplicar `time.sleep` conservador e aleatorizado (0.5s a 1.5s) entre requisições de comentários.
  * Em caso de `429 Too Many Requests` ou `LoginRequired`, pausar com segurança e retornar erro estruturado ou dados do cache, sem quebrar a execução.

### 2.2 Cache Local SQLite (`src/features/coleta/database.py`):
- **Banco:** `data/cache.db`.
- **Tabela `profile_cache`:** `username`, `profile_data_json`, `posts_data_json`, `comments_data_json`, `created_at_utc`, `ttl_seconds` (padrão: 86400 / 24h).
- **Lógica de Consulta:**
  1. Verificar se existe registro para `@username` com idade `< 24h`.
  2. Se válido: retornar imediatamente os dados cacheados (resposta em < 1 segundo).
  3. Se expirado ou inexistente: acionar o `scraper.py`, salvar o resultado e atualizar o cache.

### 2.3 Gestão de Segredos & Configurações (`src/features/coleta/auth.py`):
- Função helper `get_secret(key_name, default=None)`:
  1. Tenta ler de `st.secrets[key_name]`.
  2. Se não encontrar, tenta ler de `os.environ.get(key_name)` ou `.env`.
- Criar `.streamlit/secrets.toml.example` documentando:
  ```toml
  APP_PASSWORD = "sua_senha_aqui"
  GEMINI_API_KEY = "sua_chave_gemini"

  ```

### 2.4 Gatekeeper de Acesso Leve na View (`src/app.py`):

* Se `APP_PASSWORD` estiver configurado nos segredos, exibir tela inicial de login/senha bloqueando os módulos.
* Preservar o Design System Dodô: Fundo Cannoli (`#F5F4EC`), card central com borda `1px solid #E5E0D8`, raio `12px` e botão Vermelho Haute (`#810100`).
* Ao autenticar com sucesso, persistir `st.session_state["authenticated"] = True`.
* Inserir via `st.markdown` no `<head>` a metatag anti-indexação:
`<meta name="robots" content="noindex, nofollow">`.

---

## 3. Restrições Negativas & Invariantes (DUMMY.md)

* **PROIBIDO** acoplar queries SQL diretas dentro de `src/app.py` (a View chama apenas as funções expostas do módulo `features/coleta/`).
* **PROIBIDO** armazenar senhas ou chaves em texto plano versionáveis no Git.
* **PROIBIDO** tentar burlar rate limit com scrapers não autorizados.

---

## 4. Critérios de Aceite & Validação

1. **Performance:** Coleta completa de um perfil em modo real executando em menos de 60 segundos.
2. **Cache:** Segunda consulta do mesmo perfil executando instantaneamente (< 1s) via SQLite.
3. **Autenticação:** App bloqueado sem a senha e liberado imediatamente após inserção correta.
4. **Testes Unitários:** `pytest tests/test_coleta.py` validando leitura/escrita do cache SQLite e mock do scraper com 100% de sucesso.
