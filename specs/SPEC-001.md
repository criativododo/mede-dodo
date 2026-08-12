# SPEC-001: métricaDODÔ (MVP Enxuto)

## 1. Visão Geral
O **métricaDODÔ** é uma aplicação desktop 100% local criada para auditar a qualidade de influenciadoras para campanhas de marketing. O objetivo é extrair inteligência real de engajamento, antifraude e demografia por amostragem sem custos com ferramentas terceiras e em conformidade com a LGPD (legítimo interesse sobre dados públicos).

## 2. Requisitos Funcionais (RF)
* **RF-01 (Input Único):** Campo de entrada aceitando `@perfil` ou URL completa do Instagram.
* **RF-02 (Janela Temporal):** Seletores de período de 30, 60 ou 90 dias (foco trimestral).
* **RF-03 (Coleta Local):** Raspagem local de posts públicos (legendas, formato, curtidas, comentários) utilizando cookies de sessão local.
* **RF-04 (Cache Local):** Armazenamento em SQLite (`data/cache.db`) para evitar re-raspagem desnecessária do mesmo perfil.
* **RF-05 (Filtro Heurístico em Python):** Separação local de comentários rasos (emojis, palavras únicas) antes de qualquer chamada externa.
* **RF-06 (Demografia Local):** Inferência de gênero cruzando o primeiro nome com a base pública do IBGE (SQLite/Parquet) e de região via DDDs e bio.
* **RF-07 (Processamento Gemini em Lote):** Envio dos comentários qualificados em 1 a 2 requisições em lote (batching) com saída estruturada em JSON para classificar intenção de compra e faixa etária.
* **RF-08 (Antifraude e Interação):** Cálculo do índice de repetição de comentaristas (pods) e taxa de resposta da criadora às dúvidas de seguidoras.
* **RF-09 (Varredura de Publis):** Mapeamento de marca e links de postagens comerciais passadas.
* **RF-10 (Score DODÔ & Dashboard):** Nota técnica de 0 a 10 e parecer final exibidos em interface Streamlit, com botão de exportação de relatório (PDF/HTML).

## 3. Requisitos Não-Funcionais (RNF)
* **RNF-01 (Custo Zero):** Uso exclusivo do ecossistema Python local e do plano gratuito da API Gemini.
* **RNF-02 (Rate Limit Protection):** Throttling com delays aleatórios (jitter) entre requisições de raspagem.
* **RNF-03 (Performance de API):** Máximo de 2 chamadas de API Gemini por perfil analisado.
* **RNF-04 (Privacidade):** Operação estritamente local, sem envio de dados para servidores terceiros.

## 4. Anexo: Estado de Implementação (atualizado 2026-08-12)

| Item | Status | Issue | Observação |
|---|---|---|---|
| RF-01 Input único | Feito | ISSUE-0004 | `app.py` |
| RF-02 Janela temporal | Feito | ISSUE-0004 | 30/60/90 dias |
| RF-03 Coleta local | Parcial | ISSUE-0001 | Cache/throttling/orquestração prontos; `fetch_fn` real do Instagram (cookies de sessão) pendente |
| RF-04 Cache local | Feito | ISSUE-0001 | SQLite em `data/cache.db` |
| RF-05 Filtro heurístico | Feito | ISSUE-0002 | `src/filters.py` |
| RF-06 Demografia local | Parcial | ISSUE-0002 / ISSUE-0006 | Gênero via base curada (1.984 nomes, não o dump bruto do IBGE); região via tabela DDD (67 códigos, não validada contra a fonte primária ANATEL nesta sessão) |
| RF-07 Gemini em lote | Parcial | ISSUE-0003 | Batching/schema/fallback prontos e testados com mock; cliente Gemini real não integrado |
| RF-08 Antifraude e interação | Feito | ISSUE-0005 | Pods (`calc_pod_index`) e taxa de resposta calculados; ambos dependem de dados reais de coleta (RF-03) para deixar de ser demonstração |
| RF-09 Varredura de publis | Não implementado | — | Placeholder explícito na UI e nos relatórios; sem issue própria aberta ainda |
| RF-10 Score DODÔ & Dashboard | Feito | ISSUE-0004 / ISSUE-0005 | Score com pesos heurísticos não calibrados com dados reais; dashboard funcional em Modo Demonstração |
| RNF-01 Custo zero | Mantido | — | Nenhuma dependência paga introduzida |
| RNF-02 Rate limit protection | Feito | ISSUE-0001 | Jitter 2-5s, só ativo quando há `fetch_fn` real (nunca em Modo Demonstração) |
| RNF-03 Máx. 2 chamadas Gemini/perfil | Feito | ISSUE-0003 | `chunk_into_batches` nunca gera mais de 2 lotes |
| RNF-04 Privacidade/operação local | Mantido | — | Nenhuma chamada de rede real feita ainda (nem para Instagram, nem para Gemini) |

Detalhamento de cada pendência em `docs/issues/ISSUE-000{1,2,3,4,5,6}.md`.
