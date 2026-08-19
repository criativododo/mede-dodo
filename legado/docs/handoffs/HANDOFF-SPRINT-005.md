# HANDOFF: Sprint 005 — Estados de fluxo, ações rápidas e paridade visual com o Paper

**Sprint:** 005
**Documento de execução:** `specs/SPEC-006.md`
**Rastreamento:** `docs/issues/ISSUE-0011.md`
**Origem:** protótipo desenhado no Paper Desktop (arquivo "mede DODÔ",
`https://app.paper.design/file/01M031HEGV5DY019PTPDDVX182`), seguido de "implemente as novas telas" e, depois
de uma comparação visual direta entre a tela real e o protótipo, "revise a parte visual, eu quero idêntico ao
Paper".

## 1. Resumo executivo

A Sprint 004 (SPEC-005) já tinha entregue a arquitetura de informação do relatório. Esta sprint pegou o
protótipo desenhado no Paper — hero de busca, card de progresso, mini-cards de parceria com avatar, ações
rápidas de exportação no header — e implementou o que era honesto implementar na tela real, sem fabricar dado
que o pipeline não coleta e sem violar as regras de governança já escritas em sprints anteriores (SPRINT-003
Safety Shield, SPEC-005 "não inventar avatar/bio/categoria").

O resultado é uma paridade visual **parcial e deliberada**: tudo que dependia só de estilo (cor, raio, espaço,
badge, avatar de iniciais, pílula de ação) foi implementado; o que dependia de dado inexistente (foto de perfil,
categoria) ou contrariava uma regra de produto já escrita (grade de 4 hero metrics) ficou de fora, documentado
em `ISSUE-0011.md`, não decidido silenciosamente.

## 2. O que foi implementado

| Item do protótipo Paper | Onde entrou no código | Observação |
|---|---|---|
| Estado de entrada (hero de busca) | `app._render_hero_entrada` | Moldura editorial acima do formulário nativo (`st.text_input`/`st.form_submit_button`); só aparece com `pipeline_state.status == "ocioso"`. |
| Estado de progresso (etapas + tempo estimado) | `app._render_progress_stage_indicator`, `app._PROGRESS_STAGE_BY_ETAPA` | 3 estágios mapeados das 6 etapas internas já existentes (`PIPELINE_STEPS`) — nenhuma etapa nova de pipeline. O badge de ETA já existia (`_format_eta`). |
| Ações rápidas de exportação no header | `app._render_quick_export_actions` | "Baixar PDF ↗"/"Exportar CSV ↗" no topo direito, liberados assim que `status == "concluido"` — não esperam o clique em "Ver Relatório" (que continua gateando a seção "Exportação" completa do rodapé). |
| Exportador CSV | `src/exporter.generate_csv_report` | Novo, formato longo (tidy: `secao,campo,valor,procedencia`). Não recalcula nada — só serializa o que já está em `analysis`. |
| Avatar circular nos mini-cards de parceria | `app._render_parceria_mini_card` | Iniciais da marca real mencionada na legenda daquele post (nunca uma foto inventada). Link real via `_post_url`; sem link, vira legenda muda. Grade de até 4 colunas. |
| Aviso de Modo Demonstração fora do topo | `app._render_audit_details` | Mesmo texto, realocado para dentro de "Detalhes da auditoria" (mesmo princípio já usado para o Score DODÔ na SPEC-005: fora do primeiro viewport, mas nunca escondido). |
| Botão "Reanalisar perfil" discreto | `app._render_audit_details` | Rodapé do expander de auditoria; mesmo reset de tela que "Gerar novo relatório" (nunca limpa cache). |
| **Segunda rodada — pedida após comparação visual direta com o Paper** | | |
| Barra de progresso vermelho-haute | CSS (`[data-testid="stProgressBarTrack"]`) | Estava azul nativo do Streamlit (`rgb(28,131,225)`), não vermelho — afetava tanto a barra do pipeline quanto as barras de gênero da demografia. |
| Avatar circular de inicial no header do perfil | `app._render_profile_header` | Mesma técnica das parcerias — iniciais, não foto. |
| Bio real no header | `app._run_pipeline` + `app._render_profile_header` | `bio` já era coletada por `demo_fetch_fn`/`instaloader_fetch_fn` e persistida em `database.profiles.bio` — só nunca tinha sido propagada para `analysis`. Campo aditivo, nenhuma heurística de coleta mudou. |

Efeito colateral encontrado e corrigido no caminho: `app.py` chamava `main()` incondicionalmente na última
linha, o que fazia qualquer `import app` "bare" (usado por vários testes para chamar funções de render
isoladamente — já documentado como fragilidade conhecida em comentários de teste) reexecutar `main()` e deixar
um `st.form` "aberto" no script-run em execução. Isso só virou um problema real quando o botão "Reanalisar
perfil" (o primeiro `st.button` dentro de `_render_audit_details`) expôs o bug. Corrigido com
`if __name__ == "__main__": main()` — comportamento real (`streamlit run`/`AppTest.from_file`) inalterado,
confirmado lendo o script runner do Streamlit.

## 3. Buracos que ficaram (deliberados, não esquecidos)

Detalhado em `docs/issues/ISSUE-0011.md` §"Gaps" — resumo aqui:

1. **Categoria e localização do perfil** (badge "Moda & Lifestyle" no protótipo) — não existe esse campo em
   nenhum ponto do pipeline. Implementar exigiria capturar um dado novo na coleta, fora do não-escopo desta
   sprint.
2. **Avatar como foto real** — não existe URL de avatar em nenhum ponto do pipeline. Usa iniciais, não uma foto
   inventada nem um placeholder genérico enganoso.
3. **Grade de 4 hero metrics, como no Paper** — **não implementada de propósito.** O protótipo foi desenhado sem
   a regra em mente, mas `HANDOFF-SPRINT-003.md` §3 item 5 proíbe explicitamente essa grade ("nunca 3 ou 4 hero
   metrics"), decisão de produto já documentada. Mantido 2×2. Se a intenção for realmente adotar 4-em-linha, é
   uma revisão de governança — pedir explicitamente, não assumir.
4. **Links "Ver post ↗" dentro de `st.dataframe`/`LinkColumn`** (Posts de maior repercussão / melhor conversão)
   continuam azuis, não vermelho-haute — essas tabelas renderizam em canvas (glide-data-grid), fora do alcance
   de qualquer regra CSS. Só os mini-cards HTML (parcerias) pegam a cor certa. Corrigir as duas tabelas exigiria
   trocá-las por mini-cards HTML também — mudança maior que esta sprint não cobriu.
5. **Botão "Reanalisar perfil"** usa a mesma pílula vermelha cheia dos outros botões — o Design System não tem
   uma variante "ghost"/texto-só, e criar uma só para esse botão contrariaria a regra de não introduzir
   decoração nova (`HANDOFF-SPRINT-003.md` §3 item 10). Discreto pela posição (canto do expander), não pela cor.
6. **Pendência herdada da Sprint 004** (`ISSUE-0010.md`, ainda não fechada): o KPI "Autenticidade da audiência"
   nos KPIs principais mostra o `value` legado em vez de `base_real_pct` — não tocado nesta sprint, continua em
   aberto.

## 4. Verificação

- `pytest` — 347/347 (337 preexistentes + 10 novos: 5 em `tests/test_exporter.py` para `generate_csv_report`,
  5 em `tests/test_app.py` para mapeamento de estágios, hero de entrada, botão Reanalisar e mini-card de
  parceria).
- Validação visual manual via Playwright contra `streamlit run app.py`, Modo Demonstração, desktop 1440×1000:
  estado idle (hero + formulário), header (avatar/bio/ações rápidas), formatos, mini-cards de parceria
  (avatar + pílula), demografia (barras vermelho-haute), auditoria (aviso de demo realocado + botão
  Reanalisar). Console do navegador sem erros nem warnings em nenhuma tela.
- Nenhum commit foi feito — mesma regra de governança já aplicada na Sprint 004 (`ISSUE-0010.md`): aprovação do
  usuário necessária antes de incorporar ao histórico Git.

## 5. Referências

- [SPEC-006.md](../../specs/SPEC-006.md) — contrato desta sprint.
- [ISSUE-0011.md](../issues/ISSUE-0011.md) — rastreamento completo, incluindo a seção "Gaps" com o raciocínio
  de cada item não implementado.
- [SPEC-005.md](../../specs/SPEC-005.md) — contrato da tela de relatório, não revisitado aqui.
- [HANDOFF-SPRINT-003.md](./HANDOFF-SPRINT-003.md) §3 — guardrails ainda em vigor (grade de hero metrics, não
  introduzir decoração nova) que moldaram as decisões de "não implementar" desta sprint.
- Protótipo Paper "mede DODÔ" — `https://app.paper.design/file/01M031HEGV5DY019PTPDDVX182`.
