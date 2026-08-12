# métricaDODÔ (MVP)

Aplicação desktop de uso pessoal (MEI) para auditoria e validação de influenciadoras digitais com foco em engajamento real e custo zero.

## Estrutura do Repositório
- `specs/SPEC-001.md`: Especificação técnica oficial do projeto.
- `DUMMY.md`: Diretrizes inquebráveis de segurança e limites de API.
- `PROGRESS.md`: Estado físico das entregas e tarefas ativas.
- `docs/issues/`: Fatiamento atômico de tarefas de implementação.

## Como Executar
1. Criar e ativar o ambiente virtual (o Python do Homebrew bloqueia `pip install` direto — PEP 668):
   ```
   python3 -m venv .venv
   ```
2. Instalar dependências: `.venv/bin/python -m pip install -r requirements.txt`
3. Iniciar a aplicação: `.venv/bin/python -m streamlit run app.py`
4. Rodar a suíte de testes: `.venv/bin/python -m pytest tests/`

## Estado Atual (2026-08-12)
Pipeline local completo (coleta/cache → filtragem → demografia → pods/score → relatório)
funcionando de ponta a ponta em **Modo Demonstração** (dados fictícios determinísticos,
sem rede). Raspagem real do Instagram, cliente Gemini real e varredura de publis (RF-09)
ainda não implementados — ver `docs/issues/manifest.json` para o status por issue.
