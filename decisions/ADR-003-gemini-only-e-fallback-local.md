# ADR-003 — Gemini-only com Heurística Local e Fallback Explícito

**Status:** Accepted  
**Data:** 2026-08-15  
**Decisores:** Dani / Projeto métricaDODÔ  
**Escopo:** ISSUE-005 — análise de comentários e parecer editorial  
**Supersede:** seleção de provedores de IA descrita na ADR-001; a separação View Pura permanece válida.

## Contexto

A arquitetura original previa Gemini 2.5 Flash para triagem e Claude 3.5 Sonnet para semântica profunda e parecer editorial. Durante a rodada consultiva, o Dani definiu que a solução deve priorizar sempre a alternativa mais barata que preserve qualidade suficiente e auditabilidade. Também definiu que não será utilizado Claude nesta versão.

Grande parte do trabalho não precisa de modelo: ER, BQI, CI, SD, pesos, denominadores, validações, deduplicação, casos óbvios de ruído e pareceres baseados em regras devem permanecer em código local. A IA deve ser acionada somente quando houver interpretação linguística necessária ou quando um resumo estruturado precisar ser redigido.

## Decisão

Adotar uma arquitetura de dois níveis:

1. **Heurística local e motor matemático** como primeira camada, sem chamada de IA, para toda regra determinística ou caso de alta certeza.
2. **Gemini 2.5 Flash** como único provedor de IA, acionado para comentários ambíguos, classificação A/B/C/D não resolvida localmente e redação do parecer editorial a partir de dados já calculados.

Não integrar Claude 3.5 Sonnet, Anthropic, `ai_claude.py` ou qualquer fallback silencioso para outro provedor na v2.0.0.

## Fluxo de fallback

```text
heurística local / metrics.py
        │
        ├── caso resolvido → saída local
        │
        └── caso ambíguo → Gemini 2.5 Flash
                                  │
                                  ├── sucesso → JSON validado
                                  │
                                  └── erro/rate limit/sem chave
                                             ↓
                                      fallback local
                                             ↓
                                  indisponível se insuficiente
```

A saída deve informar `provider_used`, `fallback_level`, `model_version`, `prompt_version`, `status`, `confidence`, `warnings` e `data_gaps`. Falha de IA nunca pode ser mascarada como certeza.

## Papéis

| Componente | Papel |
|---|---|
| `metrics.py` | Calcular métricas matemáticas, sem IA. |
| `ai_local.py` | Heurísticas conservadoras, validação, deduplicação e templates de fallback. |
| `ai_gemini.py` | Batching, prompts, cliente `google.genai`, schema estrito, retry limitado e cache. |
| View | Renderizar resultados e informar limitações; não conter lógica de negócio. |

## Classificação de comentários

O Gemini retorna uma categoria dominante entre A, B, C e D. Se houver ambiguidade ou contexto insuficiente, retorna `label=null`, `status=uncertain` e `confidence=low`. O sistema não deve forçar classificação para aumentar cobertura.

A heurística local pode resolver somente casos inequívocos de vazio, emoji puro, spam evidente ou padrões versionados de ruído. Comentários curtos como “linda” ou “amei” não devem ser classificados automaticamente como D, pois podem conter sinal de estilo ou afinidade.

## Parecer editorial

O parecer do Gemini terá estrutura fixa: veredito em uma frase, três pontos fortes de branding, dois alertas, formato ideal de ativação, confiança e lacunas de dados. O tom será editorial, direto e profissional. O Gemini não recalcula ER, BQI, CI, SD, porte ou denominadores e não decide contratação sozinho.

Quando o Gemini estiver indisponível, o sistema usará um parecer templateado local somente se houver regras aprovadas e dados mínimos. Caso contrário, retornará `indisponivel` com as lacunas.

## Consequências positivas

A decisão reduz custo, reduz dependência de rate limit de múltiplos provedores, simplifica testes, torna o comportamento mais previsível e deixa clara a fronteira entre cálculo determinístico e interpretação linguística. Também permite que a maior parte dos comentários seja resolvida sem chamada externa.

## Consequências negativas

A ausência do Claude pode reduzir a qualidade em casos de ironia, contexto complexo, ambiguidade elevada e pareceres estratégicos sofisticados. Essa limitação será compensada por baixa confiança, fallback explícito, revisão humana e registro de dados ausentes. Não se deve apresentar a solução Gemini-only como equivalente a uma análise premium de múltiplos modelos.

## Segurança e operação

O comentário é tratado como dado não confiável. Instruções inseridas no texto não podem alterar o prompt de sistema, solicitar segredos ou acionar ferramentas. A chave do Gemini deve vir do mecanismo de segredos e nunca aparecer em código, logs, fixtures ou documentos versionáveis.

O cliente terá timeout, retry limitado, tratamento de rate limit, validação de JSON, `additionalProperties=false`, cache versionado por entrada/prompt/modelo e nenhum loop infinito de fallback.

## Reversibilidade

A decisão é reversível por novo ADR. A arquitetura deve manter interfaces de provedor e contratos de saída suficientemente isolados para que um provedor adicional possa ser considerado no futuro sem reescrever `metrics.py` ou a View. Isso não autoriza implementar ou ativar Claude sem novo aceite.

## Critérios de revisão

Revisar este ADR somente se o custo real do Gemini, a taxa de incerteza, a qualidade dos pareceres, a disponibilidade do provedor ou as necessidades editoriais demonstrarem que a arquitetura atual não atende ao produto. Qualquer revisão deve apresentar evidência física, custos, taxa de fallback e impacto de qualidade.
