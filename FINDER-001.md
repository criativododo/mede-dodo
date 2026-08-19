# FINDER-001: Manual Canônico de Certezas Técnicas & Métricas Autorais (v2.0.0)

> **Função:** roteador técnico compacto para a v2.0.0 do métricaDODÔ. Este documento separa certezas implementadas, contratos de integração e métricas autorais propostas para aprovação do Dani. O diretório `/legado/` é consultado somente sob pedido explícito e nunca é carregado automaticamente.

## 📑 1. Sumário & Roteamento Rápido

1. [Stack Técnica & SDKs Consolidados](#2-stack-técnica--sdks-consolidados)
2. [Modelo Matemático de Métricas Autorais](#3-modelo-matemático-de-métricas-autorais-branding--awareness)
3. [Arquitetura de Inteligência Híbrida & Contratos JSON](#4-arquitetura-de-inteligência-híbrida--contratos-json)
4. [Bases Locais & Heurísticas](#5-bases-locais--heurísticas-data)
5. [Design System Dodô & Exportação](#6-design-system-dodô--exportação)
6. [Rastreabilidade do Histórico](#7-rastreabilidade-do-histórico-legado)

### Roteamento em 30 segundos

| Pergunta | Fonte canônica | Regra |
|---|---|---|
| Posso criar código? | `DUMMY.md`, `specs/` e `docs/issues/manifest.json` | Não antes de SPEC e fórmulas autorais aprovadas pelo Dani. |
| Onde ficam as métricas? | `BENCHMARK-METRICS-001.md` | Fórmulas, pesos, cortes, amostragem e contratos de auditoria. |
| Como comparar portes? | Seção 3 deste Finder e seção 3 do benchmark | Comparar dentro de porte e formato; não usar ER bruto como nota universal. |
| Onde ficam os dados locais? | `/data/` | `names_seed.json`, `ddd_uf.json` e `cache.db`; preservar origem e cobertura. |
| Onde fica a View? | `src/app.py` | Apenas renderização e estado reativo; sem HTTP, SQL ou I/O de disco. |
| Onde ficam os adaptadores? | `src/features/{coleta,analise,relatorios}/` | Rede, heurísticas/IA e exportação ficam fora da View. |

> **Estado de aprovação:** o modelo matemático deste documento é a proposta autoral consolidada para co-criação. A existência da fórmula no arquivo não autoriza produção, score ou parecer sem aprovação explícita do Dani e evidência física em testes.

## 🛠️ 2. Stack Técnica & SDKs Consolidados

### 2.1 Imports e contratos

| Componente | Importação | Inicialização/Parâmetros | Estado |
|---|---|---|---|
| Google GenAI | `from google import genai`; `from google.genai import types`; `from google.genai.errors import APIError` | `genai.Client(api_key=os.environ["GEMINI_API_KEY"])`; `client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))` | A forma SDK foi validada no legado; o modelo histórico padrão era `gemini-flash-latest`, e o identificador 2.5 Flash é o alvo da v2.0.0. |
| Anthropic/Claude | — | — | Fora do escopo ativo da v2.0.0; referência histórica supersedida pela ADR-003. Não criar chave, cliente ou adaptador Anthropic. |
| Instaloader | `import instaloader` | `instaloader.Instaloader(max_connection_attempts=2)`; `Profile.from_username(loader.context, username)` | Forma validada no coletor histórico. |
| fpdf2 | `from fpdf import FPDF` | `pdf = FPDF()`; retorno `bytes(pdf.output())` | Forma validada no exportador histórico. |
| SQLite | `import sqlite3` | `sqlite3.connect(db_path)` com `conn.row_factory = sqlite3.Row` | Forma validada no cache local. |

O código deve obter segredos exclusivamente do `.env`, nunca gravá-los em arquivos versionáveis ou logs. O adaptador de modelo deve registrar modelo, versão de prompt, hash do input, status, timestamps e cobertura, sem registrar chaves, cookies ou conteúdo sensível [1] [2] [3].

### 2.2 Limites operacionais consolidados

O Gemini histórico usa lotes de até 100 comentários, no máximo dois lotes por perfil, e backoff de `2`, `4` e `8` segundos para erros transitórios `429`/`503`. A resposta deve ser JSON válido; ausência de chave, quota, timeout ou JSON inválido degrada para estado explícito, sem inventar dados [4].

A coleta Instaloader usa janela de até 90 dias, teto de 60 posts e pacing conservador. O caminho padrão da sessão é `~/.config/instaloader/session-<usuario>`, com referência operacional `~/.config/instaloader/session-elafashiomkt`. Ao ocorrer `429`, `403`, challenge ou checkpoint, a coleta pausa e não executa mecanismos de evasão [5] [6].

## 📊 3. Modelo Matemático de Métricas Autorais (Branding & Awareness)

As fórmulas completas, contratos de entrada e critérios de aceite ficam em [`BENCHMARK-METRICS-001.md`](BENCHMARK-METRICS-001.md). Este bloco fixa os princípios que não podem ser alterados silenciosamente.

### 3.1 Fórmula de Engajamento Ponderado por Formato

O engajamento autoral deve privilegiar sinais de marca e respeitar o formato. Pesos iniciais: Reel `F_f=1,00`, carrossel `F_f=1,10` e foto única `F_f=0,90`. Para cada publicação `i`, com `C_q` comentários qualificados, `S_h` compartilhamentos, `S_v` salvamentos, `L` curtidas e `R` alcance único:

\[
ER_{b,i}=\frac{5C_{q,i}+4S_{h,i}+4S_{v,i}+L_i}{R_i}
\]

Na janela de 90 dias, a taxa consolidada é:

\[
ER_{branding}=100\times\frac{\sum_i F_{f(i)}(5C_{q,i}+4S_{h,i}+4S_{v,i}+L_i)}{\sum_i F_{f(i)}R_i}
\]

O denominador deve ser explícito. Se o alcance não existir, não substituir silenciosamente por seguidores, impressões ou visualizações; retornar `indisponível` ou calcular uma variante com nome próprio e proveniência [7].

### 3.2 Tipologia de Comentários e Pesos de Sinal de Marca

Os comentários são classificados em um rótulo dominante, com possibilidade de sinais auxiliares: **A — desejo/percepção de estilo**, **B — conexão/afinidade real**, **C — intenção comercial secundária** e **D — ruído genérico/baixo sinal**. A intensidade autoral está em `A` e `B`; `C` é consideração, não conversão; `D` reduz confiança, mas não é automaticamente negativo.

\[
V_{AB}=100\times\frac{A+B}{A+B+C+D}
\qquad
A_{share}=\frac{A}{A+B}
\qquad
B_{share}=\frac{B}{A+B}
\]

Pisos editoriais iniciais: `V_AB ≥ 30%` é mínimo operacional, `≥ 40%` é saudável, `≥ 55%` é excelente; `V_AB < 25%` não aprova isoladamente. Controles recomendados: `A ≥ 15%`, `B ≥ 8%`, `D ≤ 45%` e spam confirmado `< 5%`. Esses cortes são autorais e permanecem sujeitos à aprovação do Dani [8].

### 3.3 Tabela de Amostragem Estratificada por Porte (90 dias)

A taxonomia não pode ter sobreposição. A regra operacional é: Nano `<10k`, Micro `10k–49.999`, Midi `50k–99.999`, Macro `100k–999.999`, Mega `≥1M` seguidores. A tabela abaixo define volume de comentários extraídos para análise, não o total que o coletor deve capturar.

| Porte | Faixa de seguidores | Amostra de comentários | Margem de referência | Estratificação mínima |
|---|---:|---:|---:|---|
| Nano | `<10.000` | 150–300 | ±8–10 p.p. | 50% orgânico, 30% publi, 20% conteúdos recentes |
| Micro | `10.000–49.999` | 250–500 | ±6–8 p.p. | Reel, carrossel e foto; orgânico/patrocinado |
| Midi | `50.000–99.999` | 350–700 | ±5–7 p.p. | Pelo menos três semanas e três formatos |
| Macro | `100.000–999.999` | 450–900 | ±5–6 p.p. | Recorrente, patrocinado e viral separados |
| Mega | `≥1.000.000` | 600–1.200 | ±4–5 p.p. | Proporcional por alcance e formato |

Para uma proporção, usar `n0 = Z²p(1-p)/e²`, com `Z=1,96` e `p=0,5`; isso produz referências aproximadas de 96 comentários para ±10 p.p., 196 para ±7 p.p. e 385 para ±5 p.p. A amostra deve ser sistemática, separar blocos de 30 dias, formatos e orgânico/patrocinado, e reservar 10% para controle de qualidade [8] [9].

**Equiparação de portes.** Influenciadoras menores tendem a apresentar maior engajamento relativo por seguidor, enquanto portes maiores entregam mais alcance absoluto; essa relação é suportada por pesquisa acadêmica e por sínteses de estudos de campanhas, mas não autoriza uma curva universal [10] [11]. Portanto:

1. Exibir sempre `ER_bruto`, denominador, alcance/seguidores, número de posts e cobertura.
2. Comparar primeiro dentro de `porte × formato × janela`; usar percentil ou mediana do estrato, nunca o corte bruto de outro porte.
3. Calcular `ER_percentil_porte` apenas quando o estrato tiver referência suficiente; caso contrário, retornar `indisponível`.
4. Se houver mediana válida de um porte de referência, uma equivalência meramente comparativa pode ser exibida como `ER_equivalente = ER_observado × (Mediana_referência / Mediana_porte)`, sem substituir o valor observado nem alimentar score automaticamente.
5. Não aplicar “desconto” fixo para Mega nem “bônus” fixo para Nano. O porte contextualiza; qualidade, cobertura, consistência e sinais de marca decidem.

### 3.4 Brand Quality Index (BQI 0–100)

O BQI combina conversação, retenção/alcance e integridade do sinal. Os pilares são `P1=45%`, `P2=40%` e um redutor de ruído `P3` com fator máximo de 15%:

\[
P_1=100\times[0,60(A+B)/T+0,25A/(A+B)+0,15B/(A+B)]
\]

\[
P_2=100\times[0,30N(SR)+0,25N(SHR)+0,25N(VTR)+0,20N(QR)]
\]

\[
P_3=100\times[0,70(1-D/T)+0,30(1-Spam/Comentários)]
\]

`N(x)=100×clip((x-L)/(U-L),0,1)`. Os limites iniciais são `Save Rate 0,5%–4,0%`, `Share Rate 0,2%–2,0%`, `VTR 10%–40%` e `Alcance Qualificado 50%–90%`, calibrados por porte e formato antes de uso produtivo.

\[
BQI_{core}=0,45P_1+0,40P_2
\]

\[
BQI_{guarded}=BQI_{core}\times(0,85+0,15P_3/100)
\qquad
BQI_{0-100}=clip(100\times BQI_{guarded}/85,0,100)
\]

Faixas: `80–100 Excelente/Embaixadora`, `65–79 Saudável/Aprovada`, `50–64 Alerta/Baixa Afinidade`, `0–49 Não Recomendada`. Fraude provável, audiência desalinhada, risco reputacional, disclosure inadequado ou dados insuficientes são bloqueadores que prevalecem sobre qualquer nota.

### 3.5 Consistência Trimestral e Limite de Saturação de Publis

Para consistência, reportar mediana e média; a decisão usa mediana para não deixar um viral dominar. O índice recomendado é:

\[
CI=100\times[0,70(1-clip(IQR/(2M),0,1))+0,30(semana\ acima\ do\ piso/semanas\ observadas)]
\]

`CI ≥ 75` é consistente, `60–74` é aceitável com volatilidade e `<60` é instável. A densidade patrocinada é:

\[
SD=unidades\ patrocinadas/unidades\ comparáveis
\]

`SD ≤ 20%` é preferencial; `20–25%` é tolerável com ressalvas; `25–33%` é alerta; `>33%` não é recomendado para embaixada. Calcular também `BrandMix = marcas parceiras únicas/publis totais` e observar o desempenho do conteúdo imediatamente posterior à publi [8].

## 🤖 4. Arquitetura de Inteligência Econômica & Contratos JSON

A arquitetura de IA da v2.0.0 usa **heurística local + Gemini 2.5 Flash**. O Claude 3.5 Sonnet e a dependência Anthropic foram retirados do escopo por decisão do Dani; a separação View Pura permanece válida.

### 4.1 Pré-triagem e fallback local

Heurísticas locais resolvem apenas casos determinísticos e inequívocos: comentário vazio, sequência exclusivamente composta por emojis, spam evidente e padrões de ruído versionados. Comentários curtos ou ambíguos não devem ser forçados para `D`; devem seguir para o Gemini ou retornar `uncertain`.

O mesmo contrato JSON deve ser usado pelo resultado local e pelo resultado do Gemini, sempre informando `provider_used`, `fallback_level`, `status`, `confidence`, `prompt_version` quando aplicável e `data_gaps`.

### 4.2 Papel do Gemini 2.5 Flash

O Gemini faz triagem dos comentários não resolvidos localmente e redige o parecer editorial a partir de um resumo matemático já calculado. O cliente usa `google.genai`, saída JSON estrita, batching de até 100 comentários por lote e limite operacional de dois lotes por perfil. O limite é configurável e deve ser versionado.

Para a classificação A/B/C/D, o Gemini deve retornar uma única categoria dominante, evidência literal presente no comentário, código de razão, confiança e estado. Quando não houver evidência suficiente, deve retornar `label=null`, `status="uncertain"` e `confidence="low"`. O modelo não pode inventar intenção de compra, idade, gênero, localização ou contexto.

Para o parecer editorial, o Gemini recebe apenas métricas, sinais agregados, proveniência, cobertura e limitações. A saída contém veredito em uma frase, três pontos fortes de branding, dois alertas, formato ideal, confiança e lacunas de dados. Ele não recalcula `ER`, `BQI`, `CI`, `SD`, porte ou denominadores.

### 4.3 Contratos e modo convidado

```json
{
  "comment_id": "comentario-001",
  "label": "A|B|C|D|null",
  "status": "classified|uncertain|invalid",
  "confidence": "high|medium|low",
  "evidence": "trecho literal presente no comentário",
  "provider_used": "local_heuristic|gemini_2_5_flash",
  "fallback_level": "local_primary|gemini_primary|local_fallback|indisponivel"
}
```

Sem chave, diante de rate limit, timeout ou schema inválido, o sistema usa o fallback local e, quando os dados forem insuficientes, retorna `indisponível`. Não existe fallback para Claude ou outro provedor. Nenhum fallback pode esconder status, origem, modelo, versão do prompt, cobertura ou lacunas.

## 🗄️ 5. Bases Locais & Heurísticas (/data/)

### 5.1 `names_seed.json` — gênero estimado / IBGE

`data_loaders.py` lê o JSON com UTF-8. A base curada possui 1.984 nomes derivados de fonte comunitária que cita o serviço público do IBGE; não é a base bruta completa. Normalizar acentos/caixa, consultar contagens `F`/`M` e classificar apenas quando a proporção atingir `0,85`; caso contrário, `indeterminado`. Handles podem fornecer segmentos alfabéticos como fallback local [12] [13].

### 5.2 `ddd_uf.json` — regionalização

O JSON mapeia DDD para UF. Procurar padrões de telefone no texto, cruzar o DDD com a tabela e, em paralelo, localizar menções normalizadas de estados/cidades. Deduplicar UFs dentro do comentário e expor cobertura; “Pará” exige acento no texto original para não confundir com a preposição “para” [13].

### 5.3 `cache.db` — SQLite e TTL de 24h

O contrato mínimo contém `profiles(username, bio, followers_count, updated_at, source, audit_report)` e `posts_cache(username, post_id, raw_payload, likes_count, comments_count, collected_at)`, com chave única `(username, post_id)`. Consultas são parametrizadas, `source` separa real/demo e o cache válido deve ter `updated_at`/`collected_at` dentro do TTL operacional de 24 horas. Nunca misturar dados de fontes diferentes nem apagar cache sem autorização [14].

## 🎨 6. Design System Dodô & Exportação

### 6.1 Tokens de estilo

| Token | Valor |
|---|---|
| Cannoli | `#F5F4EC` |
| Vermelho Haute | `#810100` |
| Borda | `1px solid #E5E0D8` |
| Raio editorial | `12px` |
| Tipografia de títulos | Work Sans |
| Tipografia de corpo | Elms Sans |
| Tipografia técnica | IBM Plex Mono, somente em dados técnicos |

Manter contraste de texto branco sobre Vermelho Haute, foco visível, estados de ausência explícitos e nenhuma paleta externa, gradiente ou superfície branca pura [15].

### 6.2 PDF editorial e CSV

Os exportadores são funções puras: `generate_html_report(analysis) -> str`, `generate_pdf_report(analysis) -> bytes` e `generate_csv_report(analysis) -> bytes`. O PDF usa `fpdf2`, fonte core e normalização segura; o CSV usa `csv.writer`/UTF-8 e cabeçalho `secao,campo,valor,procedencia`. Nenhum exportador acessa rede, disco ou estado da View; cada valor informa `observado`, `derivado`, `estimado` ou `indisponivel` [16].

## 📦 7. Rastreabilidade do Histórico (/legado/)

| Fonte histórica | Consulta pontual |
|---|---|
| `legado/SPRINT-002/BENCHMARK-001.md` | Benchmark anterior, contratos de proveniência, amostragem, BQI, consistência e saturação. |
| `legado/src/gemini_analyzer.py` | Imports `google.genai`, batching, JSON mínimo e retry. |
| `legado/src/scraper.py` e `rate_controller.py` | Sessão, Instaloader, janela de 90 dias, teto de 60 posts, pacing e parada segura. |
| `legado/src/data_loaders.py` e `demographics.py` | Leitura dos JSONs, limiar de gênero, DDD e cobertura. |
| `legado/src/database.py` | Schema SQLite, origem do cache, snapshots e filtros temporais. |
| `legado/src/exporter.py` | Contratos HTML/PDF/CSV e proveniência. |
| `legado/app.py` e `legado/docs/finders/FINDER-006.md` | Apenas tokens de estilo; código acoplado ao Streamlit é proibido. |
| `legado/SPRINT-002/FINDER-001.md`, `FINDER-003.md` e `docs/issues/` | Contexto de arquitetura, segurança, limites metodológicos e decisões históricas. |

### Referências

[1]: <legado/src/gemini_analyzer.py> "Cliente histórico Google GenAI"
[2]: <legado/src/scraper.py> "Coletor histórico Instaloader"
[3]: <legado/src/database.py> "Cache SQLite histórico"
[4]: <legado/src/gemini_analyzer.py> "Batching e contrato JSON Gemini"
[5]: <legado/src/scraper.py> "Sessão, janela e teto de coleta"
[6]: <legado/src/rate_controller.py> "Pacing e parada segura"
[7]: <legado/SPRINT-002/BENCHMARK-001.md> "Benchmark histórico de denominadores"
[8]: <legado/SPRINT-002/BENCHMARK-001.md> "Tipologia, BQI, consistência e saturação"
[9]: <legado/docs/issues/ISSUE-0008.md> "Amostragem e pipeline real"
[10]: <https://www.sciencedirect.com/science/article/pii/S0148296324002509> "Less is more: Engagement with the content of social media influencers"
[11]: <https://kellercenter.hankamer.baylor.edu/news/story/2025/follower-count-vs-engagement-uncovering-best-influencer-strategy> "Follower Count vs. Engagement, Baylor University"
[12]: <legado/docs/issues/ISSUE-0006.md> "Proveniência da base de nomes"
[13]: <legado/src/demographics.py> "Heurísticas locais de gênero e região"
[14]: <legado/src/database.py> "Schema e validade do cache"
[15]: <legado/docs/handoffs/HANDOFF-SPRINT-003.md> "Tokens e guardrails editoriais"
[16]: <legado/src/exporter.py> "Contratos de exportação"
