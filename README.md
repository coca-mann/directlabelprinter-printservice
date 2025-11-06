# Servidor de Impressão Django-Windows (Print Service)

Este é um microserviço Python (Flask) projetado para atuar como uma ponte segura entre um aplicativo web (como um servidor Django) e uma impressora local instalada em uma máquina Windows.

## O Problema que Resolve

Servidores web modernos (Django, etc.) rodam em ambientes isolados (Linux, Docker, Nuvem), mas impressoras de etiquetas (como Zebras) estão conectadas a máquinas Windows locais. Este serviço recebe um trabalho de impressão (um arquivo PDF) do servidor Django pela rede e o encaminha para a impressora padrão do Windows usando a API nativa `pywin32`.

## Funcionalidades

* **API Segura:** O endpoint (`/api/print`) é protegido por uma chave de API secreta (via cabeçalho `X-API-Key`).
* **Desacoplado:** Permite que seu servidor Django principal rode em qualquer lugar (Linux, Nuvem, etc.), eliminando a dependência do `win32api` no seu projeto principal.
* **Seguro para GitHub:** A chave de API secreta é carregada de um arquivo `.env` local e **não** é armazenada no código-fonte. O `.gitignore` garante que este arquivo nunca seja enviado ao repositório.
* **Impressão Nativa:** Usa `win32api.ShellExecute` para impressão direta, o que é ideal para drivers de impressora especializados.
* **Serviço Windows:** Projetado para ser instalado como um serviço Windows robusto usando `NSSM`, iniciando automaticamente com o computador.

## Diagrama da Arquitetura

`[Servidor Django]` --(API Request)--> `[Rede Local (Firewall)]` --> `[Máquina Windows: Print Service (Flask)]` --(`win32api`)--> `[Impressora Específica]`

---

## Endpoints da API

Todos os endpoints exigem um cabeçalho `X-API-Key` com a chave secreta.

### 1. Testar Conexão

* **Endpoint:** `GET /api/test`
* **Função:** Verifica se o serviço está online e se a chave API é válida.
* **Resposta de Sucesso (200):**
  ```json
  {
    "status": "sucesso",
    "mensagem": "Conexão com o Serviço de Impressão bem-sucedida."
  }
  ```

### 2. Listar Impressoras
* **Endpoint:** `GET /api/printers`
* **Função:** Retorna uma lista de todas as impressoras instaladas no Windows.
* **Resposta de Sucesso (200):**
  ```json
  {
    "status": "sucesso",
    "impressoras": [
        {
        "nome": "Zebra ZD420",
        "porta": "USB001",
        "driver": "ZDesigner ZD420-203dpi ZPL",
        "localizacao": "Mesa da TI",
        "comentario": "Impressora de etiquetas"
        },
        {
        "nome": "HP LaserJet Pro MFP M227fdw",
        "porta": "WSD-12345-...",
        "driver": "HP Universal Print Driver",
        "localizacao": "Escritório",
        "comentario": ""
        }
    ]
  }
  ```

### 3. Enviar Impressão
* **Endpoint:** POST /api/print
* **Função:** Recebe um PDF e o nome de uma impressora, e envia o trabalho.
* **Formato:** multipart/form-data
* **Campos:**
    1. **pdf_file:** O arquivo PDF (ex: etiqueta.pdf).
    2. **printer_name:** O nome exato da impressora (obtido de /api/printers).
* **Resposta de Sucesso (200):**
    ```json
    {
    "status": "sucesso",
    "mensagem": "Documento enviado para a impressora 'Zebra ZD420'."
    }
    ```
* **Resposta de Erro (400/500):**
    ```json	
    {
        "status": "erro",
        "mensagem": "Impressora desconhecida: 'Zebra_Errada'. Impressoras disponíveis: Zebra ZD420, HP LaserJet..."
    }
    ```
---

## Instalação (Máquina Windows da Impressora)

Siga estes passos na máquina Windows que está fisicamente conectada à impressora (ou que a tenha instalada na rede).

### Pré-requisitos

1.  **Python 3.x:** [Download do Python](https://www.python.org/downloads/).
    * *Importante: Durante a instalação, marque a caixa "Add Python to PATH".*
2.  **NSSM (Non-Sucking Service Manager):**
    * Usado para rodar o script como um serviço.
    * [Download do NSSM](https://nssm.cc/download) (baixe o `nssm.zip`).
    * Extraia o `nssm.exe` (da pasta `win64` ou `win32`) para uma pasta permanente (ex: `C:\NSSM\`).

### Passo 1: Obter os Arquivos do Serviço

1.  Crie uma pasta permanente para o serviço (ex: `C:\print_service`).
2.  Clone ou baixe e coloque os arquivos deste projeto (`print_service.py`, `requirements.txt`, `run.bat`, `.gitignore`) dentro de `C:\print_service`.

### Passo 2: Configurar o Ambiente Python

1.  Abra o **Prompt de Comando (cmd)** como **Administrador**.
2.  Navegue até a pasta do serviço:
    ```bash
    cd C:\print_service
    ```
3.  Crie um ambiente virtual para isolar as dependências:
    ```bash
    python -m venv venv
    ```
4.  Ative o ambiente virtual:
    ```bash
    call .\venv\Scripts\activate.bat
    ```
5.  Instale as bibliotecas necessárias:
    ```bash
    pip install -r requirements.txt
    ```

### Passo 3: Configurar a Chave de API (Segurança)

Esta é a etapa mais importante para a segurança.

1.  Dentro de `C:\print_service`, crie um novo arquivo chamado `.env` (começando com um ponto).
2.  Abra `C:\print_service\.env` no Bloco de Notas e cole o seguinte conteúdo:

    ```ini
    # Chave secreta para autenticar o Django. 
    # Mude para uma string longa, aleatória e segura.
    PRINT_SERVICE_API_KEY="sua-chave-secreta-muito-longa-e-aleatoria-12345"

    # Porta que o serviço vai escutar
    PORTA_SERVICO=5001
    ```

3.  Salve o arquivo. O `.gitignore` incluído neste projeto já impede que este arquivo seja enviado ao GitHub.

### Passo 4: Testar o Serviço Manualmente

Antes de instalar como um serviço, teste-o diretamente no terminal para ver se há erros:

1.  No mesmo prompt (Admin) com o `venv` ativado:
    ```bash
    python print_service.py
    ```
2.  Você deve ver uma saída indicando que o servidor está rodando:
    ```
    Iniciando Servidor de Impressão na porta 5001...
    Escutando em todas as interfaces (0.0.0.0)
     * Running on all addresses (0.0.0.0)
     * Running on [http://127.0.0.1:5001](http://127.0.0.1:5001)
     * Running on http://[SEU_IP_DE_REDE]:5001
    ```
3.  **Importante:** Anote o `[SEU_IP_DE_REDE]` (ex: `192.168.1.50`). Este é o IP que você deve colocar no `settings.py` do seu projeto Django.
4.  Tente enviar uma impressão do seu app Django agora. Verifique o console do serviço para ver os logs ("Arquivo PDF recebido...").
5.  Quando o teste funcionar, pare o servidor manual (pressione **Ctrl+C**).
6.  Digite `deactivate` para sair do ambiente virtual por enquanto.

### Passo 5: Instalar como Serviço Windows (com NSSM)

Isto fará com que o serviço inicie automaticamente com o Windows.

1.  No seu **Prompt de Comando de Administrador**, navegue até a pasta onde você colocou o `nssm.exe`:
    ```bash
    cd C:\NSSM
    ```
2.  Instale o serviço (você pode escolher o nome que quiser, ex: `PrintServiceDjango`):
    ```bash
    nssm install PrintServiceDjango
    ```
3.  Uma GUI do NSSM pode aparecer. Se aparecer, use-a. Se não, use estes comandos para configurar o serviço:

    ```bash
    REM 3a. Define o programa a ser executado (nosso script .bat)
    nssm set PrintServiceDjango Application "C:\print_service\run.bat"

    REM 3b. Define o diretório de onde ele deve rodar
    nssm set PrintServiceDjango AppDirectory "C:\print_service"

    REM 3c. (Opcional, mas recomendado) Configura arquivos de log
    nssm set PrintServiceDjango AppStdout "C:\print_service\log.txt"
    nssm set PrintServiceDjango AppStderr "C:\print_service\error.txt"
    ```

4.  Inicie o serviço:
    ```bash
    nssm start PrintServiceDjango
    ```

O serviço agora está rodando em segundo plano e será reiniciado automaticamente.

---

## Gerenciamento do Serviço

Use estes comandos no CMD (Admin) para gerenciar o serviço:

* **Iniciar:** `nssm start PrintServiceDjango`
* **Parar:** `nssm stop PrintServiceDjango`
* **Reiniciar:** `nssm restart PrintServiceDjango`
* **Ver Status:** `nssm status PrintServiceDjango`
* **Remover:** `nssm remove PrintServiceDjango` (pare o serviço antes)

## Configuração do Lado do Django (Lembrete)

No seu projeto Django principal (que está na nuvem ou em outro servidor), você precisa configurar:

1.  **`settings.py`:**
    ```python
    PRINT_SERVICE_URL = "http://[IP_DA_MAQUINA_WINDOWS]:5001/api/print"
    PRINT_SERVICE_KEY = "sua-chave-secreta-muito-longa-e-aleatoria-12345" # (Deve ser a mesma do .env)
    ```
2.  **Firewall do Windows:**
    * Certifique-se de que a máquina Windows tenha uma regra de firewall **liberando a entrada** na porta `5001` (ou a porta que você definiu) para que o servidor Django possa se conectar a ela.

## Depuração (Logs)

Se a impressão falhar, os primeiros lugares para verificar são os arquivos de log na máquina da impressora:
* `C:\print_service\log.txt` (Para saídas normais, como "Arquivo PDF recebido...")
* `C:\print_service\error.txt` (Para erros críticos do Python que fizeram o serviço falhar)