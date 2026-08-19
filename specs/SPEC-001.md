# SPEC-01-MEDE-DODO: Especificação Técnica Soberana do MVP (v2.0.0)

> **Status:** Ativa / Blueprint Oficial da v2.0.0  
> **Autor:** Dani Perrut (Criativo Dodô)  
> **Fase:** Fase 2 — Meio (Arquitetura & Especificação)  
> **Alvo:** Repositório métricaDODÔ (Local macOS)

> **Regra de precedência:** esta SPEC, o `DUMMY.md`, o `BENCHMARK-METRICS-001.md`, o `FINDER-001.md` e o ADR-001 formam o conjunto normativo da v2.0.0. Nenhum código de produção deve ser criado ou alterado fora de uma micro-issue aprovada e evidenciada.

---

## 1. Visão Geral & Proposta de Valor

O métricaDODÔ é uma aplicação local de inteligência de influência e auditoria estética/editorial de criadoras para marcas de moda feminina e lingerie. O MVP recebe um perfil do Instagram, coleta dados públicos dentro de uma janela de 90 dias, preserva os dados em cache local, calcula sinais autorais de branding e awareness e entrega um relatório editorial auditável.

| Elemento | Contrato soberano |
|---|---|
| Propósito | Avaliar densidade de comunidade, percepção de valor, qualidade de relacionamento e coerência editorial de uma criadora. |
| Diferencial de mercado | Foco estrito em **branding, awareness, densidade de comunidade e percepção de valor**, não em conversão direta ou ROI de clique. |
| Janela padrão | Trimestral, com `window_days=90`, data real de publicação e cobertura explícita. |
| Saída | View interativa Paper Desktop, parecer editorial humano-assistido, PDF autocontido e CSV tabular. |
| Fonte de verdade | Dados observados, proveniência, fórmulas versionadas e estados `indisponível`; nunca zeros silenciosos ou inferências sem cobertura. |

O sistema não promete alcance, vendas, conversão, localização certa de seguidores ou diagnóstico definitivo de autenticidade. Toda estimativa deve declarar método, amostra, janela, denominador, cobertura e ressalvas [1] [2].

## 2. Contrato Visual & Design System Dodô (Paper Desktop 1:1)

### 2.1 Referência e tokens

A interface deve espelhar 1:1 o layout aprovado no [Paper Desktop](https://app.paper.design/file/01M031HEGV5DY019PTPDDVX182/1-0). O link é referência visual de composição; os tokens abaixo são a fonte de implementação.

| Token | Valor obrigatório |
|---|---|
| Fundo Cannoli | `#F5F4EC` |
| Vermelho Haute | `#810100` |
| Superfícies/cards | Borda `1px solid #E5E0D8`, raio `12px`, sombra baixa quando prevista no layout |
| Tipografia de títulos | Work Sans |
| Tipografia de corpo | Elms Sans |
| Dados técnicos | IBM Plex Mono, somente em identificadores, números e inventário |
| Contraste de ação | Texto `#FFFFFF` sobre Vermelho Haute; foco visível em todos os controles |

Não introduzir gradientes, paletas externas, branco puro como superfície, template completo de terceiros ou estilos que desloquem a composição do Paper Desktop. A View deve preservar estados de ausência, erro, carregamento e baixa cobertura com texto e estrutura, não somente cor.

### 2.2 Componentes da interface

1. **Header de identidade:** input do `@username`, avatar circular da criadora, nome/identidade e logo ou foto da marca contratante. O header deve informar a janela de análise e o estado da coleta.
2. **Cards de métricas principais:** ER Branding contextualizado por porte, BQI `0–100`, Índice de Consistência `CI %` e Taxa de Saturação de Publis `SD %`. Cada card exibe unidade, denominador ou cobertura e status de proveniência.
3. **Bento Grid de gráficos e distribuições:** distribuição de formatos (Reels, carrossel e foto); tipologia A/B/C/D de comentários; demografia estimada por nomes e regionalização por DDD; e sinais de retenção/alcance quando disponíveis.
4. **Card de parecer editorial da IA:** caixa de destaque com `Recomendada com Alta Afinidade`, `Recomendada com Ressalvas` ou `Não Recomendada`, acompanhada de pontos fortes, bloqueadores e ressalvas de briefing. O texto não é aprovação automática nem garantia de conversão.
5. **Barra de ações:** exportação de Relatório PDF Editorial via `fpdf2` e download de CSV tabular. As ações devem ser idempotentes e não realizar nova coleta.

## 3. Arquitetura de Software (Feature-Based Folders)

### 3.1 Fronteiras

O sistema segue separação física por feature. A View não contém chamadas HTTP diretas, queries SQL, manipulação de arquivos ou lógica de negócio. Cada feature recebe dependências explícitas, retorna dados serializáveis e mantém testes independentes.

```text
src/
├── app.py                         # View pura/burra e estado reativo
└── features/
    ├── coleta/
    │   ├── scraper.py             # Instaloader, sessão, pacing e parsing
    │   └── database.py            # Cache SQLite e contratos de validade
    ├── analise/
    │   ├── ai_local.py            # Heurísticas, validação e fallback local
    │   ├── ai_gemini.py           # Triagem e parecer JSON em lotes
    │   ├── metrics.py              # ER, BQI, CI e SD autorais
    │   └── demographics.py         # Nomes e DDD/UF locais
    └── relatorios/
        ├── pdf_exporter.py        # PDF editorial autocontido
        └── csv_exporter.py        # CSV tabular auditável
```

### 3.2 View Pura / Burra (`src/app.py`)

`src/app.py` atua exclusivamente na renderização da UI e no gerenciamento de estado reativo do Streamlit. Pode receber eventos do usuário, chamar serviços internos e exibir estados, mas é terminantemente proibido conter SQL, `sqlite3`, chamadas HTTP diretas, `requests`, `urllib3`, escrita/leitura direta de disco ou acesso a segredos. A regra de fronteira é a mesma definida no ADR-001 [3].

### 3.3 Módulo de Coleta (`src/features/coleta/`)

`scraper.py` integra Instaloader com sessão persistida em `~/.config/instaloader/session-elafashiomkt`, pacing conservador, janela de 90 dias e teto de 60 posts. `database.py` mantém o cache em `data/cache.db`, TTL operacional de 24 horas, separação `source=real|demo`, timestamps UTC e consultas parametrizadas. Em `429`, `403`, challenge ou checkpoint, a coleta pausa de forma segura e não tenta evasão [4] [5].

### 3.4 Módulo de Análise (`src/features/analise/`)

`ai_local.py` resolve casos determinísticos, valida contratos, deduplica comentários e fornece o fallback sem rede. `ai_gemini.py` usa `google.genai` para classificar comentários ambíguos e redigir pareceres a partir de resumos matemáticos, em lotes de até 100 itens e no máximo dois lotes por perfil. A saída é JSON estrita e deve registrar provedor, fallback, confiança e lacunas. Não há integração Anthropic/Claude na v2.0.0. `metrics.py` implementa exclusivamente as fórmulas do `BENCHMARK-METRICS-001.md`; `demographics.py` cruza os datasets locais `data/names_seed.json` e `data/ddd_uf.json` e declara cobertura.

### 3.5 Módulo de Relatórios (`src/features/relatorios/`)

`pdf_exporter.py` gera PDF editorial autocontido com `fpdf2`; `csv_exporter.py` gera CSV UTF-8 com campos, valores e proveniência. Ambos recebem um payload resolvido, não acessam a View, não realizam rede e não escrevem diretamente no disco.

## 4. Modelo Matemático de Métricas Autorais

As fórmulas desta seção são a transposição operacional do [`BENCHMARK-METRICS-001.md`](../BENCHMARK-METRICS-001.md). Pesos e cortes são autorais, versionados e bloqueados contra alteração via código sem aprovação do Dani.

### 4.1 ER Branding ponderado por formato (Rodada 1 — aprovada, `BMQ-001-v2.0.0-r1`)

> Substitui os pesos preliminares desta seção. Congelado após a Rodada 1 da consultoria de métricas autorais (ver `docs/issues/issue-004-motor-metricas-autorais.md §3`) e implementado em `src/features/analise/metrics.py`.

Para cada publicação `i`, com `D_i` como o denominador resolvido (`resolve_denominator`: prioriza `reach_unique`; recorre a `followers_count` só quando o alcance está ausente ou é `<= 0`), `C_i` como comentários, `S_h,i` como compartilhamentos, `S_v,i` como salvamentos e `L_i` como curtidas:

\[
ER_{b,i}=\frac{3C_{i}+3S_{h,i}+2S_{v,i}+3L_i}{D_i}
\]

A taxa consolidada na janela é:

\[
ER_{branding}=100\times\frac{\sum_{i=1}^{n}F_{f(i)}(3C_{i}+3S_{h,i}+2S_{v,i}+3L_i)}{\sum_{i=1}^{n}F_{f(i)}D_i}
\]

Os pesos de formato são `F_Carrossel=1,20`, `F_Foto=1,00` e `F_Reel=0,80`. Formato desconhecido nunca recebe peso implícito: o post é excluído do agregado e a exclusão é registrada em `warnings`. O relatório deve exibir `denominator_mode` (`reach_unique`, `followers`, `mixed` ou `unavailable`), escopo, número de posts e cobertura. Alcance ausente nunca é substituído silenciosamente — o fallback para seguidores é sempre declarado em `denominator_mode` e em `warnings`.

Tipologia A/B/C/D, BQI, CI e densidade de patrocínio (§4.2–§4.4) — Rodadas 2 e 3 aprovadas pelo Dani em 2026-08-15 (ver ADR-002) e implementadas em `src/features/analise/metrics.py`. **Ressalva física registrada em `docs/issues/manifest.json`/`PROGRESS.md`:** o Pilar 2 do BQI (§4.4) exige `save_rate`/`share_rate`/`VTR`/`alcance_qualificado`, sinais que a coleta pública via Instaloader não expõe — `bqi` e `ci` retornam `indisponivel` em auditorias reais até uma futura expansão do coletor (fora do escopo da ISSUE-004). `comment_typology`/`V_AB`/Pilar 1 e `sponsor_density` (SD) já são calculáveis com dado real hoje.

### 4.2 Tipologia A/B/C/D

Comentários são classificados em um rótulo dominante pela ISSUE-005 (`ai_local.py`/`ai_gemini.py`) — `metrics.py` nunca classifica texto bruto, só agrega rótulos já resolvidos: `A` desejo/percepção de estilo; `B` conexão e afinidade real; `C` intenção comercial secundária; `D` ruído genérico/baixo sinal. O indicador de valor de marca é:

\[
V_{AB}=100\times\frac{A+B}{A+B+C+D}
\]

O patamar saudável inicial é `V_AB ≥ 40%`, com mínimo operacional em `30%` e excelência em `55%`. `C` não é conversão; `D` não é automaticamente negativo, mas reduz o sinal informativo.

O Pilar 1 do BQI (conversação e afinidade), com `T=A+B+C+D`:

\[
P_1=100\times\left[0,60\frac{A+B}{T}+0,25\frac{A}{A+B}+0,15\frac{B}{A+B}\right]
\]

Divisão por zero (amostra vazia ou `A+B=0` no segundo/terceiro termo) retorna `indisponível`/zero técnico, nunca aprovação automática (`calculate_comment_typology` em `metrics.py`).

### 4.3 Amostragem estratificada em 90 dias

| Porte | Seguidores | Comentários analisados |
|---|---:|---:|
| Nano | `<10.000` | 150–300 |
| Micro | `10.000–49.999` | 250–500 |
| Midi | `50.000–99.999` | 350–700 |
| Macro | `100.000–999.999` | 450–900 |
| Mega | `≥1.000.000` | 600–1.200 |

A seleção deve separar Reel, carrossel e foto; orgânico e patrocinado; e três blocos de 30 dias. Reservar 10% para controle de qualidade. Os números são volume de amostra, não limite de coleta.

### 4.4 BQI, CI e SD

O Pilar 2 (retenção visual e alcance qualificado) usa `SR=saves/reach`, `SHR=shares/reach`, `VTR=complete_views/views` (vídeo) e `QR=qualified_reach/reach`, cada um normalizado por `N(x)=100×clip((x-L)/(U-L),0,1)`:

| Métrica | Piso `L` | Meta `U` | Peso |
|---|---:|---:|---:|
| Save Rate | 0,5% | 4,0% | 0,30 |
| Share Rate | 0,2% | 2,0% | 0,25 |
| VTR | 10% | 40% | 0,25 |
| Alcance qualificado | 50% | 90% | 0,20 |

\[
P_2=100\times[0,30N(SR)+0,25N(SHR)+0,25N(VTR)+0,20N(QR)]
\]

**Nenhum desses quatro sinais é exposto pela API pública do Instagram via Instaloader** — `calculate_visual_retention` (`metrics.py`) retorna `indisponivel` sem os quatro simultaneamente, nunca aproxima com outro sinal. Como o BQI depende de P2, ele herda esse `indisponivel` em auditorias reais até uma futura expansão do coletor (fora do escopo da ISSUE-004).

O Pilar 3 (redutor de ruído), calculável com dado real (`comment_labels` da ISSUE-005):

\[
P_3=100\times\left[0,70\left(1-\frac{D}{T}\right)+0,30\left(1-\frac{spam}{T}\right)\right]
\]

O BQI usa `P1=45%`, `P2=40%` e o redutor `P3` com impacto máximo de 15%:

\[
BQI_{core}=0,45P_1+0,40P_2
\qquad
BQI_{guarded}=BQI_{core}\times(0,85+0,15P_3/100)
\qquad
BQI=clip\left(100\times\frac{BQI_{guarded}}{85},0,100\right)
\]

Sem `P3` (redutor de ruído indisponível), o BQI é calculado sem penalização (`P3=100`) e o resultado carrega um `warning` explícito — nunca falha silenciosamente. As faixas são `80–100` excelente, `65–79` saudável, `50–64` alerta e `0–49` não recomendado.

A Consistência (`CI`) usa a mediana `M` e o IQR dos valores semanais de ER Branding, mais a fração de semanas acima de um piso aprovado:

\[
CI=100\times\left[0,70\left(1-clip\left(\frac{IQR}{2M},0,1\right)\right)+0,30\frac{semanas\ acima\ do\ piso}{semanas\ observadas}\right]
\]

`CI≥75` é consistente; `60–74` é aceitável com volatilidade; `<60` é instável. `CI` exige um `floor` (piso) explícito e ao menos duas semanas de observação (`calculate_consistency` em `metrics.py`) — sem esses insumos, retorna `indisponivel`; o valor numérico do piso permanece uma decisão editorial aberta, não fabricada por código.

A Saturação de Publis (`SD`), calculável com dado real (`is_sponsored` por post, ISSUE-002):

\[
SD=100\times\frac{unidades\ patrocinadas}{unidades\ compar\text{á}veis}
\]

`SD≤20%` é saturação preferencial; `20–25%` tolerável; `25–33%` alerta; `>33%` não recomendado para embaixada. Unidade comparável é conteúdo de feed/Reel com formato reconhecido; Stories e formato desconhecido nunca contam como comparáveis.

O parecer editorial combinado (`editorial_opinion` em `metrics.py`) segue a tabela:

| Condição | Parecer |
|---|---|
| `BQI≥80`, `V_AB≥40%`, `CI≥75`, `SD≤20%`, `D≤35%`, sem bloqueador | Recomendada com alta afinidade |
| `BQI 65–79`, `V_AB≥30%`, `CI≥60`, `SD≤25%` | Recomendada com ressalvas |
| `BQI 50–64`, `V_AB<30%`, `CI<60`, `SD>25%`, ou dependência de viral | Não recomendada para branding |
| Qualquer BQI + fraude provável, risco reputacional, audiência desalinhada ou disclosure inadequado | Não recomendada |

Bloqueador ativo sempre vence, independente do BQI. Sem `BQI`/`V_AB`/`CI`/`SD` resolvidos simultaneamente, o parecer retorna `indisponivel` — nunca um veredito fabricado sobre dado ausente.

A equiparação de portes deve comparar dentro de `porte × formato × janela`, exibindo ER observado, percentil do estrato e cobertura. Não aplicar desconto fixo à Mega nem bônus fixo à Nano; porte contextualiza, mas qualidade de relacionamento e proveniência decidem [6] [7].

## 5. Contratos de Dados & Schemas JSON

### 5.1 Entrada canônica dos motores

```json
{
  "profile": {
    "username": "@exemplo",
    "followers_count": 0,
    "tier": "nano|micro|midi|macro|mega"
  },
  "window": {"days": 90, "from": "ISO-8601", "to": "ISO-8601"},
  "posts": [{
    "post_id": "...",
    "format": "reel|carrossel|foto",
    "published_at": "ISO-8601",
    "reach": 0,
    "likes": 0,
    "shares": 0,
    "saves": 0,
    "qualified_comments": 0,
    "sponsored": false
  }],
  "comments": [{"comment_id": "...", "text": "...", "username": "..."}],
  "coverage": {"comments": 0.0, "reach": 0.0}
}
```

### 5.2 Saída auditável

```json
{
  "status": "ok|insufficient_data|indisponivel",
  "method_version": "BMQ-001-v2.0.0",
  "metrics": {
    "er_branding": {"value": 0.0, "unit": "pct", "denominator": "reach_unique"},
    "bqi": {"value": 0.0, "unit": "0-100"},
    "ci": {"value": 0.0, "unit": "pct"},
    "sd": {"value": 0.0, "unit": "pct"}
  },
  "provenance": {
    "formula_version": "BMQ-001-v2.0.0",
    "window_days": 90,
    "posts_n": 0,
    "sample_n": 0,
    "source": "local_scraper|manual|cache",
    "coverage": 0.0,
    "generated_at": "ISO-8601"
  },
  "warnings": []
}
```

Toda métrica deve informar método, versão de fórmula, data/hora, contagem de posts, amostra, cobertura e ressalvas. `indisponivel` é estado válido e não deve ser convertido em `0,0%`.

## 6. Fluxo de Execução End-to-End

1. O usuário insere `@username` e seleciona a marca contratante no Streamlit.
2. `src/app.py` aciona `features/coleta/`; o serviço consulta o cache SQLite de 24 horas e somente dispara Instaloader quando não há cache compatível.
3. Os dados brutos entram em `features/analise/`: heurísticas locais resolvem casos determinísticos; Gemini 2.5 Flash classifica comentários ambíguos em A/B/C/D e, quando aplicável, redige o parecer editorial a partir do resumo; heurísticas de demografia processam nomes IBGE e DDDs; `metrics.py` calcula ER Branding, BQI, CI e SD. Sem chave, rate limit ou erro de schema, a saída degrada explicitamente para fallback local ou `indisponivel`.
4. `features/relatorios/` prepara payloads para PDF e CSV, sem nova coleta.
5. `src/app.py` renderiza o dashboard interativo no Bento Grid do Paper Desktop, exibindo valores, cobertura, estado e ressalvas.
6. A auditoria registra `source`, `method_version`, `formula_version`, janela, amostra, timestamp, warnings e decisão editorial.

## 7. Fatiamento em Micro-Issues (Roteiro da Fase Meio)

| Issue | Entrega | Dependência principal |
|---|---|---|
| ISSUE-001 | Scaffold visual no Streamlit, View Pura e layout Paper Desktop 1:1 | ADR-001 e tokens Dodô |
| ISSUE-002 | Módulo de coleta e cache SQLite, Instaloader e sessão | `data/cache.db`, `.env` e regras anti-ban |
| ISSUE-003 | Heurísticas demográficas locais | `data/names_seed.json` e `data/ddd_uf.json` |
| ISSUE-004 | Motor matemático de métricas autorais | `BENCHMARK-METRICS-001.md` aprovado |
| ISSUE-005 | Integração IA econômica: heurística local + Gemini Flash | Schemas JSON estritos, batching e fallback local |
| ISSUE-006 | Exportação de PDF `fpdf2` e CSV tabular | Contratos de relatório |
| ISSUE-007 | Conexão end-to-end, testes e homologação visual | Todas as issues anteriores |

Cada issue deve conter escopo, arquivos-alvo, pré-condições, critérios de aceite, testes, evidência física e atualização do `docs/issues/manifest.json`. Nenhuma issue pode alterar fórmulas ou SPEC sem decisão aprovada.

## 8. Critérios de Aceite & Definition of Done (DoD)

A entrega do MVP só pode ser considerada concluída quando todos os critérios seguintes forem satisfeitos:

- **Governança:** conformidade absoluta com `DUMMY.md`, `ADR-001`, `FINDER-001.md` e esta SPEC; nenhuma regra negativa é violada.
- **View:** `src/app.py` não contém imports de `sqlite3`, `requests` ou `urllib3`, nem queries SQL, HTTP direto ou I/O de disco.
- **Coleta:** Instaloader respeita sessão persistida, pacing, TTL de 24h, janela de 90 dias, teto de 60 posts e parada segura em rate limit.
- **Análise:** Heurísticas locais e Gemini recebem contratos JSON estritos; falhas degradam de forma explícita; nenhum Claude/Anthropic é utilizado; incerteza e indisponibilidade permanecem visíveis.
- **Métricas:** ER Branding, BQI, CI e SD possuem fórmulas versionadas, denominador, porte, formato, janela, amostra e proveniência; equiparação não usa bônus/desconto fixo.
- **Testes:** cobertura unitária em `tests/` para coleta, cache, heurísticas, schemas, métricas, fallback e exportação.
- **Visual:** renderização idêntica ao Paper Desktop nos navegadores padrão, com tokens Dodô, contraste, estados vazios e sem overflow.
- **Relatórios:** PDF autocontido e CSV tabular reproduzem o mesmo payload auditável, sem rede ou estado oculto.
- **Rastreabilidade:** issues concluídas no manifest, logs/testes anexados e `PROGRESS.md` atualizado com evidências físicas.

### Referências normativas

[1]: <../DUMMY.md> "Safety Shield e restrições negativas"
[2]: <../FINDER-001.md> "Manual canônico de certezas técnicas e métricas"
[3]: <../decisions/ADR-001-arquitetura-hibrida-e-view-pura.md> "ADR-001: arquitetura híbrida e View pura"
[4]: <../legado/src/scraper.py> "Implementação histórica Instaloader"
[5]: <../legado/src/database.py> "Implementação histórica SQLite"
[6]: <../BENCHMARK-METRICS-001.md> "Modelo autoral de Branding & Awareness"
[7]: <https://www.sciencedirect.com/science/article/pii/S0148296324002509> "Less is more: Engagement with the content of social media influencers"
