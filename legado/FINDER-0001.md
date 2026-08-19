Com a análise dos documentos de arquitetura, especificações técnicas e o log de progresso, a extensão do impacto da descontinuação do modelo `gemini-1.5-flash` e do pacote `google.generativeai` (na versão `0.8.6`) no pipeline do **métricaDODÔ** é detalhada a seguir:

### 1. Extensão do Impacto no Pipeline

* **Interrupção da Análise de Intenção e Faixa Etária (RF-07):** O processamento de inteligência artificial do projeto depende do envio de comentários qualificados (filtrados localmente) para o Gemini para classificar a intenção de compra e a faixa etária estimada. Se o modelo `gemini-1.5-flash` ou a versão da SDK forem descontinuados, a análise real (fora do "Modo Demonstração") deixará de funcionar.
* **Comportamento Resiliente e Fallback:** O pipeline foi projetado para ser resiliente. Se o cliente Gemini falhar ou não estiver configurado, a etapa de análise da IA é pulada usando a constante de mensagem `GEMINI_NAO_CONFIGURADO_MSG`, exibindo uma nota explicativa no painel sem travar o restante da execução do dashboard Streamlit.
* **Aviso de Depreciação Existente:** A suíte de testes do projeto já apresenta **1 aviso de depreciação (deprecation warning)** vindo diretamente do pacote `google.generativeai`, sinalizando que a base de código atual está utilizando chamadas obsoletas que deixarão de funcionar em versões futuras da biblioteca.

---

### 2. Onde a Dependência está Instanciada (Arquivos e Funções)

A integração com o SDK `google-generativeai` está concentrada especificamente nos seguintes locais:

* **`src/gemini_analyzer.py` (Classe `RealGeminiClient`):**
  * É a classe que encapsula a chamada da SDK real do Google. Ela lê a chave de API diretamente de `os.environ.get("GEMINI_API_KEY")` e é onde o modelo (`gemini-1.5-flash`) e os parâmetros de configuração (como o `response_mime_type` para saída estruturada em JSON) são definidos para interagir com a API.
* **`src/gemini_analyzer.py` (Função `analyze_comments` / `call_gemini_batch`):**
  * Essas funções gerenciam a divisão dos comentários qualificados em até 2 lotes (de no máximo 100 comentários cada) e acionam o `RealGeminiClient`. É aqui também que ocorre o tratamento de exceções específicas da SDK, convertendo o erro de esgotamento de cota (`ResourceExhausted`) em `GeminiRateLimitError` para um fallback gracioso.
* **`app.py` (Função `_run_pipeline`):**
  * Na orquestração do pipeline, o `RealGeminiClient` é instanciado em segundo plano se a chave `GEMINI_API_KEY` estiver configurada no ambiente. Ele é passado como o parâmetro `gemini_client` para a thread de processamento.
* **`requirements.txt`:**
  * O arquivo de dependências lista o pacote `google-generativeai` (junto de outras bibliotecas open-source de uso gratuito), garantindo o versionamento estrito do ambiente virtual do projeto.

---

Para destravar o MVP do **métricaDODÔ** e realizar o *Go Live* o mais rápido possível, a decisão entre manter o SDK legado ou migrar imediatamente envolve trade-offs críticos de tempo de entrega, estabilidade e esforço de testes. 

Abaixo está a análise técnica comparativa entre as duas abordagens, considerando a estrutura atual do projeto:

---

### **Opção A: Apenas alterar o `model_name` mantendo o SDK atual (`google-generativeai`==0.8.6)**

Esta opção foca em manter a base de código do `RealGeminiClient` (`src/gemini_analyzer.py`) intacta, alterando apenas a string do modelo (por exemplo, de `gemini-1.5-flash` para um modelo legado que ainda esteja ativo no Google AI Studio).

*   **Prós:**
    *   **Lançamento imediato (Esforço Quase Zero):** Requer apenas a alteração de uma constante de string no código.
    *   **Preservação da integridade dos testes:** Toda a suíte de testes atual do projeto — que conta com **145 testes 100% verdes** — permanecerá intocada e funcional, pois os mocks em `tests/test_gemini_analyzer.py` que simulam a interface do SDK atual não precisarão ser reescritos.
    *   **Validação rápida do pipeline real:** Como a integração do `RealGeminiClient` no pipeline do `app.py` já está completa, essa mudança simples permite testar imediatamente o comportamento com uma chave `GEMINI_API_KEY` real.

*   **Contras:**
    *   **Sobrevivência com prazo de validade curto:** O próprio console de testes do projeto já emite **1 aviso de depreciação (deprecation warning)** vindo da biblioteca `google.generativeai`. Manter o SDK antigo significa ignorar esse aviso e postergar uma quebra inevitável.
    *   **Falta de suporte a novos modelos:** Modelos mais recentes e eficientes lançados pelo Google podem não ser retrocompatíveis ou não funcionar perfeitamente com a versão antiga do SDK (`0.8.6`).

*   **Riscos Técnicos:**
    *   **Quebra súbita em produção (*Decommissioning*):** O maior risco é o desligamento completo dos endpoints legados da API REST do Gemini por parte do Google. Se isso ocorrer, o `RealGeminiClient` falhará e, embora o pipeline do **métricaDODÔ** seja resiliente e exiba um fallback gracioso (`GEMINI_NAO_CONFIGURADO_MSG` ou erro tratado na UI), a funcionalidade de análise de intenção e faixa etária (RF-07) deixará de funcionar para o usuário final.
    *   **Acúmulo de débito técnico:** A necessidade de migração não deixará de existir, apenas será empurrada para frente, potencialmente gerando um cenário de manutenção sob pressão pós-lançamento.

---

### **Opção B: Migração definitiva para o novo SDK oficial `google.genai`**

Esta opção envolve atualizar o arquivo `requirements.txt` e reescrever o cliente de integração para utilizar a nova biblioteca recomendada pelo Google.

*   **Prós:**
    *   **Lançamento Robusto e Duradouro (*Future-proof*):** Garante que o MVP nasça alinhado com as diretrizes modernas do Google, eliminando o aviso de depreciação da suíte de testes e garantindo compatibilidade com os modelos atuais e futuros.
    *   **Melhor suporte a saídas estruturadas:** O novo SDK oferece melhorias na geração de respostas estruturadas (JSON), o que pode aumentar a confiabilidade da classificação de intenção de compra e faixa etária por comentário.
    *   **Segurança e Correções de Bugs:** A nova biblioteca recebe atualizações ativas, garantindo estabilidade contra mudanças de infraestrutura do Google.

*   **Contras:**
    *   **Atraso no Go Live (Esforço de Desenvolvimento):** Exige esforço imediato para reescrever a classe `RealGeminiClient`.
    *   **Necessidade de refatoração massiva de testes:** Os mocks construídos para simular o comportamento de chamada de lote (batching) e tratamento de erros de limite de cota (`GeminiRateLimitError`/`ResourceExhausted`) terão que ser completamente reescritos e revalidados em `tests/test_gemini_analyzer.py`.

*   **Riscos Técnicos:**
    *   **Regressão na Suíte de Testes:** Modificar o cliente e os mocks correspondentes pode desestabilizar os testes de integração do pipeline (`tests/test_app.py`), exigindo rodadas extras de depuração para colocar os 145 testes de volta no estado "verde".
    *   **Comportamento inesperado no tratamento de erros:** O novo SDK pode lançar exceções de rede ou cotas com nomes e estruturas diferentes da SDK antiga, exigindo revalidação cuidadosa para garantir que o pipeline continue ignorando lotes falhos sem travar a interface Streamlit.

---

### **Recomendação Técnica para o MVP**

Considerando que o **métricaDODÔ** é uma aplicação desktop de uso pessoal (MEI) com foco em **custo zero** e **MVP enxuto**:

1.  **Se o objetivo é colocar o produto no ar esta semana:** Siga com a **Opção A**. Ela é segura no curtíssimo prazo porque a integração está 100% testada e pronta. Isso permite que você valide a aplicação com o usuário final usando dados reais imediatamente. Abra uma nova tarefa no `PROGRESS.md` agendando a migração do SDK (Opção B) como o primeiro item do próximo ciclo de desenvolvimento.
2.  **Se você dispõe de 1 ou 2 dias adicionais de desenvolvimento:** Opte diretamente pela **Opção B**. Realizar a migração antes do Go Live evita que você tenha que mexer duas vezes em uma parte tão sensível do pipeline (IA e sua suíte de testes de batching) em um futuro muito próximo.


---

Caso a decisão seja migrar para o novo SDK oficial **`google.genai`**, a estrutura do cliente de inteligência artificial precisará ser reformulada para se adequar ao novo padrão de arquitetura unificada do Google. 

Abaixo está o mapeamento de como a sintaxe de chamada deve ser alterada e o design exato que a classe **`RealGeminiClient`** deve assumir em **`src/gemini_analyzer.py`**.

---

### 1. Mudança no Padrão de Chamada da SDK

No SDK legado (`google-generativeai`), a inicialização ocorria de forma global e o modelo era instanciado diretamente. No novo SDK (`google.genai`), **toda interação passa por uma instância explícita de `genai.Client`**, e as chamadas de geração de conteúdo são feitas através do sub-módulo `.models`.

*   **Padrão Antigo (Legado):**
    ```python
    import google.generativeai as genai
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
    ```

*   **Padrão Novo (`google.genai`):**
    ```python
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash", # Ou o modelo desejado
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    ```

---

### 2. Estrutura Exata da Classe `RealGeminiClient`

Para manter a compatibilidade com a resiliência de tratamento de erros e batching exigidos pelo projeto, as falhas de cota/limite de requisição devem ser traduzidas para a exceção customizada **`GeminiRateLimitError`**. No novo SDK, essas falhas disparam uma **`google.genai.errors.APIError`** com o código HTTP `429` (Too Many Requests).

O arquivo **`src/gemini_analyzer.py`** deverá ser estruturado da seguinte forma:

```python
import os
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Exceção customizada do projeto para garantir a resiliência do pipeline
class GeminiRateLimitError(Exception):
    pass

class RealGeminiClient:
    """
    Cliente real de integração com o Gemini utilizando a nova SDK oficial google.genai.
    """
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        # Recupera a chave diretamente das variáveis de ambiente do projeto
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada no ambiente de execução.")
        
        # O novo SDK exige a inicialização do objeto cliente
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate_content(self, prompt: str) -> str:
        """
        Executa a geração de conteúdo em formato estruturado JSON.
        """
        try:
            # Reescrita da chamada de geração seguindo o padrão unificado da nova SDK
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    # Garante que a saída venha estritamente como JSON estruturado para análise
                    response_mime_type="application/json"
                )
            )
            return response.text
            
        except APIError as e:
            # Captura erros de esgotamento de limite de requisições do Google AI Studio
            if e.code == 429:
                # Mantém o mapeamento para tratamento resiliente do pipeline
                raise GeminiRateLimitError("Limite de cota da API Gemini esgotado.") from e
            raise e
```

---

### 3. Impacto nos Testes e Mocks

Com essa reestruturação, os testes unitários em **`tests/test_gemini_analyzer.py`** precisarão ser atualizados. O mock do cliente antigo, que fingia retornar um objeto com o método `.generate_content` simulando a resposta JSON estruturada, precisará passar a simular a nova estrutura hierárquica do cliente (`client.models.generate_content`).

---

A transição do modelo do Gemini ou a atualização do SDK impactará a sua suíte de **145 testes atualmente verdes** de formas muito diferentes dependendo do caminho escolhido. 

Como o pipeline e a integração do `RealGeminiClient` em `app.py` foram desenhados de forma altamente desacoplada, você pode blindar a maior parte da suíte de testes de integração se jogar com inteligência arquitetural.

Abaixo está o mapeamento exato do impacto e o que precisará ser ajustado em `tests/` para manter a suíte verde.

---

### **Cenário A: Apenas alterar o `model_name` (Mantendo o SDK legado)**
Se você optar por apenas trocar a string do modelo (ex: de `"gemini-1.5-flash"` para outro modelo legado que ainda esteja ativo) em `src/gemini_analyzer.py`, o impacto na suíte de testes será **nulo**.

*   **Impacto nos Mocks:** Nenhum. Os mocks em `tests/test_gemini_analyzer.py` e `tests/test_app.py` simulam o comportamento de chamada do SDK antigo (`google-generativeai`). Como a assinatura do método e a estrutura de retorno continuam iguais, os mocks continuam válidos e todos os testes continuarão passando de primeira.
*   **O que ajustar:** Apenas se houver algum teste específico que faça um assert explícito sobre a string do nome do modelo (ex: `assert client.model_name == "gemini-1.5-flash"`). Caso exista, basta atualizar a string esperada no teste correspondente.

---

### **Cenário B: Migração definitiva para o novo SDK (`google.genai`)**
Se você optar por migrar para o novo SDK oficial `google.genai`, haverá um **impacto estrutural nos testes unitários**, mas você poderá **salvar os testes de integração** mantendo a casca (interface pública) de `RealGeminiClient` idêntica.

Aqui está o que muda e o que precisará ser ajustado em `tests/`:

#### 1. Reescrita dos Mocks do SDK (`tests/test_gemini_analyzer.py`)
No SDK antigo, o mock do cliente simulava uma chamada direta ao método `generate_content` do modelo instanciado. No novo SDK `google.genai`, toda chamada passa pela estrutura unificada `client.models.generate_content` [como detalhado no novo padrão do cliente].

*   **Como era o mock (antes):**
    ```python
    mock_client = MagicMock()
    mock_client.generate_content.return_value = MagicMock(text="{\"intencao_compra\": \"alta\"}")
    ```
*   **Como deve ser o mock (ajuste necessário):**
    ```python
    mock_client = MagicMock()
    # O mock agora precisa refletir a estrutura hierárquica do novo cliente (.models)
    mock_client.models.generate_content.return_value = MagicMock(text="{\"intencao_compra\": \"alta\"}")
    ```

#### 2. Atualização dos Mocks de Exceção de Cota (Rate Limit)
Em `tests/test_gemini_analyzer.py`, existem testes específicos para validar se o pipeline do **métricaDODÔ** trata graciosamente erros de limite de cota (`GeminiRateLimitError`), isolando lotes falhos sem derrubar o processo principal.

*   **Antes:** Os testes injetavam a exceção do SDK legado (geralmente baseada em `google.api_core.exceptions.ResourceExhausted`).
*   **Ajuste necessário:** O novo SDK dispara uma **`google.genai.errors.APIError`** com o código HTTP `429` para rate limits. Os testes unitários que validam o comportamento de cota estourada precisarão mockar o lançamento dessa nova exceção:
    ```python
    from google.genai.errors import APIError

    # Simula o erro de cota (Too Many Requests - HTTP 429) lançado pela nova SDK
    mock_client.models.generate_content.side_effect = APIError(message="Cota esgotada", code=429)
    ```

#### 3. Blindagem de `tests/test_app.py` (Testes de Integração)
O dashboard do Streamlit (`app.py`) orquestra o pipeline chamando o `RealGeminiClient`. Se você mantiver a **interface pública** do `RealGeminiClient` rigorosamente idêntica (ou seja, a classe ainda expõe o método `generate_content(prompt)` retornando uma string, encapsulando o novo SDK internamente), as funções que testam o fluxo no nível do aplicativo **não sofrerão impacto**.

*   Como o pipeline de integração em `tests/test_app.py` roda majoritariamente em **Modo Demonstração** (que gera dados locais sem acionar o Gemini) ou simulando o `RealGeminiClient` de alto nível, proteger a interface pública do wrapper evita que você precise reescrever testes de integração complexos do Streamlit.

---

### **Resumo de Ações para Manter a Suíte Verde (Opção B)**

Caso escolha a migração, o roteiro de ajustes em `tests/` é:

1.  **Em `tests/test_gemini_analyzer.py`:**
    *   [ ] Ajustar os patches de importação para apontar para `google.genai`.
    *   [ ] Atualizar a estrutura dos mocks para usar `.models.generate_content` em vez de `.generate_content`.
    *   [ ] Substituir a simulação de falhas de cota antiga por `APIError(code=429)`.
2.  **Em `tests/test_app.py`:**
    *   [ ] Certificar-se de que nenhum mock de integração dependa da estrutura interna antiga da SDK, mockando apenas a classe `RealGeminiClient` se necessário.

Seguindo esse fluxo, você garante que os **145 testes permaneçam verdes** e protege a estabilidade do **métricaDODÔ** contra regressões de pipeline.

---

Para declarar o MVP do **métricaDODÔ** oficialmente pronto para produção (*Go Live*), consolidando a robustez da coleta local de dados com a inteligência do novo SDK do Gemini, utilize o checklist técnico final estruturado abaixo:

---

### **1. Validação de Variáveis de Ambiente**

*   **`GEMINI_API_KEY` (Obrigatória):** Essencial para inicializar o `RealGeminiClient` com o novo SDK. Se ausente, o pipeline executará em modo de degradação graciosa (exibindo uma nota informativa sobre a ausência do serviço de IA sem travar o painel), mas a análise de intenção de compra e faixa etária por IA (RF-07) só funcionará de forma real com esta chave ativa.
*   **`INSTAGRAM_SESSION_FILE` (Opcional):** Define o caminho absoluto para o arquivo de cookies de sessão do Instagram. Embora o sistema conte com o mecanismo de autodetecção automática que varre e carrega o primeiro arquivo `session-*` funcional em `~/.config/instaloader/`, configurar essa variável explicitamente no servidor blinda o deploy contra variações de caminhos de sistema operacionais.

---

### **2. Ajustes e Auditoria no `requirements.txt`**

Para assegurar que o deploy em produção ocorra sem problemas de importação, garanta que as dependências estejam exatamente configuradas:

*   **Substituição do SDK do Gemini:** Remova o pacote legado `google-generativeai` do arquivo e inclua o novo pacote unificado oficial:
    ```text
    google-genai
    ```
*   **Correção de Drift de Coleta:** Garanta a presença explícita do Instaloader em sua versão estável corrigida:
    ```text
    instaloader==4.15.3
    ```
*   **Dependências de Interface e PDF:** Verifique se as dependências abaixo estão listadas para renderização do painel Streamlit e exportação correta de relatórios sem erros de espaçamento:
    ```text
    streamlit
    fpdf2
    pytest
    ```

---

### **3. Preparação da Infraestrutura de Arquivos Locais**

*   **Diretório de Dados (`/data`):** O projeto exige que a pasta `data/` na raiz possua permissão de escrita e leitura. Nela devem estar:
    *   `data/names_seed.json`: Base curada contendo os 1.984 nomes do IBGE essenciais para a estimativa de gênero local (RF-06).
    *   `data/ddd_uf.json`: Tabela nacional com o mapeamento dos 67 códigos DDD do Brasil para identificação de região geográfica.
    *   `data/cache.db`: Banco de dados SQLite criado automaticamente pela aplicação para persistência offline e proteção de limites de requisição.
*   **Sessão do Instagram Ativa:** Verifique se o arquivo físico de sessão do perfil de auditoria (ex: `criativododo`) está devidamente gravado e acessível no diretório padrão:
    ```path
    ~/.config/instaloader/session-criativododo
    ```

---

### **4. Comandos de Inicialização e Boot**

Dado que sistemas modernos restringem instalações globais de pacotes Python (PEP 668), a sequência exata de comandos para levantar o ambiente de produção isolado é:

1.  **Criação e Ativação do Ambiente Virtual:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
2.  **Instalação Limpa de Dependências:**
    ```bash
    .venv/bin/python -m pip install -r requirements.txt
    ```
3.  **Execução do Servidor Streamlit:**
    ```bash
    .venv/bin/python -m streamlit run app.py
    ```

---

### **5. Verificação de Integridade Pós-Deploy (*Sanity Checks*)**

Antes de abrir o acesso geral ao dashboard:

*   [ ] **Suíte de Testes Verde:** Execute `.venv/bin/python -m pytest tests/` para assegurar que a suíte completa de **145 testes está passando sem falhas** no ambiente final.
*   [ ] **Validação da Sidebar:** Abra a aplicação no navegador e verifique a sidebar. O Streamlit deve exibir o rótulo visual **"Sessão ativa: <usuario>"**. Isso valida que o motor de autodetecção de cookies local está operacional em ambiente real sem cair em requisições anônimas instáveis.
*   [ ] **Teste de Análise Real:** Execute uma auditoria de perfil de teste fora do Modo Demonstração. Certifique-se de que o pipeline resgate dados reais de comentários, filtre termos publicitários em legendas (RF-09) e realize as chamadas ao Gemini sem estourar os limites estruturais de 2 lotes de requisição por perfil.

Com essa lista verificada e validada, o **métricaDODÔ** está pronto para operar em produção com custos de infraestrutura e consumo de APIs de IA inteiramente zerados.

---

Para guiar a caça a bugs e o mapeamento de pontos cegos na transição para o **Go Live** do seu projeto (`metricaDODO`), precisamos analisar o cenário sob a ótica do **Vibe Coding Profissional (Spec-Driven Development e PREVICE)**. A transição de uma integração volátil com fallbacks (Instagram) para uma refatoração de infraestrutura pesada (migração do SDK do Gemini) é o momento onde mais ocorrem falhas sistêmicas catastróficas.

Abaixo está o mapeamento das armadilhas mais comuns, dos acoplamentos ocultos e da estratégia de auditoria para blindar o seu sistema.

---

### 1. A Armadilha do "Cobertor de Pobre" (*Wakamol Bug*) na Refatoração
No Vibe Coding literal (prompts freestyle sem planejamento), o maior risco é o efeito **"cobertor de pobre"** (*Wakamol Bug*): você altera a base do Gemini e descobre que a integração do Instagram que acabou de ser estabilizada parou de funcionar. 
*   **O Erro de Momentum:** Por ter acabado de estabilizar o scraper, o desenvolvedor tende a se empolgar e iniciar a refatoração do Gemini no mesmo chat ou branch, misturando históricos. 
*   **Contaminação de Contexto (*Context Window Bloat*):** Ao manter a lógica do scraper e a refatoração do SDK na mesma sessão de chat, a janela de contexto da IA fica sobrecarregada com tokens inúteis do scraper. A IA perde a capacidade de raciocínio de curto prazo e começa a duplicar códigos ou criar lógicas confusas.

---

### 2. Camadas de Integração e Acoplamentos Invisíveis (`app.py`)
O instanciamento direto do `RealGeminiClient` dentro do arquivo global `app.py` é uma violação grave do princípio de **Separation of Concerns (Separação de Responsabilidades)**. 
*   **O Acoplamento Oculto:** Se o seu frontend ou orquestrador global (`app.py`) conhece e instancia diretamente o cliente de produção da API, você perde o isolamento de rede. Em caso de queda ou indisponibilidade da API do Gemini, o fluxo do `app.py` travará por completo, arrastando o scraper do Instagram junto.
*   **Arquitetura Baseada em Features (*Feature-Based Folders*):** As lógicas do Gemini e do Instagram devem ser isoladas em pastas de funcionalidades totalmente independentes (ex: `/features/gemini-client` e `/features/instagram-scraper`). Nenhuma View ou controlador global deve instanciar o cliente diretamente; eles devem consumir interfaces abstratas.
*   **Vazamento de Segredos de API:** Certifique-se de que a nova biblioteca `google.genai` leia as credenciais estritamente de variáveis de ambiente do backend (`.env` listado no `.gitignore`). Sob o pretexto de resolver o bug rapidamente, as LLMs frequentemente tentam chumbar (*hardcode*) chaves privadas diretamente no código do cliente, o que expõe o seu sistema a botes de varredura pública no GitHub.

---

### 3. Falsos Positivos na Suíte de Testes (145/145 Passando)
O fato de sua suíte de testes estar 100% verde é uma **falsa sensação de segurança** durante migrações de SDKs de IA pelas seguintes razões:
*   **Mocks de Assinatura Obsoleta:** Os seus testes provavelmente utilizam mocks ou dublês de testes baseados no SDK antigo (`google.generativeai`). Como a estrutura de chamadas e retornos mudou na nova API (`google.genai`), os testes continuam passando porque estão validando o comportamento simulado do código antigo, enquanto o código real de produção falhará ao rodar a chamada real.
*   **Comportamento Não Determinístico:** Diferente de softwares tradicionais, as integrações de IA falham em silêncio. A chamada à API do Gemini pode retornar um erro HTTP ou uma resposta mal formatada que os seus mocks não previram, fazendo a aplicação quebrar na produção mesmo com os testes locais passando.
*   **Loop de Autovalidação Binário:** É preciso criar testes de integração reais (ou mocks extremamente fiéis baseados em schemas JSON estritos) que rodem de forma binária. A IA deve ser instruída a rodar os testes e se retroalimentar com as saídas físicas de erro do terminal até que o código se ajuste de forma idempotente, sem que o humano precise validar visualmente cada chamada de rede.

---

### 4. Guia de Ação Tática para a Refatoração Seguro

Para executar essa migração profunda mantendo a resiliência e a fluidez do desenvolvimento, siga o protocolo de engenharia de contexto:

1.  **Limpeza e Higiene de Contexto:** Antes de tocar em um único arquivo do Gemini, dê o comando `/clear` no terminal do Claude Code para esvaziar a memória de curto prazo e eliminar o "lixo" acumulado da estabilização do scraper do Instagram.
2.  **Pesquisa com MCP de Documentação Atualizada:** Visto que os modelos de IA possuem bases de dados de treinamento que podem estar congeladas no passado, o Claude não saberá usar a sintaxe correta do novo SDK de 2026 de forma nativa. Ative e force o uso do MCP **Context 7** para buscar a documentação oficial e atualizada da API `google.genai`. Isso garante que a IA implemente o código correto de primeira (*one-shot*), evitando o desperdício de tokens com tentativas e erros.
3.  **Handoff e Divulgação Progressiva (*Progressive Disclosure*):** Atualize o seu arquivo `CLAUDE.md` (ou `agents.md`) com as novas diretrizes da arquitetura. Utilize as **Skills** como manuais de instruções sob demanda. O arquivo de inicialização do Claude deve conter apenas o índice das regras, de modo que ele só consuma os tokens pesados do Redbook quando for editar ativamente a camada do Gemini.
4.  **Auditoria via Advisor Mode:** Utilize um modelo de alto raciocínio (como o Opus) rodando em uma sessão de chat paralela para atuar no **Advisor Mode**. Peça para o modelo revisor analisar a Pull Request da refatoração e mapear possíveis brechas de segurança ou vazamentos de contexto que o modelo executor (Sonnet) possa ter deixado passar no `app.py`.