# SPEC-006: Estados de fluxo, ações rápidas de exportação e mini-cards de parceria

**Sprint:** 005
**Status:** aprovada por instrução direta do usuário (mockup construído no Paper, arquivo "mede DODÔ" —
`https://app.paper.design/file/01M031HEGV5DY019PTPDDVX182/1-0/1-0` — seguido de "implemente as novas telas").
**Runtime:** Streamlit/Python local.
**Objetivo:** implementar, na tela real (`app.py`), os componentes desenhados no protótipo do Paper: estado de
entrada editorial, indicador de etapas no progresso, ações rápidas de exportação no header, avatar circular nos
mini-cards de parceria, e reorganização editorial (aviso de Modo Demonstração e botão de reanálise).

> Esta SPEC estende SPEC-005 (já implementada e integrada na main) — não revisita nenhuma fórmula, contrato de
> métrica ou regra de procedência definida lá. Onde há sobreposição, SPEC-005 continua soberana.

## 1. Escopo e não escopo

### 1.1 Escopo

1. **Estado de entrada** — bloco editorial (título + subtítulo) acima do formulário de busca, visível somente
   quando `pipeline_state.status == "ocioso"` (antes de qualquer tentativa de análise).
2. **Estado de progresso** — indicador de 3 etapas (Coletando métricas → Analisando comentários → Consolidando
   formatos) mapeado das etapas internas já existentes em `PIPELINE_STEPS`, sem criar nenhuma etapa nova de
   pipeline.
3. **Ações rápidas no header** — botões "Baixar PDF ↗" e "Exportar CSV ↗" junto ao bloco de seguidores do
   `_render_profile_header`, disponíveis assim que o relatório está `concluido` (sem depender do gate "Ver
   Relatório" que continua controlando a seção de Exportação completa no rodapé).
4. **Exportador CSV novo** — `src/exporter.generate_csv_report(analysis)`, formato longo (tidy: `secao, campo,
   valor, procedencia`), serializando campos já calculados — não recalcula nenhuma métrica.
5. **Mini-cards de parceria com avatar** — cada publi detectada (`analysis["publis"]`) ganha um card com avatar
   circular, handle da(s) marca(s) mencionada(s) na legenda daquele post, indícios e link real do post
   (`Ver post ↗`), em grade de até 4 colunas.
6. **Limpeza editorial** — o aviso `st.info("Resultado gerado em MODO DEMONSTRAÇÃO...")` sai do topo da tela de
   relatório e passa a viver dentro de "Detalhes da auditoria"; um botão discreto "↻ Reanalisar perfil" é
   adicionado no rodapé do mesmo expander, replicando o reset de tela já feito por "Gerar novo relatório".

### 1.2 Não escopo

Não alterar coleta, scraping, sessão, rate limiting, fórmulas de ER/TER/Score DODÔ/PostScore, contratos de
`src/metrics.py`/`src/demographics.py`, heurística de autenticidade, nem os exportadores HTML/PDF já existentes
além da nova função CSV aditiva. Não inventar avatar/foto/logo de marca — nenhuma URL de imagem existe no
pipeline de coleta atual (`filters.detect_sponsored_posts` não captura avatar). Não remover o gate "Ver
Relatório" da seção de Exportação completa (HTML/PDF/JSON) no rodapé. Não construir um componente Streamlit
customizado (`st.components.v2`) para a barra de busca — o formulário nativo (`st.text_input` +
`st.form_submit_button`) permanece, só ganha uma moldura editorial acima.

## 2. Componentes e contratos

### 2.1 Indicador de etapas (progresso)

Mapeamento fixo, só apresentacional — reutiliza a `etapa` já escrita em `state` por `_run_pipeline`/
`_make_coleta_progress_callback`, sem novo campo de estado:

| Etapas internas (`PIPELINE_STEPS`) | Rótulo de estágio exibido |
|---|---|
| `coleta` | 1. Coletando métricas |
| `filtragem`, `demografia`, `pods_score`, `gemini` | 2. Analisando comentários |
| `relatorio` | 3. Consolidando formatos |

O estágio ativo usa `--color-primary`/negrito; os demais ficam com opacidade reduzida. A barra de progresso e o
badge de ETA (`_format_eta`) já existentes continuam como estão — o indicador de etapas é aditivo, não substitui
nada.

### 2.2 `generate_csv_report(analysis) -> bytes`

Formato longo (uma linha por métrica) para consumo por planilha ou por ferramentas de IA que preferem tabela
plana a JSON aninhado:

```text
secao,campo,valor,procedencia
identidade,username,silviabraz,observado
identidade,followers_count,2218990,observado
kpis,engagement_rate_pct,6.40,derivado
formato_reels,post_count,18,observado
formato_reels,average_likes,61400.00,derivado
demografia,feminino_pct,89.00,derivado
parceria,post_1_marcas,@marca_fashion_demo,observado
parceria,post_1_link,https://www.instagram.com/p/abc123/,observado
```

Regras: nenhuma linha é criada para uma seção `indisponível` além de uma linha `status,indisponivel` explícita —
nunca `0` no lugar de ausência (mesma regra de SPEC-005 §5). Não recalcula nada: lê os mesmos campos já expostos
por `generate_html_report`/`generate_pdf_report`.

### 2.3 Mini-card de parceria

Fonte de dados: `analysis["publis"]` (um item por post com indício comercial, `src/filters.detect_sponsored_posts`
— já carrega `link` real daquele post específico). Não usa `brand_mentions` (agregado por handle, sem link de
post único) para este card — essa métrica continua exibida como tabela de resumo, inalterada.

| Elemento | Regra |
|---|---|
| Avatar circular | Iniciais da primeira marca citada na legenda (`marcas[0]`), maiúscula, sobre `--color-tag-bg`/borda `--color-border`. Sem marca identificada → glifo neutro (`—`), nunca um avatar genérico fingindo ser real. |
| Título | `marcas[0]` se houver; senão `"Publi sem marca identificada"` (rótulo honesto, não inventa handle). |
| Legenda | Indícios (`termos`) já existentes, sem alteração de fonte de dados. |
| Ação | Pílula `Ver post ↗` com `href` real (`_post_url`). Sem `shortcode`/link → pílula substituída por legenda muda `"link indisponível"`, nunca um `href="#"` fictício. |
| Grade | Até 4 colunas por linha, resumo limitado por `PARCERIAS_RESUMO_MAX` (já existente, inalterado). |

### 2.4 Ações rápidas do header

`_render_profile_header` ganha uma linha de botões (`st.download_button`) acima do bloco de seguidores:
"Baixar PDF ↗" (reusa `exporter.generate_pdf_report`, já existente) e "Exportar CSV ↗" (usa a nova função §2.2).
Chaves (`key=`) prefixadas com `header_` para não colidir com os botões homônimos da seção "Exportação" no
rodapé (`download_pdf_button` etc.), que continuam existindo e gated por "Ver Relatório".

## 3. Critérios de aceite

- [ ] O bloco editorial de entrada só aparece com `pipeline_state.status == "ocioso"`.
- [ ] O indicador de 3 etapas aparece durante `status == "rodando"`, com o estágio correto em destaque conforme
      a tabela §2.1.
- [ ] `generate_csv_report` existe em `src/exporter.py`, é testada isoladamente e não altera nenhuma função
      existente do exportador.
- [ ] Os botões "Baixar PDF ↗"/"Exportar CSV ↗" aparecem no header assim que o status é `concluido`, sem exigir
      clique em "Ver Relatório".
- [ ] A seção "Exportação" completa (HTML/PDF/JSON) no rodapé continua gated por "Ver Relatório", inalterada.
- [ ] As parcerias mostram avatar circular de iniciais (nunca uma foto inventada) e link real por post.
- [ ] O aviso de Modo Demonstração não aparece mais no topo da tela de relatório; ainda existe (mesmo texto)
      dentro de "Detalhes da auditoria".
- [ ] "↻ Reanalisar perfil" existe no rodapé de "Detalhes da auditoria" e reseta a tela do mesmo jeito que
      "Gerar novo relatório" (sem limpar cache).
- [ ] `pytest` passa sem regressão nos testes existentes; novos testes cobrem os itens acima.

## 4. Referências

[1]: Protótipo Paper "mede DODÔ" — `https://app.paper.design/file/01M031HEGV5DY019PTPDDVX182/1-0/1-0`, artboard
"métricaDODÔ — Relatório (SPEC-005)" e artboards "Estado 1 — Entrada" / "Estado 2 — Progresso".

[2]: `SPEC-005.md` — contrato soberano da tela de relatório, não revisitado aqui.

[3]: `../src/filters.py` (`detect_sponsored_posts`) e `../src/metrics.py` (`extract_brand_mentions`) — fontes de
dados reais para os cards de parceria; confirmam a ausência de qualquer campo de avatar/logo no pipeline atual.

[4]: `docs/issues/ISSUE-0011.md` — rastreamento desta sprint, incluindo os gaps que ficaram fora deste corte.
