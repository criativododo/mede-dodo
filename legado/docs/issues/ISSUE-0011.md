# ISSUE-0011: Estados de fluxo, ações rápidas e paridade visual com o protótipo Paper (SPEC-006)

## Objetivo

Implementar, na tela real (`app.py`), os componentes desenhados no protótipo Paper "mede DODÔ"
(`https://app.paper.design/file/01M031HEGV5DY019PTPDDVX182`): estado de entrada editorial, indicador de
etapas no progresso, ações rápidas de exportação no header, mini-cards de parceria com avatar circular, e
uma segunda rodada de ajustes de paridade visual (avatar/bio reais no header, cor da barra de progresso)
pedida explicitamente depois de comparar a tela real com o protótipo.

## Tarefas de implementação

1. **Estado de entrada** (`app._render_hero_entrada`) — bloco editorial acima do formulário, visível só com
   `pipeline_state.status == "ocioso"`.
2. **Indicador de progresso** (`app._render_progress_stage_indicator` + `app._PROGRESS_STAGE_BY_ETAPA`) — 3
   estágios apresentacionais mapeados das etapas internas já existentes em `PIPELINE_STEPS`, sem criar etapa
   nova de pipeline.
3. **Ações rápidas no header** (`app._render_quick_export_actions`) — "Baixar PDF ↗"/"Exportar CSV ↗",
   disponíveis assim que `status == "concluido"`, sem depender do gate "Ver Relatório" (que continua controlando
   a seção "Exportação" completa no rodapé).
4. **`exporter.generate_csv_report`** — exportação nova em formato longo (tidy), aditiva, sem recalcular nada.
5. **Mini-cards de parceria** (`app._render_parceria_mini_card`) — avatar circular de iniciais (nunca foto
   inventada) + link real por post, em grade de até 4 colunas.
6. **Limpeza editorial** — aviso de Modo Demonstração movido do topo do relatório para dentro de "Detalhes da
   auditoria"; botão "↻ Reanalisar perfil" adicionado no rodapé do mesmo expander.
7. **Correção de fragilidade de teste pré-existente** — `app.py` chamava `main()` incondicionalmente na última
   linha; qualquer teste que fizesse `import app` (vários já faziam, para chamar funções de render isoladamente)
   reexecutava `main()` como efeito colateral, deixando um `st.form` "aberto" no script-run em execução. Isso já
   estava documentado como fragilidade conhecida em comentários de teste (`test_limpar_cache_button_...`) e só
   não quebrava nada porque nenhuma função chamada isoladamente tinha `st.button`. A adição do botão "Reanalisar
   perfil" (item 6) expôs o problema. Corrigido com o idiom padrão `if __name__ == "__main__": main()` —
   `Streamlit` executa o script-alvo com `__name__ == "__main__"` (confirmado lendo
   `streamlit/runtime/scriptrunner/script_runner.py`), então o comportamento real (`streamlit run app.py` /
   `AppTest.from_file`) não muda; só `import app` como módulo deixa de rodar `main()`.
8. **Segunda rodada — paridade visual pedida após comparação direta com o Paper:**
   - Barra de progresso nativa do Streamlit (`st.progress`, usada tanto no pipeline quanto nas barras de gênero
     da demografia) renderizava em azul nativo (`rgb(28,131,225)`), não no Vermelho Haute do Design System —
     corrigido via CSS (`[data-testid="stProgressBarTrack"]`).
   - `bio` já era coletada por `demo_fetch_fn`/`instaloader_fetch_fn` e persistida em `database.profiles.bio`,
     mas nunca era propagada para `analysis` nem exibida — passou a aparecer no header quando existe (campo
     aditivo, nenhuma heurística de coleta mudou).
   - Avatar circular de inicial (mesma técnica das parcerias) adicionado ao header, ao lado do `@handle`.

## Critérios de aceite (Definition of Done)

- [x] Os 3 estágios do progresso, as ações rápidas do header, o CSV novo, os mini-cards de parceria e a
      realocação do aviso de demo/Reanalisar estão implementados e cobertos por teste.
- [x] `pytest` passa sem regressão — 347/347 (337 preexistentes + 10 novos desta issue).
- [x] Validação visual manual via Playwright contra `streamlit run app.py` em Modo Demonstração, desktop
      (1440×1000): header com avatar/bio/ações rápidas, formatos, mini-cards de parceria, barras de gênero em
      vermelho haute, aviso de demo dentro da auditoria, botão "Reanalisar perfil" — console sem erros.
- [ ] **Paridade visual completa com o protótipo Paper — parcial, não integral.** Ver "Gaps" abaixo para o que
      ficou de fora deliberadamente, por regra de governança ou por ausência de dado real.

## Gaps (o que ficou de fora deliberadamente)

1. **Categoria/localização do perfil no header** — o protótipo Paper mostra um badge de categoria
   (`Moda & Lifestyle`) ao lado do `@handle`. Não existe nenhum campo de categoria em `analysis`, no schema do
   banco (`database.profiles`) nem em nenhum ponto do pipeline de coleta — implementar exigiria capturar um dado
   novo (fora do não-escopo "não alterar coleta" de SPEC-005/SPEC-006). Não implementado; não fabricado.
2. **Avatar como foto real** — o protótipo usa uma foto de perfil circular. Não existe URL de avatar em nenhum
   ponto do pipeline (`scraper.py` nunca captura `profile_pic_url`). Implementado como iniciais sobre superfície
   neutra (mesma técnica das parcerias) em vez de inventar uma foto ou usar um placeholder genérico enganoso.
3. **Grade de hero metrics em 4 colunas, como no Paper** — **não implementado, de propósito.** SPRINT-003
   "Safety Shield" item 5 (`docs/handoffs/HANDOFF-SPRINT-003.md` §3) proíbe explicitamente "introduzir uma grade
   de três ou quatro hero metrics" — decisão de produto documentada (evitar grade genérica, manter contraste de
   escala). O protótipo Paper foi desenhado sem essa restrição em mente. Mantido 2×2 (`_render_primary_kpis`,
   inalterado). Se o objetivo for realmente adotar a grade de 4, é uma revisão de governança que precisa decisão
   explícita de quem conduz o projeto — não uma escolha unilateral de implementação.
4. **Links "Ver post ↗" dentro de `st.dataframe`/`LinkColumn`** (Posts de maior repercussão, Posts com melhor
   conversão) continuam azul nativo do navegador de dados do Streamlit, não a pílula vermelha usada nos
   mini-cards de parceria. A regra CSS `.stApp a { color: vermelho-haute }` já existe desde SPEC-004, mas o
   `st.dataframe` do Streamlit atual renderiza células via canvas (glide-data-grid), fora do alcance de CSS do
   DOM — confirmado inspecionando o elemento renderizado. Corrigir exigiria substituir essas duas tabelas por
   mini-cards HTML (como os de parceria), mudança maior e fora do escopo desta issue.
5. **"↻ Reanalisar perfil" usa a mesma pílula vermelha cheia** dos outros botões — o Design System não tem uma
   variante "ghost"/texto-só, então não foi criada uma classe nova só para esse botão (SPRINT-003 Safety Shield
   item 10 pede não introduzir tokens/decoração novos). O protótipo Paper mostrava um texto mudo sem
   preenchimento; a versão real é uma pílula pequena, discreta pela posição (canto do expander), não pela cor.

## Notas de implementação

- `analysis["bio"]` e a normalização `@` de `analysis["publis"][i]["marcas"]` (aplicada tanto no mini-card
  quanto no `generate_csv_report`) são as duas únicas mudanças desta issue que tocam dado exibido fora da UI
  pura — ambas são propagação de dado já coletado, não nova heurística.
- Nenhuma fórmula de `src/metrics.py`/`src/scoring.py`/`src/demographics.py` foi tocada.
