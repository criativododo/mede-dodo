# FINDER-003: Geração de Relatórios Instagram — Workflow, Sessão e Coleta Responsável

> **Projeto:** métricaDODÔ / Projeto Médio Dodô. **Uso:** referência compacta para Claude Code. **Escopo:** módulo de geração de relatórios, UI Streamlit, manutenção de sessão autorizada, pacing compatível, cache, resiliência, observabilidade e exportação.
>
> **Regra de segurança:** este documento não ensina a contornar anti-bot, falsificar fingerprint/TLS, rotacionar proxies para escapar de limites, distribuir carga entre contas ou simular navegação para ocultar automação. Recomendações legadas com esse objetivo são preservadas apenas como referências históricas e explicitamente marcadas como **não normativas**. A implementação deve preferir APIs oficiais, dados públicos permitidos, sessão pertencente ao usuário, rate limits documentados, cache e pausa quando a plataforma sinalizar bloqueio.

## 1. Objetivo e requisitos não funcionais

O módulo transforma `@usuario` em auditoria exportável de perfil Instagram. O fluxo deve preservar a responsividade do Streamlit, manter a identidade da sessão autorizada, limitar tráfego, tolerar falhas parciais e expor a proveniência de cada métrica.

| ID | Requisito |
|---|---|
| RF-01 | Receber `@handle` ou URL; validar username com `[A-Za-z0-9._]{1,30}` e normalizar `@`. |
| RF-02 | Executar I/O em `threading.Thread(daemon=True)`; a UI nunca chama `join()` nem `st.*` na thread de fundo. |
| RF-03 | Consultar `data/cache.db` antes de qualquer chamada externa; registrar `source`, `collected_at`, `freshness`, `status` e `warnings`. |
| RF-04 | Respeitar limites documentados da API/cliente; interromper quando houver 429, challenge, checkpoint, CAPTCHA ou sinal de abuso. |
| RF-05 | Janela padrão configurável; teto de segurança inicial: 60 posts e 90 dias por auditoria. O teto é proteção de carga, não bloqueio de contas grandes. |
| RF-06 | Coletar comentários de forma limitada e incremental; priorizar primeira página, máximo inicial de 50 por post, com amostra explicitada. |
| RF-07 | Filtrar localmente comentários rasos/spam antes de Gemini; IA opcional, JSON estrito, cache por hash e máximo de 2 lotes por perfil. |
| RF-08 | Exportar HTML/PDF/JSON somente quando o estado de dados requerido estiver `concluido` ou `partial` explicitamente confirmado; nunca ocultar warnings. |
| RNF-01 | Custo zero: sem API paga, proxy pago, pool de contas ou dependência obrigatória de GPU. |
| RNF-02 | Segurança e privacidade: somente contas/dados públicos permitidos ou contas profissionais autenticadas pelo próprio usuário. |
| RNF-03 | Recuperação: retry limitado, backoff, cache fallback, checkpoint de progresso e re-login explícito quando necessário. |

## 2. Arquitetura assíncrona e workflow Streamlit

```text
[Input @handle/URL] -> [Gerar Relatório]
          |
          v
[State: idle -> validating -> running -> retrying/partial -> completed/failed]
          |
          +--> [cache.db] --hit--> [metrics/report]
          |
          +--> [authorized session/API] -> [bounded collection] -> [local filters]
                                                    |
                                                    +--> [Gemini JSON, optional]
                                                    v
                                          [HTML/PDF/JSON + provenance]
```

### 2.1 Entrada e estado inicial

A tela em repouso contém input com placeholder `@usuario`/`influenciadora`, validação de caracteres, seletor de janela (30/60/90 dias), modo demonstração e botão primário **Gerar Relatório**. O botão fica desabilitado até o input ser válido. A sidebar mostra `Sessão ativa: <usuario>` ou um aviso de sessão ausente/expirada antes de iniciar a rede.

### 2.2 Disparo em background e polling

```python
# pseudocódigo normativo
if analyze_clicked and valid_handle(handle):
    state = {
        "status": "validating", "phase": "session", "progress": 0.0,
        "eta_seconds": None, "warnings": [], "analysis": None
    }
    thread = Thread(target=_run_pipeline,
                    args=(handle, window_days, demo_mode, state),
                    daemon=True)
    thread.start()
    st.rerun()

if state["status"] in {"validating", "running", "retrying"}:
    render_status_bottom(state)
    time.sleep(0.3)
    st.rerun()
```

A thread de fundo manipula apenas um dicionário simples de estado; não invoca `st.*`. O polling atualiza mensagem, progresso, ETA, fase, retry e warnings. No modo demonstração, não há rede nem jitter: os dados são determinísticos e o fluxo deve terminar rapidamente.

### 2.3 Fases visíveis, mensagens e ETA

| Faixa | Fase | Mensagem compacta |
|---:|---|---|
| 0–10% | Resolução | `Resolvendo perfil e validando sessão...` |
| 10–30% | Grid | `Analisando histórico na janela selecionada...` |
| 30–85% | Extração | `Coletando comentários com limite seguro — post X/Y...` |
| 85–95% | Processamento | `Agregando métricas, publis, demografia e IA opcional...` |
| 95–100% | Compilação | `Estruturando HTML/PDF/JSON...` |

Com `P_remaining` posts elegíveis:

```text
T_remaining = P_remaining * (D_net_mean + D_proc_mean)
D_net_mean  = média observada do controlador, não constante fixa
D_proc_mean = média móvel do processamento local
ETA         = clamp(T_remaining, 0, max_runtime_budget)
```

A especificação histórica estimava `D_net_mean=3,5s`, `D_proc_mean=0,2s` e jitter de 2–5s; esses valores são **prior inicial**, não garantia. A UI deve substituir o prior pela média móvel depois dos primeiros itens e mostrar intervalo quando a variância for alta.

### 2.4 Conclusão e reset

Ao atingir 100%, o painel inferior vira card de conclusão; aparece o botão secundário **Ver Relatório**, que abre dashboard/modal e libera HTML/PDF/JSON. **Gerar novo relatório** limpa apenas o estado da tela, não o cache global sem confirmação. Em `partial`, o relatório pode ser visto somente se a UI indicar componentes ausentes e origem stale/partial; o modo estrito pode exigir `completed`.

## 3. Sessão autorizada, cookies e login

### 3.1 Hierarquia de sessão

1. Preferir API oficial Meta para contas profissionais e tokens OAuth autorizados.
2. Para coleta local compatível já existente, autodetectar `session-*` em `~/.config/instaloader/` ou usar `INSTAGRAM_SESSION_FILE` explícito.
3. Validar com `test_login()`/equivalente antes da coleta; não chamar endpoints de dados com sessão desconhecida.
4. Derivar e exibir o proprietário da sessão; recusar mismatch entre usuário solicitado e sessão ativa.
5. Armazenar cookies/token em Keychain macOS, secret store ou arquivo com permissões restritas; nunca em Git, frontend, log ou prompt.
6. Ao expirar, pausar, salvar estado parcial e solicitar re-login humano. Não trocar automaticamente para pool de contas.

Cookies historicamente mencionados no arquivo (`sessionid`, `csrftoken`, `mid`, `ig_did`) devem ser tratados como credenciais sensíveis; não é contrato de que todos sejam necessários. A documentação do Instaloader recomenda preservar o session file, pois relogins repetidos favorecem falhas e 429; o cliente também possui `RateController`, `max_connection_attempts`, `request_timeout` e tratamento específico de checkpoint/challenge [1] [2].

### 3.2 Validação e renovação segura

```text
load_session_file()
  -> test_login()
  -> owner == requested_handle? else fail SESSION_IDENTITY_MISMATCH
  -> session_age/health check
  -> if valid: proceed
  -> if expired/401/403: save partial, pause, ask user login
```

“Renovação silenciosa” significa apenas renovar token OAuth dentro do fluxo oficial e com consentimento já concedido; não significa renovar cookies por scraping, importar credenciais sem autorização ou ocultar um challenge. Após login manual, o usuário deve gerar/salvar nova sessão pelo fluxo suportado; o agente não deve pedir senha no chat nem registrar o valor.

### 3.3 API oficial e permissões

A Instagram Platform atende contas profissionais Business/Creator. Standard Access serve desenvolvimento/contas com papel; Advanced Access, App Review e Business Verification são necessários quando o app atende contas profissionais de terceiros [3]. Tokens usam OAuth; códigos de autorização são de curta duração, tokens de curta duração devem ser trocados por long-lived tokens e estes podem ser renovados antes de expirar [3].

Insights de mídia podem incluir `comments`, `likes`, `views`, `reach`, `saved`, `shares`, `total_interactions`, `link_clicks`, `navigation`, `profile_activity` e métricas de Reels/Stories, conforme tipo de mídia e permissão. A API pode retornar conjunto vazio quando dado não existe, ter atraso de até 48h e manter Insights de Stories por janela limitada; ausência nunca deve virar zero silencioso [4].

## 4. Pacing, rate limiting e proteção operacional

### 4.1 Princípio

O pacing existe para respeitar capacidade e termos do serviço, não para ocultar automação. O controlador deve ser conservador, observável e monotônico: diante de sinal de bloqueio, reduz chamadas e pausa; nunca aumenta volume, muda identidade, gira IP ou tenta “furar” a barreira.

O Instaloader já mantém contabilidade própria e recomenda não executar navegador/app/segunda instância em paralelo; reinicializações frequentes favorecem 429. Se 429 ocorrer, aguardar o controlador, preservar estado e não insistir em loop [1]. A Graph API/Instagram Platform possui limites por app/usuário/use case, pode expor headers de uso e recomenda espalhar queries, reduzir escopo e parar quando o limite é alcançado [5] [3].

### 4.2 Controlador de atraso

O prior do projeto é delay aleatório de **2–5s** entre operações de rede. Deve ser calibrado pelo cliente oficial/Instaloader e pelos sinais de uso; não é promessa universal da plataforma. O modo demo desativa espera de rede.

| Operação | Prior inicial | Regra segura |
|---|---:|---|
| Resolução inicial | 4–7s | Uma chamada; usar cache se possível |
| Seções/post metadata | 2–5s | Serializar; não paralelizar por sessão |
| Lote de até 10 posts | 3–6s | Batch/cache; reduzir se quota aproximar limite |
| Pausa de proteção | 30–60s | Aplicar por budget, não por tentativa de evasão |
| 429/challenge/checkpoint | fora da tabela | Parar, backoff e pedir ação; não rotacionar identidade |

```python
# pseudocódigo: controlador de conformidade
wait = controller.next_wait(query_type)
sleep(wait)
response = request_once()
if response.status in {429, 403} or response.challenge:
    controller.pause_until_safe_signal()
    checkpoint.save(partial_state)
    raise SafeStop(reason=response.status)
```

Para falhas transitórias de API própria, backoff limitado pode usar `min(base*2**attempt, 30s) + jitter(0, 0.5s)`, respeitando `Retry-After`. Não repetir indefinidamente nem transformar 429 em gatilho para trocar de IP/sessão.

### 4.3 Safety cap e amostragem

- Janela: até 90 dias, baseada em `post.date_utc`/`published_at`, não em `collected_at`.
- Posts: máximo inicial de 60 por auditoria; se houver mais, registrar truncamento e calcular sobre amostra segura.
- Comentários: primeira página, máximo inicial de 50 por post; registrar cobertura.
- Páginas adicionais somente quando o orçamento, permissão e rate controller permitirem.
- Um cap protege conta e custo; não exclui perfis por tamanho nem cria limite comercial para contas com mais de 10k seguidores.

### 4.4 O que não fazer

As seguintes recomendações do texto histórico são mantidas como **não normativas e proibidas para implementação**: rotacionar 5+ User-Agents; spoofing de navigator.webdriver; emitir TLS fingerprint humano; usar proxies residenciais/rotativos; sticky sessions de vários IPs; manter pool de 3–5 contas; simular rolagem/cliques para parecer humano; alternar contas/IPs após bloqueio; ou usar bibliotecas de bypass. Headers devem ser consistentes com o cliente oficial e não falsificados; fingerprint deve ser estável e honesto; geografia deve refletir ambiente real; CAPTCHA/challenge exige pausa e ação humana.

### 4.5 Cache, filtros e custo

Antes da rede: `cache.db` por `(platform, handle, window, scope, formula_version)`. Antes do Gemini: hash de comentários qualificados + prompt + modelo + versão. Filtrar localmente elogios genéricos, emojis isolados, spam, repetição e padrões bot-like; preservar contagem e motivo. Gemini recebe somente dados necessários, em até dois lotes, JSON estruturado e fallback de cache. Isso reduz quota, latência, tráfego e risco sem usar técnica de evasão.

## 5. Modelo de tempo e cenários de UX

Os tempos abaixo preservam os cenários do documento de origem; são **simulações**, não SLO. A latência real depende de cache, sessão, plataforma, volume, rate controller e disponibilidade do Gemini.

| Cenário | Posts | Coleta prior | IA/relatório | Total histórico | Faixa histórica |
|---|---:|---:|---:|---:|---:|
| Perfil enxuto/micro | 10 | ~37s | ~9,5s | ~54s | 45s–1m05s |
| Perfil moderado | 30 | ~111s | ~9,5s | ~2m08s | 1m50s–2m25s |
| Hiperativo/cap | 60 | ~222s | ~9,5s | ~4m | 3m35s–4m25s |

As simulações assumem ~3,7s/post e até duas requisições de IA. A UI deve recalcular ETA e atualizar cada item, não prometer o valor histórico. Se o tempo exceder budget, estado vira `partial`/`paused` e oferece retomar após validação.

## 6. Tratamento de exceções e recuperação

| Evento | Estado/ação normativa |
|---|---|
| Timeout/DNS/conexão | Retry limitado com backoff; máximo 3 tentativas locais; depois cache/partial e log |
| 429/rate limit | Parar novas chamadas, respeitar `Retry-After`/controlador, persistir checkpoint e aguardar; não rotacionar IP/sessão |
| 400/schema/`asset://laser.provider/ig_business_category_subvertical` | Registrar endpoint/versão; tentar somente fallback aprovado (`TopSearchResults`/consulta suportada); se falhar, partial |
| 401/403/sessão inválida | Invalidar sessão local, não imprimir cookies, salvar progresso, solicitar login humano/OAuth |
| Challenge/CAPTCHA | Pausar imediatamente, exibir mensagem de segurança e pedir resolução humana; não alternar para sessão/IP “limpo” |
| Perfil privado/não seguido | Recusar ou informar indisponibilidade; não tentar contornar privacidade |
| Falha em comentários de um post | Preservar itens coletados, marcar `post_status=partial`, continuar somente se rate controller permitir |
| Falha total no endpoint | Manter posts já processados; continuar demais apenas após decisão do controlador |
| JSON Gemini inválido | Marcar lote; preservar métricas determinísticas; não reprocessar em loop |
| Gemini ausente/quota | `gemini_status=not_configured/quota_exceeded`; relatório determinístico continua |
| >5 min/budget excedido | Interromper com checkpoint, mostrar retomada manual e ETA recalculado |

Mensagem mínima de segurança: **“A coleta foi pausada para proteger a sessão. Dados parciais foram salvos. Verifique a sessão/permissões e tente novamente mais tarde; nenhum mecanismo de contorno foi executado.”**

### 6.1 Checkpoint

```json
{
  "audit_id": "uuid",
  "handle": "@usuario",
  "window_days": 90,
  "last_post_id": "shortcode",
  "processed_posts": 18,
  "partial_comments": 622,
  "status": "partial|paused|retrying",
  "reason": "rate_limit|session_expired|timeout|schema_error",
  "session_owner": "criativododo",
  "created_at": "ISO-8601",
  "resume_requires": "explicit_user_confirmation"
}
```

## 7. Dados, processamento e saída

A janela usa `published_at=date_utc`. O pipeline deve seguir: resolver perfil → consultar cache → coletar bounded posts → coletar primeira páginA janela usa `published_at=date_utc`. O pipeline deve seguir: resolver perfil → consultar cache → coletublis por regex → pods/qualidade → Gemini opcional → score → exportação.

Cards do relatório: **Engajamento Real/ER**, demografia estimada, audiência/pods, publis, Score DODÔ, intenção, NSS, Top 3 e clusters. Cada card mostra `observed/derived/estimated/model_output`, fonte, janela, amostra, confiança e warnings. Exportadores HTML/PDF devem consumir o mesmo `analysis` canônico; o JSON acompanha `audit_id` e `formula_versions`.

### 7.1 Estado mínimo

```python
{
  "status": "idle|validating|running|retrying|partial|completed|failed|paused",
  "phase": "session|grid|comments|metrics|ai|export",
  "progress": 0.0,
  "eta_seconds": None,
  "session_owner": None,
  "processed_posts": 0,
  "total_posts": 0,
  "warnings": [],
  "error_code": None,
  "analysis": None
}
```

## 8. Observabilidade e testes

Registrar `audit_id`, timestamp, handle, sessão apenas por identificador não secreto, tipo de consulta, endpoint/cliente, status, atraso aplicado, tentativa, cache hit/miss, quantidade de posts/comentários, fase, motivo de pausa e duração. Nunca logar cookie, token, senha, conteúdo privado ou header de autenticação.

Métricas mínimas: `report_success_rate`, `session_validation_success_rate`, `partial_report_rate`, `429_count`, `403_count`, `challenge_count`, `cache_hit_rate`, `mean_post_latency`, `p95_report_duration`, `gemini_batch_count`, `export_success_rate` e `resume_count`.

Testes: validação de handle; thread sem `st.*`; ETA; progressão 0–100; cap 60/90d; cap 50 comentários; cache; sessão mismatch; 400 fallback; 401/403; 429 stop/backoff; timeout; challenge pause; partial pagination; Gemini absent/invalid JSON/quota; export only after state rule; no secrets in logs; demo sem rede/jitter.

## 9. Stack e operação

| Camada | Padrão aprovado | Alternativa/limite |
|---|---|---|
| UI | Streamlit | FastAPI/Flask/Express apenas se a SPEC futura justificar |
| Pipeline | Python thread + state polling | Fila externa não necessária no MVP |
| Coleta | Instaloader fixado, sessão autorizada, rate controller | API oficial Meta para contas profissionais |
| Persistência | SQLite `data/cache.db` | Redis/TTL somente em arquitetura futura |
| Segredos | `.env`/Keychain/secret store | Nunca `localStorage` aberto, Git ou logs |
| IA | `google-genai`, Gemini Flash (`gemini-flash-latest`), JSON e cache | Sem SDK/API paga |
| Relatório | HTML autocontido, PDF fpdf2, JSON | MCP/CRM futuro |
| Boot | `./iniciar_app.command` no macOS ou `.venv/bin/python -m streamlit run app.py` | Validar `.venv` e requirements antes de iniciar |

O arquivo original mencionava `curl_cffi`, `puppeteer-extra`, Redis e proxies residenciais como alternativas; eles permanecem listados nas referências por preservação histórica, mas não são dependências aprovadas. `curl_cffi`/`puppeteer-extra` não devem ser usados para falsificar fingerprint; proxies não devem ser usados para contornar limites.

## 10. Checklist operacional compacto

```text
[ ] .venv e requirements válidos; iniciar_app.command homologado
[ ] GEMINI_API_KEY somente no ambiente; INSTAGRAM_SESSION_FILE somente no ambiente
[ ] data/cache.db gravável; names_seed.json e ddd_uf.json presentes
[ ] Sessão ativa identificada; owner confere com execução; nenhum segredo no log
[ ] API oficial/permissão ou coleta pública permitida confirmada
[ ] Cache consultado antes da rede; janela e caps registrados
[ ] Controller ativo; nenhuma instância concorrente; 429/challenge interrompe
[ ] Filtro local ativo antes do Gemini; batches <=2; JSON/cache/hash
[ ] Progress 0–100%, ETA, status inferior e warnings funcionando
[ ] Exportação somente no estado permitido; HTML/PDF/JSON com provenance
[ ] Modo demo validado sem rede/jitter
[ ] Pytest verde; métricas/logs de saúde revisados
```

## 11. Fontes pré-existentes preservadas

As fontes abaixo já existiam no FINDER-003 original. Foram mantidas integralmente para rastreabilidade; as que descrevem evasão, bypass, proxy rotation, fingerprint spoofing ou automação não são endossadas como instrução de implementação.

| Fonte | Papel no material original | Tratamento nesta versão |
|---|---|---|
| [sociavault — scrape Instagram](https://sociavault.com/blog/scrape-instagram-without-getting-blocked) | pacing, cookies, headers, timing e proteção | Mantida como referência histórica; adotar somente rate limiting/cache |
| [sociavault — bypass rate limits](https://sociavault.com/blog/bypass-social-media-rate-limits) | backoff e estratégias de limite | Mantida; não adotar bypass |
| [sociavault — CAPTCHA](https://sociavault.com/blog/handle-captchas-social-media-scraping) | tratamento de CAPTCHA | Mantida; ação normativa é pausar e pedir humano |
| [Apify — hashtag scraper](https://apify.com/crawlerbros/instagram-hashtag-scraper) | validação de sessão | Mantida; preferir OAuth/Instaloader suportado |
| [Apify — advanced scraper/rate limit bypass](https://apify.com/oneary/instagram-advanced-scraper-rate-limit-bypass) | fingerprint/rate limit | Mantida apenas para identificar recomendações não permitidas |
| [Dev.to — scraper ban](https://dev.to/olams/scraping-instagram-without-getting-banned-what-actually-works-in-2026-3jfh) | timing, IP, sessão | Mantida; não usar pool/rotação para evasão |
| [Dev.to — Selenium resiliente](https://dev.to/tsvetang2/building-a-resilient-instagram-scraper-with-selenium-what-mimicking-human-behavior-actually-looks-egc) | fluxo resiliente | Mantida; não simular comportamento para ocultar automação |
| [Google Sites — scraper API](https://sites.google.com/view/alexwritesthings/instagram-scraper-api-extract-public-data-without-getting-blocked) | proxies/geografia | Mantida; proxies de evasão não aprovados |
| [Creatorflow — automation safety](https://creatorflow.so/blog/is-instagram-automation-safe-2026/) | segurança de automação | Mantida como contexto de risco |
| [DeepWiki — anti-detection](https://deepwiki.com/makiisthenes/Insta-mass-account-creator/5.3-anti-detection-strategies) | estratégias de anti-detecção | Mantida apenas como fonte não normativa; não reproduzir bypass |
| [Scrapfly — scrape Instagram](https://scrapfly.io/blog/posts/how-to-scrape-instagram) | timeout, 429, retry | Mantida para conceitos de resiliência |
| [DataDwip — scrape Instagram](https://www.datadwip.com/blog/how-to-scrape-instagram/) | stack e perfis públicos | Mantida; usar somente fontes permitidas |
| [Instagram](https://www.instagram.com/) | domínio de referência/Referer citado no original | Mantido; headers devem ser honestos e consistentes |

## 12. Fontes oficiais adicionadas

[1]: https://instaloader.github.io/troubleshooting.html — Instaloader Troubleshooting: 429, session files, login, checkpoint e limites.

[2]: https://instaloader.github.io/module/instaloadercontext.html — InstaloaderContext/RateController: sleep, requests, retry e controle de taxa.

[3]: https://developers.facebook.com/documentation/instagram-platform/overview — Meta Instagram Platform: contas profissionais, OAuth, Standard/Advanced Access, permissões, tokens, políticas e rate limits.

[4]: https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media/insights — Meta Instagram Media Insights: métricas, atraso, Stories, permissões e respostas vazias.

[5]: https://developers.facebook.com/docs/graph-api/overview/rate-limiting/ — Meta Graph API Rate Limiting: quotas, headers, throttling, spread de queries e parada após limite.

## 13. Referências externas preservadas no corpo original

Os links abaixo também permanecem registrados porque estavam presentes no arquivo de origem, ainda que não sejam fontes normativas de segurança: [sociavault](https://sociavault.com/blog/scrape-instagram-without-getting-blocked), [apify](https://apify.com/crawlerbros/instagram-hashtag-scraper), [dev](https://dev.to/olams/scraping-instagram-without-getting-banned-what-actually-works-in-2026-3jfh), [apify bypass](https://apify.com/oneary/instagram-advanced-scraper-rate-limit-bypass), [sites.google](https://sites.google.com/view/alexwritesthings/instagram-scraper-api-extract-public-data-without-getting-blocked), [sociavault rate limits](https://sociavault.com/blog/bypass-social-media-rate-limits), [deepwiki](https://deepwiki.com/makiisthenes/Insta-mass-account-creator/5.3-anti-detection-strategies), [creatorflow](https://creatorflow.so/blog/is-instagram-automation-safe-2026/), [scrapfly](https://scrapfly.io/blog/posts/how-to-scrape-instagram), [sociavault CAPTCHA](https://sociavault.com/blog/handle-captchas-social-media-scraping), [dev Selenium](https://dev.to/tsvetang2/building-a-resilient-instagram-scraper-with-selenium-what-mimicking-human-behavior-actually-looks-egc) e [datadwip](https://www.datadwip.com/blog/how-to-scrape-instagram/).

## 14. Nota de conformidade

A documentação anterior usava “anti-ban”, “indetectável”, “simulação humana”, rotação de User-Agent, spoofing de `navigator.webdriver`, TLS fingerprint e proxies rotativos. Esses conceitos foram preservados como contexto e fonte, mas **não fazem parte da arquitetura aprovada**. A arquitetura aprovada é: autorização explícita, API oficial quando disponível, dados públicos permitidos, sessão única pertencente ao usuário, cliente estável, cache, rate controller, backoff, cap, pausa em bloqueio, resolução humana de CAPTCHA, logs sem segredos e respeito aos Termos de Uso.
