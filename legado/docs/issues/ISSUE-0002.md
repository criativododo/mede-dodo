# ISSUE-0002: Filtragem Heurística e Demografia Local

## Objetivo
Implementar, 100% localmente (sem chamada a LLM), a separação de comentários rasos de comentários com intenção comercial relevante (RF-05), e a inferência de demografia (gênero e região) a partir de nome e sinais textuais (RF-06) — preparando o terreno qualificado que será enviado ao Gemini na ISSUE-0003.

## Tarefas de Implementação

1. **Filtro Heurístico (`src/filters.py`):**
   - Detectar comentários "rasos": só emoji, ou frases de elogio genérico de 1-2 palavras (ex: "linda", "top", "gata").
   - Classificar comentários por intenção comercial: preço, tecido, tamanho, envio, loja — via regex/keywords.
   - `filter_comments(comments)` separa `qualified` (não-rasos) de `shallow` (descartados antes de qualquer chamada externa, conforme DUMMY.md regra 2).
   - `isolate_high_intent(comments)` isola os comentários com pelo menos uma categoria de intenção comercial detectada.

2. **Demografia Local (`src/demographics.py`):**
   - `infer_gender(nome, names_db=...)`: cruza o primeiro nome com uma base local nome→gênero, retornando `feminino`/`masculino`/`indeterminado`.
   - `infer_region(texto, ddd_to_uf=..., region_keywords=...)`: extrai DDDs de números de telefone/menções no texto e mapeia para UF; também detecta menções diretas a estados/cidades.

3. **Testes TDD:**
   - `tests/test_filters.py`
   - `tests/test_demographics.py`

## Critérios de Aceite (Definition of Done)
- [x] `filter_comments` separa corretamente comentários rasos (emoji-only, elogio genérico) de qualificados.
- [x] `isolate_high_intent` identifica comentários de preço, tecido, tamanho, envio e loja.
- [x] `infer_gender` retorna `feminino`/`masculino`/`indeterminado` a partir de nome + base local.
- [x] `infer_region` extrai UF por DDD e por menção textual.
- [x] Testes de `filters` e `demographics` executados com sucesso via pytest (12/12).

## Notas de Implementação
- **Base de nomes do IBGE**: a integração com a base pública completa do IBGE (SQLite/Parquet, conforme RF-06) fica para uma issue de integração de dados subsequente. `infer_gender` recebe `names_db` como parâmetro injetável (com um pequeno dataset-semente embutido como default) — a interface já está pronta para receber a base oficial sem mudar a assinatura pública.
- **Tabela DDD→UF**: o dicionário embutido em `demographics.py` é um subconjunto parcial (capitais e DDDs mais comuns), não a tabela oficial completa da ANATEL. `infer_region` aceita `ddd_to_uf` injetável para permitir completar a tabela depois sem quebrar a interface.
