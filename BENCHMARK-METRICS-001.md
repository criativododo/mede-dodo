# BENCHMARK-METRICS-001: Modelo Autoral de Branding & Awareness (v2.0.0)

> **Status:** proposta canônica para co-criação e aprovação do Dani. Este documento define contratos, fórmulas, pesos e cortes para auditoria de criadoras de moda feminina; não constitui uma verdade universal de mercado nem autoriza produção antes de SPEC, testes e aprovação.

## Sumário

1. [Princípios e escopo](#1-princípios-e-escopo)
2. [Engajamento ponderado por formato](#2-engajamento-ponderado-por-formato)
3. [Tipologia de comentários e sinais de marca](#3-tipologia-de-comentários-e-sinais-de-marca)
4. [Amostragem estratificada em 90 dias](#4-amostragem-estratificada-em-90-dias)
5. [Equiparação por porte](#5-equiparação-por-porte)
6. [Brand Quality Index — BQI 0–100](#6-brand-quality-index--bqi-0100)
7. [Consistência trimestral e saturação de publis](#7-consistência-trimestral-e-saturação-de-publis)
8. [Contratos JSON e proveniência](#8-contratos-json-e-proveniência)
9. [Parecer editorial e bloqueadores](#9-parecer-editorial-e-bloqueadores)
10. [Rastreabilidade e referências](#10-rastreabilidade-e-referências)

## 1. Princípios e escopo

O objetivo é medir **qualidade de relacionamento com a marca**, não apenas volume de interações. A análise deve separar alcance absoluto, taxa relativa, qualidade dos comentários, retenção, consistência, densidade patrocinada e cobertura da amostra. Todo número precisa carregar janela, escopo, denominador, fonte, status e ressalvas.

A comparação por porte é obrigatória. Influenciadoras menores tendem a gerar mais engajamento relativo por seguidor, enquanto maiores podem entregar mais alcance absoluto; estudos acadêmA comparação por porte é obrigatória. Influenciadomostram que a relação varia por ação e formato [1] [2]. Por isso, nenhum ER bruto deve ser convertido diretamente em nota ou comparado entre portes sem normalização contextual.

A v2.0.0 não incorpora fórmulas antigas de mercado. Os pesos abaixo são **decisões autorais propostas**, auditáveis e versionadas. O estado `indisponível` é preferível a zero silencioso quando alcance, visualizações, comentários qualificados ou referência de porte não estiverem disponíveis.

## 2. Engajamento ponderado por formato

### 2.1 Pesos de formato

A comparação deve ser feita dentro do formato antes de qualquer consolidação.

| Formato | Função principal | Peso `F_f` |
|---|---|---:|
| Reel | Descoberta, alcance incremental e compartilhamento | 1,00 |
| Carrossel | Detalhe de look, modelagem, retenção e salvamento | 1,10 |
| Foto única | Posicionamento estético e coerência visual | 0,90 |

### 2.2 Fórmula por publicação

Para cada publicação `i`, `R_i` é o alcance único; `C_q,i` é o número de comentários qualificados; `S_h,i` são compartilhamentos; `S_v,i` são salvamentos; e `L_i` são curtidas.

\[
ER_{b,i}=\frac{5C_{q,i}+4S_{h,i}+4S_{v,i}+L_i}{R_i}
\]

A versão percentual é `100 × ER_b,i`. Os pesos `5/4/4/1` representam força de sinal de branding e não pesos de conversão.

### 2.3 Consolidação em 90 dias

\[
ER_{branding}=100\times\frac{\sum_{i=1}^{n}F_{f(i)}(5C_{q,i}+4S_{h,i}+4S_{v,i}+L_i)}{\sum_{i=1}^{n}F_{f(i)}R_i}
\]

Para cada formato `f`, calcular também:

\[
ER_{b,f}=100\times\frac{\sum_{i\in f}(5C_{q,i}+4S_{h,i}+4S_{v,i}+L_i)}{\sum_{i\in f}R_i}
\]

A implementação nunca deve apresentar `ER_branding` sem `denominator="reach_unique"`, `included_actions`, `content_scope`, `window_days=90`, `posts_n` e `coverage`. Se alcance não estiver disponível, não usar seguidores, impressões ou visualizações como substituto silencioso.

## 3. Tipologia de comentários e sinais de marca

Cada comentário recebe um rótulo dominante e pode receber sinais auxiliares. A tipologia não pretende diagnosticar personalidade nem provar conversão.

| Código | Sinal | Critério operacional |
|---|---|---|
| A | Desejo e percepção de estilo | Estética, caimento, modelagem, proporção, styling ou associação aspiracional com a marca. |
| B | Conexão e afinidade real | Identificação pessoal, relato contextualizado, diálogo continuado, confiança ou valores. |
| C | Intenção comercial secundária | Preço, tecido, tamanho, estoque, entrega, composição ou onde comprar; consideração, não conversão. |
| D | Ruído genérico/baixo sinal | Emoji isolado, elogio | D | Ruído genérico/baixo sinal | Emoji isolado, elogio | D | Ruído genérico/baixo sinal | Emoji isolado, elogio | D | Ruído genérico/baixo sinal | Emoji isolado, elogio | D | Ruído genérico/baixo sinal | Emoji isolado, elogio | D | Ruído genérico/baixo sinal | Emoji iso` mínimo operacional | `≥30%` |
| `V_AB` saudável | `≥40%` |
| `V_AB` excelente | `≥55%` |
| `V_AB<25%` | Não aprovar isoladamente, salvo evidência qualitativa excepcional |
| `A` mínimo recomendado | `≥15%` do total |
| `B` mínimo recomendado | `≥8%` do total |
| `D` máximo recomendado | `≤45%` |
| Spam confirmado | `<5%` |

`C` é reportado separadamente. Volume alto de perguntas comerciais pode indicar consideração, mas não deve ser rotulado como vendas ou conversão sem evento observável.

## 4. Amostragem estratificada em 90 dias

### 4.1 Referência estatística

Para estimar proporção com 95% de confiança:

\[
n_0=\frac{Z^2p(1-p)}{e^2}
\]

Usar `Z=1,96`, `p=0,5` como escolha conservadora e `e` como margem de erro. Referências: ±10 p.p. ≈ 96 comentários; ±7 p.p. ≈ 196; ±5 p.p. ≈ 385 [3]. Esses valores não substituem estratificação por formato, período e patrocínio.

### 4.2 Faixas por porte

| Porte | Seguidores | Amostra analisada | Margem indicativa | Estratificação mínima |
|---|---:|---:|---:|---|
| Nano | `<10.000` | 150–300 | ±8–10 p.p. | 50% orgânico, 30% publi, 20% conteúdos recentes |
| Micro | `10.000–49.999` | 250–500 | ±6–8 p.p. | Reel, carrossel e foto; orgânico/patrocinado |
| Midi | `50.000–99.999` | 350–700 | ±5–7 p.p. | Pelo menos três semanas e três formatos |
| Macro | `100.000–999.999` | 450–900 | ±5–6 p.p. | Recorrente, patrocinado e viral separados |
| Mega | `≥1.000.000` | 600–1.200 | ±4–5 p.p. | Amostra proporcional por alcance e formato |

### 4.3 Regra de seleção

Para cada criadora, listar posts publicados nos 90 dias, separar Reel/carrossel/foto, distinguir orgânico de patrocinado, ordenar em três blocos de 30 dias, selecionar sistematicamente dentro de cada estrato e reservar 10% para controle de qualidade/dupla codificação. Não concentrar a amostra nos posts de maior alcance. O coletor pode capturar todos os comentários e selecionar o subconjunto para análise.

## 5. Equiparação por porte

### 5.1 Certeza e limite

A literatura externa consultada converge em uma direção qualitativa: criadoras menores tendem a apresentar maior engajamento relativo por seguidor, enquanto criadoras maiores têm maior escala de alcance absoluto. O estudo do *Journal of Business Research* encontrou mais favoritos por seguidor para micro-influenciadores, mas não o mesmo padrão para retweets absolutos; a pesquisa resumida pela Baylor University, com mais de 1,8 milhão de compras em campanhas, encontrou maior engajamento e ROI para nano/micro em contextos específicos [1] [2].

Isso **não** autoriza uma curva universal de desconto. O padrão pode variar por plataforma, formato, nicho, objetivo, alcance, qualidade da audiência, frequência de publis e ação observada. O porte deve ser usado como contexto de comparação e não como prêmio automático para Nano ou punição automática para Mega.

### 5.2 Procedimento de normalização

1. Calcular e exibir o valor observado com seu denominador: `ER_bruto`, `ER_branding`, alcance, seguidores, posts e cobertura.
2. Comparar primeiro dentro do estrato `porte × formato × janela`.
3. Quando houver referência empírica suficiente, calcular o percentil do valor no mesmo estrato:

\[
ER_{percentil}=ECDF(ER\mid porte,formato,janela)\times100
\]

4. Como leitura opcional, nunca como substituição do observado, calcular:

\[
ER_{equivalente}=ER_{observado}\times\frac{Mediana_{referência}}{Mediana_{porte}}
\]

5. Se a mediana do porte ou da referência não for confiável, retornar `indisponível` em vez de criar fator.
6. Alimentar o BQI com o valor contextualizado e a cobertura somente quando o benchmark do estrato estiver versionado; preservar `ER_observado` no relatório.

A decisão final deve considerar conjuntamente `ER_percentil`, `V_AB`, `BQI`, `CI`, `SD`, bloqueadores e adequação de audiência. A equiparação reduz o viés de comparar uma nano com uma mega em uma escala bruta; ela não transforma métricas relativas em garantia de resultado.

## 6. Brand Quality Index — BQI 0–100

### 6.1 Pilares e normalização

Todos os pilares são normalizados para 0–100. O BQI usa `P1=45%`, `P2=40%` e um redutor de integridade com impacto máximo de 15%.

#### Pilar 1 — Conversação e afinidade

\[
P_1=100\times\left[0,60\frac{A+B}{T}+0,25\frac{A}{A+B}+0,15\frac{B}{A+B}\right]
\]

onde `T=A+B+C+D`. Divisões por zero retornam `indisponível`/zero técnico, nunca uma aprovação automática.

#### Pilar 2 — Retenção visual e alcance qualificado

\[
P_2=100\times[0,30N(SR)+0,25N(SHR)+0,25N(VTR)+0,20N(QR)]
\]

`SR=saves/reach`, `SHR=shares/reach`, `VTR=complete_views/views` para vídeo e `QR=qualified_reach/reach`. A normalização é:

\[
N(x)=100\times clip\left(\frac{x-L}{U-L},0,1\right)
\]

Limites iniciais por calibrar:

| Métrica | Piso `L` | Meta `U` |
|---|---:|---:|
| Save Rate | 0,5% | 4,0% |
| Share Rate | 0,2% | 2,0% |
| VTR | 10% | 40% |
| Alcance qualificado | 50% | 90% |

Para foto/carrossel sem VTR, substituir por `ATR=tempo_médio_de_exposição/tempo_de_referência` ou redistribuir o peso de VTR somente após decisão documentada.

#### Pilar 3 — Redutor de ruído

\[
P_3=100\times\left[0,70\left(1-\frac{D}{T}\right)+0,30\left(1-\frac{spam}{comentários}\right)\right]
\]

### 6.2 Fórmula final e cortes

\[
BQI_{core}=0,45P_1+0,40P_2
\]

\[
BQI_{guarded}=BQI_{core}\times\left(0,85+0,15\frac{P_3}{100}\right)
\]

Como o máximo teórico de `BQI_guarded` é 85, normalizar para a escala pública:

\[
BQI=clip\left(100\times\frac{BQI_{guarded}}{85},0,100\right)
\]

| BQI | Parecer inicial |
|---:|---|
| 80–100 | Excelente / Embaixadora potencial |
| 65–79 | Saudável / Aprovada para branding |
| 50–64 | Alerta / Baixa afinidade |
| 0–49 | Não recomendada |

Fraude provável, audiência desalinhada, disclosure inadequado, risco reputacional ou falta de dados mínimos bloqueiam o parecer independentemente do BQI.

## 7. Consistência trimestral e saturação de publis

### 7.1 Consistência

Calcular `ER_b,i`, `V_AB,i`, `P2,i`, alcance qualificado, ruído e BQI por post ou bloco semanal. A mediana é decisória e a média é diagnóstica:

\[
M=median(x_1,...,x_n)
\qquad
\bar{x}=\frac{1}{n}\sum_i x_i
\]

\[
CV_{robusto}=\frac{IQR(x)}{median(x)}
\qquad
MAD=median(|x_i-median(x)|)
\]

O índice autoral de consistência é:

\[
CI=100\times\left[0,70\left(1-clip\left(\frac{IQR}{2M},0,1\right)\right)+0,30\frac{semanas\ acima\ do\ piso}{semanas\ observadas}\right]
\]

`CI≥75` é consistente; `60–74` é aceitável com volatilidade; `<60` indica dependência de virais ou instabilidade.

### 7.2 Saturação de publis

\[
SD=\frac{unidades\ patrocinadas}{unidades\ comparáveis}
\qquad
BrandMix=\frac{marcas\ parceiras\ únicas}{publis\ totais}
\]

A unidade comparável é conteúdo de feed/Reel; Stories são reportados separadamente ou em blocos documentados.

| `SD` em 90 dias | Interpretação |
|---:|---|
| `≤20%` | Preferencial; aproximadamente uma publi para quatro peças orgânicas |
| `20–25%` | Tolerável com ressalvas |
| `25–33%` | Alerta |
| `>33%` | Não recomendado para embaixada |

Verificar também desempenho do post seguinte à publi, repetição da mesma marca e concentração de associação. Densidade patrocinada não é prova isolada de baixa qualidade.

## 8. Contratos JSON e proveniência

### 8.1 Entrada do motor de métricas

```json
{
  "profile": {"username": "@exemplo", "followers_count": 0, "tier": "nano"},
  "window": {"days": 90, "from": "ISO-8601", "to": "ISO-8601"},
  "posts": [{
    "post_id": "...", "format": "reel|carrossel|foto",
    "published_at": "ISO-8601", "reach": 0,
    "likes": 0, "shares": 0, "saves": 0,
    "qualified_comments": 0, "sponsored": false
  }],
  "comment_labels": {"A": 0, "B": 0, "C": 0, "D": 0, "spam": 0},
  "coverage": {"comments": 0.0, "reach": 0.0}
}
```

### 8.2 Saída auditável

```json
{
  "status": "ok|insufficient_data|indisponivel",
  "method_version": "BMQ-001-v2.0.0",
  "metrics": {
    "er_branding": {"value": 0.0, "unit": "pct", "denominator": "reach_unique"},
    "er_percentil_porte": {"value": 0.0, "unit": "pct", "status": "ok"},
    "bqi": {"value": 0.0, "unit": "0-100"},
    "v_ab": 0.0, "ci": 0.0, "sponsor_density": 0.0
  },
  "provenance": {
    "window_days": 90, "tier": "nano",
    "formats": ["reel", "carrossel", "foto"],
    "posts_n": 0, "sample_n": 0,
    "source": "local_scraper|manual|cache",
    "formula_version": "BMQ-001-v2.0.0"
  },
  "warnings": []
}
```

Toda saída deve informar fórmula, denominador, ações incluídas, escopo, janela, tamanho da amostra, cobertura, versão e ressalvas. `status=indisponivel` é um resultado válido; nunca preencher ausência com `0,0%` sem explicação.

## 9. Parecer editorial e bloqueadores

| Condição | Parecer |
|---|---|
| `BQI≥80`, `V_AB≥40%`, `CI≥75`, `SD≤20%`, `D≤35%`, sem bloqueador | Recomendada com alta afinidade |
| `BQI 65–79`, `V_AB≥30%`, `CI≥60`, `SD≤25%` | Recomendada com ressalvas |
| `BQI 50–64`, `V_AB<30%`, `CI<60`, `SD>25%` ou dependência de viral | Não recomendada para branding |
| Qualquer BQI + fraude provável, risco reputacional, audiência desalinhada ou disclosure inadequado | Não recomendada |

O parecer é editorial e exige revisão humana. Não é aprovação automática, não garante conversão e não deve ocultar dados ausentes. As fórmulas e cortes permanecem bloqueados para alteração via código sem aprovação do Dani e atualização da SPEC/issue correspondente.

## 10. Rastreabilidade e referências

| Fonte | Conteúdo preservado |
|---|---|
| `legado/SPRINT-002/BENCHMARK-001.md` | Fórmulas de ER, tipologia A/B/C/D, amostragem, BQI, consistência, saturação e matriz editorial. |
| `legado/src/gemini_analyzer.py` | Contratos JSON, batching e limites do Gemini. |
| `legado/src/demographics.py` e `data_loaders.py` | Heurísticas locais e cobertura. |
| `legado/src/database.py` | Cache, schema, timestamps e origem. |
| `legado/src/exporter.py` | Contratos de exportação e proveniência. |
| `legado/docs/issues/ISSUE-0008.md` | Recorte de 90 dias, data de publicação e amostragem operacional. |

### Referências externas

[1]: <https://www.sciencedirect.com/science/article/pii/S0148296324002509> "Less is more: Engagement with the content of social media influencers, Journal of Business Research, 2024"
[2]: <https://kellercenter.hankamer.baylor.edu/news/story/2025/follower-count-vs-engagement-uncovering-best-influencer-strategy> "Follower Count vs. Engagement: Uncovering the Best Influencer Strategy, Baylor University"
[3]: <https://www.calculatorcollection.org/en/calculators/statistics/sample-size-calculator/> "Sample size reference for proportions"
[4]: <legado/SPRINT-002/BENCHMARK-001.md> "Benchmark histórico local"
[5]: <legado/src/gemini_analyzer.py> "Contrato histórico Gemini"
[6]: <legado/src/database.py> "Contrato histórico SQLite"
