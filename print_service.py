import os
import tempfile
import time
import traceback
import win32api
import win32print
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from functools import wraps


load_dotenv() 
SECRET_API_KEY = os.environ.get("PRINT_SERVICE_API_KEY")
PORTA_SERVICO = int(os.environ.get("PORTA_SERVICO", 5001))

if not SECRET_API_KEY:
    raise ValueError("ERRO CRÍTICO: 'PRINT_SERVICE_API_KEY' não foi definida no arquivo .env!")

app = Flask(__name__)

# --- 1. DECORADOR DE AUTENTICAÇÃO (NOVO) ---
def require_api_key(f):
    """
    Um decorador para proteger os endpoints com a chave de API.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != SECRET_API_KEY:
            print(f"!!! Tentativa de acesso falhou! Chave recebida: {api_key}")
            return jsonify({"erro": "Chave de API inválida"}), 401
        return f(*args, **kwargs)
    return decorated_function

# --- 2. FUNÇÃO HELPER DE LISTAR IMPRESSORAS (NOVO) ---
def get_installed_printers():
    """
    Busca todas as impressoras instaladas (locais e de rede) 
    e retorna uma lista de dicionários.
    """
    printers = []
    try:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers_info = win32print.EnumPrinters(flags, None, 2)
        
        for p in printers_info:
            printers.append({
                "nome": p.get('pPrinterName'),
                "porta": p.get('pPortName'),
                "driver": p.get('pDriverName'),
                "localizacao": p.get('pLocation'),
                "comentario": p.get('pComment'),
            })
    except Exception as e:
        print(f"!!! Erro ao enumerar impressoras: {e}")
        traceback.print_exc()
        raise # Levanta o erro para que o endpoint possa tratá-lo
        
    return printers

# --- 3. FUNÇÃO DE IMPRESSÃO (MODIFICADA) ---
def imprimir_pdf_na_impressora_especifica(caminho_do_pdf, nome_da_impressora):
    """
    Envia um PDF para uma impressora específica pelo nome.
    """
    
    # Validação: Verifica se a impressora existe
    try:
        nomes_impressoras = [p['nome'] for p in get_installed_printers()]
        if nome_da_impressora not in nomes_impressoras:
            msg_erro = f"Impressora desconhecida: '{nome_da_impressora}'. Impressoras disponíveis: {', '.join(nomes_impressoras)}"
            print(f"!!! Erro: {msg_erro}")
            return (False, msg_erro)
    except Exception as e:
        traceback.print_exc()
        return (False, f"Erro ao validar lista de impressoras: {e}")

    if not os.path.exists(caminho_do_pdf):
        return (False, f"Arquivo PDF não encontrado em: {caminho_do_pdf}")

    try:
        # Usa o nome da impressora recebido
        ret = win32api.ShellExecute(
            0,
            "printto",
            caminho_do_pdf,
            f'"{nome_da_impressora}"', # Alvo da impressão
            ".",
            0
        )
        if ret > 32:
            time.sleep(5) 
            return (True, f"Documento enviado para a impressora '{nome_da_impressora}'.")
        else:
            return (False, f"Falha ao enviar para ShellExecute. Código: {ret}")
    except Exception as e:
        traceback.print_exc()
        return (False, f"Erro na chamada da API de impressão do Windows: {e}")


# --- 4. ENDPOINT DE TESTE (NOVO) ---
@app.route('/api/test', methods=['GET'])
@require_api_key
def test_connection():
    """
    Endpoint simples para o Django testar a conexão e a chave API.
    """
    print("Sucesso: Conexão de teste recebida.")
    return jsonify({"status": "sucesso", "mensagem": "Conexão com o Serviço de Impressão bem-sucedida."})

# --- 5. ENDPOINT DE LISTAR IMPRESSORAS (NOVO) ---
@app.route('/api/printers', methods=['GET'])
@require_api_key
def list_printers():
    """
    Retorna uma lista JSON de todas as impressoras instaladas.
    """
    try:
        impressoras = get_installed_printers()
        print(f"Sucesso: {len(impressoras)} impressoras encontradas e listadas.")
        return jsonify({"status": "sucesso", "impressoras": impressoras})
    except Exception as e:
        print(f"!!! Erro ao listar impressoras: {e}")
        traceback.print_exc()
        return jsonify({"status": "erro", "mensagem": f"Erro ao listar impressoras: {e}"}), 500

# --- 6. ENDPOINT DE IMPRESSÃO (MODIFICADO) ---
@app.route('/api/print', methods=['POST'])
@require_api_key
def handle_print_request():
    """
    Recebe um PDF e um nome de impressora, salva o PDF 
    temporariamente e o envia para a impressora especificada.
    """
    
    # Validação do Arquivo PDF
    if 'pdf_file' not in request.files:
        print("!!! Erro: Request recebido sem 'pdf_file'.")
        return jsonify({"erro": "Nenhum arquivo 'pdf_file' encontrado no request"}), 400
    
    file = request.files['pdf_file']
    
    # Validação do Nome da Impressora
    # (Enviado como 'data' junto com 'files')
    nome_impressora = request.form.get('printer_name')
    if not nome_impressora:
        print("!!! Erro: Request recebido sem 'printer_name'.")
        return jsonify({"erro": "'printer_name' não fornecido no formulário"}), 400

    if file and file.mimetype == 'application/pdf':
        arquivo_temporario_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                file.save(tmp.name)
                arquivo_temporario_path = tmp.name
            
            print(f"Arquivo PDF recebido. Enviando para impressora: '{nome_impressora}'...")

            # Envia para a impressora específica
            sucesso, mensagem = imprimir_pdf_na_impressora_especifica(arquivo_temporario_path, nome_impressora)
            
            if sucesso:
                print(f"Sucesso: {mensagem}")
                return jsonify({"status": "sucesso", "mensagem": mensagem}), 200
            else:
                print(f"Erro: {mensagem}")
                return jsonify({"status": "erro", "mensagem": mensagem}), 500
                
        except Exception as e:
            print(f"!!! Erro crítico no processamento: {e}")
            traceback.print_exc()
            return jsonify({"status": "erro", "mensagem": f"Erro interno: {e}"}), 500
        finally:
            if arquivo_temporario_path and os.path.exists(arquivo_temporario_path):
                os.unlink(arquivo_temporario_path)
                print(f"Arquivo temporário removido.")
    else:
        return jsonify({"erro": "Tipo de arquivo inválido. Apenas PDF é aceito."}), 400

# --- Ponto de Partida (Sem mudança) ---
if __name__ == '__main__':
    print(f"Iniciando Servidor de Impressão v2.0 na porta {PORTA_SERVICO}...")
    print(f"Chave API carregada: {SECRET_API_KEY[:4]}...{SECRET_API_KEY[-4:]}")
    print("Endpoints disponíveis: GET /api/test, GET /api/printers, POST /api/print")
    print("Escutando em todas as interfaces (0.0.0.0)")
    app.run(host='0.0.0.0', port=PORTA_SERVICO, debug=True)
