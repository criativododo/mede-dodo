# ISSUE-0006: Bases de Dados para Demografia Local (Nomes e DDD)

## Objetivo
Substituir os datasets-semente embutidos em `src/demographics.py` (`DEFAULT_NAMES_DB` com 8 nomes e `DEFAULT_DDD_TO_UF` com 12 DDDs) por bases mais completas, carregadas via um novo módulo `src/data_loaders.py`, injetáveis nos parâmetros `names_db`/`ddd_to_uf` já existentes em `infer_gender`/`infer_region` — sem alterar `src/demographics.py`.

## Tarefas de Implementação
1. **`src/data_loaders.py`:**
   - `load_names_db()`: carrega `data/names_seed.json` e retorna `{nome_normalizado: {"F": int, "M": int}}`.
   - `load_ddd_to_uf()`: carrega `data/ddd_uf.json` e retorna `{"11": "SP", ...}`.
   - Ambos aceitam `path` injetável (default aponta para os arquivos em `data/`), mantendo o mesmo padrão de testabilidade já usado em `src/database.py` (`DB_PATH` injetável).
2. **Dados estáticos:**
   - `data/ddd_uf.json`: tabela DDD→UF.
   - `data/names_seed.json`: base nome→contagem por gênero.
3. **Testes TDD (`tests/test_data_loaders.py`):** cobertura de forma (formato do dict, chaves normalizadas) e de integração real (chamando `demographics.infer_gender`/`infer_region` com os dados carregados).

## Critérios de Aceite (Definition of Done)
- [x] `load_ddd_to_uf()` retorna as 67 DDDs válidas do plano de numeração nacional, todas mapeadas para uma UF válida.
- [x] `load_names_db()` retorna um dicionário no formato exato esperado por `infer_gender`, com chaves normalizadas (minúsculo, sem acento) e mais de 500 nomes.
- [x] Testes de integração confirmam que `demographics.infer_gender`/`infer_region` funcionam corretamente recebendo os dados carregados por este módulo (não só o formato "no papel").
- [x] `src/demographics.py` **não foi alterado** (interface injetável já existente foi suficiente).
- [x] Testes executados com sucesso via pytest (7/7 em `test_data_loaders.py`; 57/57 na suíte completa), sem warnings.

## Notas de Implementação — Proveniência Real dos Dados

### Tabela DDD → UF (`data/ddd_uf.json`, 67 entradas)
- As páginas oficiais da ANATEL (`anatel.gov.br/hotsites/CodigosNacionaisLocalidade/...`) retornaram erro HTTP 520 (indisponível/bloqueado) em todas as tentativas de acesso nesta sessão — **não foi possível validar diretamente contra a fonte primária da ANATEL**.
- A tabela foi montada a partir do conteúdo obtido de **https://www.ruacep.com.br/ddd/uf/** (tabela completa DDD→UF, todos os 67 códigos), cruzada com o resumo de busca de **https://www.ddi-ddd.com.br/Codigos-Telefone-Brasil/** (que também afirma "67 códigos DDD, de 11 a 99, com números não atribuídos reservados") e com o conhecimento factual já presente no modelo sobre o plano de numeração nacional brasileiro — as três fontes convergem exatamente para os mesmos 67 pares DDD→UF.
- **Honestamente**: isto é uma tabela de conhecimento público estável (não muda desde a criação dos DDDs 47/48/49 em SC e do DDD 28 no ES, há anos), mas não foi confirmada byte-a-byte contra o PDF/planilha oficial da ANATEL nesta sessão por indisponibilidade do site oficial.

### Base de Nomes → Gênero (`data/names_seed.json`, 1.984 nomes normalizados)
- **Não é a base bruta completa do Censo do IBGE** (que tem centenas de milhares de nomes) — por decisão consciente de escopo ("base leve"), conforme instrução da tarefa.
- Fonte usada: repositório público **[MedidaSP/nomes-brasileiros-ibge](https://github.com/MedidaSP/nomes-brasileiros-ibge)** (GitHub), que descreve seu conteúdo como extraído do serviço público **"Nomes no Brasil" do IBGE** (API oficial de frequência de nomes por censo). Foram baixados os arquivos `ibge-fem-10000.csv` e `ibge-mas-10000.csv` (10.000 nomes mais frequentes por gênero, com colunas `nome`, `freq`, `rank`, `sexo`).
- Processamento aplicado: para cada gênero, os 1.000 nomes de maior frequência (`rank` 1–1000) foram selecionados como "incluídos"; para cada nome incluído, a contagem `F`/`M` foi obtida cruzando sua frequência real nos dois arquivos completos (não apenas nos top-1000, para não zerar artificialmente nomes unissex como "Alex" que têm presença real nos dois gêneros mas fora do top-1000 de um deles). Nomes foram normalizados (minúsculo, sem acento) via a mesma lógica de `demographics._normalize_name`; nomes que colidem após normalização tiveram suas contagens somadas.
- Resultado: 1.984 nomes normalizados únicos, arquivo de ~56 KB.
- **Limitação assumida**: os valores de frequência são reais (contagens do IBGE), mas o corte em top-1000 por gênero significa que nomes muito raros em ambos os gêneros simplesmente não aparecem na base (tratados como "indeterminado" por `infer_gender`, que já é o comportamento correto/seguro para nome desconhecido).
- Em nenhum momento este dataset é apresentado como "dados oficiais brutos do IBGE" — é uma base curada e reduzida, derivada de um dataset comunitário que por sua vez cita a API pública do IBGE como fonte original.
