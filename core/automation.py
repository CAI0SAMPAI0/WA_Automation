import os
import time
import traceback
import sys
import undetected_chromedriver as uc
import json
import shutil
import tempfile
import uuid
import random
import subprocess
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Delays (ajustáveis)
WHATSAPP_LOAD = 10
SHORT_DELAY = 1.0
MID_DELAY = 1.6
LONG_DELAY = 2.0

# --- FUNÇÃO PARA AGENDAMENTO ---
def run_auto(json_path):
    """ Função chamada pelo app.py quando o Windows dispara o agendamento. Lê o arquivo JSON e executa a automação. """
    print(f"Iniciando automação agendada: {json_path}")
    
    if not os.path.exists(json_path):
        print(f"Erro: Arquivo {json_path} não encontrado.")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Extrai os dados do JSON gerado pela sua interface
        target = dados.get("target")
        mode = dados.get("mode")
        message = dados.get("message")
        file_path = dados.get("file_path")

        # Chama a função mestre j
        executar_envio(
            userdir=None, # O iniciar_driver achará o perfil
            target=target,
            mode=mode,
            message=message,
            file_path=file_path,
            logger=lambda m: print(f"[AUTO-LOG] {m}"),
            headless=True
        )
        print("✓ Automação agendada concluída com sucesso.")
        
    except Exception as e:
        print(f"❌ Erro na execução automática: {e}")
        traceback.print_exc()
        sys.exit(1)
# --------------------------
# Utilitários internos
# --------------------------
def _log(logger, msg):
    """Log centralizado: usa callable logger se fornecido"""
    if logger:
        try:
            logger(msg)
        except Exception:
            pass
    else:
        print(msg)

def criar_perfil_temporario(base_profile_dir, logger=None):
    try:
        temp_dir = os.path.join(tempfile.gettempdir(), f"whatsapp_bot_profile_{uuid.uuid4().hex[:8]}")
        _log(logger, f"Clonando perfil para uso paralelo: {temp_dir}")
        
        # Função interna para ignorar erros de arquivos travados (Cookies/Sessão)
        def copy_with_ignore(src, dst):
            try:
                shutil.copy2(src, dst)
            except Exception:
                # Se o arquivo estiver travado (WinError 32), apenas ignora ele
                pass

        # Cria a árvore de diretórios manualmente ou usa copytree com ignore
        shutil.copytree(base_profile_dir, temp_dir, dirs_exist_ok=True, copy_function=copy_with_ignore)
        
        return temp_dir
    except Exception as e:
        _log(logger, f"Erro crítico ao clonar: {e}. Tentando seguir com original.")
        return base_profile_dir

def _wait(driver, by, selector, timeout=10):
    """Espera por presença de elemento e retorna WebElement ou None."""
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
    except Exception:
        return None

def _wait_clickable(driver, by, selector, timeout=10):
    """Espera por elemento clicável."""
    try:
        return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))
    except Exception:
        return None

def _find(driver, candidates):
    """
    Recebe lista de tuplas (By, selector) e retorna o primeiro WebElement encontrado.
    candidates: [(By.XPATH, '...'), (By.CSS_SELECTOR, '...'), ...]
    """
    for by, sel in candidates:
        try:
            el = _wait(driver, by, sel, timeout=6)
            if el:
                return el, (by, sel)
        except Exception:
            continue
    return None, None

# --------------------------
# Headless a partir da 3ª execução
# --------------------------

def contador_execucao(incrementar=True):
    import sys
    import os

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    count_file = os.path.join(base_dir, "execution_count.txt")
    
    count = 0
    # Tenta ler o valor atual
    if os.path.exists(count_file):
        try:
            with open(count_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                count = int(content) if content else 0
        except Exception as e:
            print(f"Erro ao ler arquivo de contagem: {e}")
            count = 0

    # Se for para incrementar, realiza a gravação "forçada" no disco
    if incrementar:
        count += 1
        try:
            # 'w' sobrescreve o arquivo com o novo número
            with open(count_file, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(str(count))
                f.flush()
                os.fsync(f.fileno()) 
        except Exception as e:
            print(f"Erro ao gravar contador: {e}")
            
    return count

# --------------------------
# Driver
# --------------------------
'''def iniciar_driver(userdir=None, headless=False, timeout=60, logger=None):
    """
    Inicia undetected_chromedriver com perfil persistente.
    """
    try:
        # CORREÇÃO CRÍTICA: Se userdir é None, usa o perfil da pasta do executável
        if userdir is None:
            # Determina o diretório base corretamente
            if getattr(sys, 'frozen', False):
                # Modo executável (.exe)
                base_dir = os.path.dirname(sys.executable)
            else:
                # Modo desenvolvimento (.py)
                base_dir = os.path.dirname(os.path.abspath(__file__))
                base_dir = os.path.join(base_dir, "..")
            
            userdir = os.path.join(base_dir, "perfil_bot_whatsapp")
        
        # Garante que o diretório existe
        if not os.path.exists(userdir):
            os.makedirs(userdir)
            if logger:
                logger(f"Criado novo perfil Chrome em: {userdir}")
        
        if logger:
            logger(f"Iniciando Chrome com profile: {userdir}")
            
            # Verifica se o perfil já foi autenticado
            local_state = os.path.join(userdir, "Local State")
            if os.path.exists(local_state):
                logger("✓ Perfil Chrome encontrado (pode estar autenticado)")
            else:
                logger("⚠️  Perfil Chrome novo/não autenticado")

        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={userdir}")

        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        
        # Importante para evitar problemas de permissão
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")

        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(timeout)
        
        # Maximiza a janela (importante para elementos aparecerem)
        if not headless:
            driver.maximize_window()

        if logger:
            logger("Chrome iniciado. Acessando WhatsApp Web...")
        
        driver.get("https://web.whatsapp.com")
        
        # Tempo de espera maior para modo automático
        wait_time = 10  # 10 segundos para carregar
        if logger:
            logger(f"Aguardando {wait_time} segundos para carregar WhatsApp...")
        
        time.sleep(wait_time)

        # Verificação simples se está autenticado
        try:
            # Tenta encontrar qualquer elemento que indique que está logado
            driver.find_element(By.XPATH, "//div[@role='textbox']")
            if logger:
                logger("✓ WhatsApp Web parece estar autenticado")
        except:
            if logger:
                logger("⚠️  WhatsApp Web não parece autenticado")
                logger("   Talvez precise escanear QR Code novamente")
            # Não falha imediatamente - continua e vê o que acontece

        if logger:
            logger("WhatsApp Web carregado (ou pronto para autenticação).")
        
        return driver
        
    except Exception as e:
        if logger:
            logger(f"❌ ERRO ao iniciar Chrome: {e}")
            import traceback
            logger(traceback.format_exc())
        raise'''

def iniciar_driver(userdir=None, headless=True, timeout=60, logger=None):
    """
    Inicia o undetected_chromedriver com configurações reforçadas para modo Headless.
    """
    import os, sys, time, random, subprocess
    import undetected_chromedriver as uc
    driver = None
    debug_port = 'padrão'

    try:
        # Configuração do diretório do perfil
        if userdir is None:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                base_dir = os.path.join(base_dir, "..")
            userdir = os.path.join(base_dir, "perfil_bot_whatsapp")
        
        if not os.path.exists(userdir):
            os.makedirs(userdir)

        # 3. Opções do Chrome
        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={userdir}")
        
        # Ignora erros de certificado e automação
        options.add_argument("--start-maximized")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--no-first-run')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-session-crashed-bubble")

        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            
            # Porta de debug aleatória evita o erro "cannot connect to chrome"
            debug_port = random.randint(9000, 9999)
            options.add_argument(f'--remote-debugging-port={debug_port}')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Define um tamanho de janela real para que os elementos apareçam no DOM
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')

        # 4. Inicialização do Driver
        if logger: logger(f"Iniciando Chrome (Headless={headless}) na porta {debug_port if headless else 'padrão'}...")
        
        driver = uc.Chrome(
            options=options,
            use_subprocess=True,
            version_main=None
        )
    
        if headless:
            driver.set_window_size(1920, 1080)
        else:
            driver.maximize_window()
            # Pequeno truque: se o maximize falhar, forçamos o tamanho
            driver.set_window_rect(0, 0, 1920, 1080) 

        driver.set_page_load_timeout(timeout)

        # 5. Acesso ao WhatsApp
        if logger: logger("Acessando WhatsApp Web...")
        driver.get("https://web.whatsapp.com")
        
        # Headless precisa de um tempo maior para o primeiro carregamento de scripts pesados
        tempo_espera = 25 if headless else 15
        if logger: logger(f"Aguardando {tempo_espera}s para sincronização de mensagens...")
        time.sleep(tempo_espera)

        return driver

    except Exception as e:
        if logger: logger(f"❌ ERRO CRÍTICO no iniciar_driver: {str(e)}")
        # Em caso de erro, tenta garantir que o processo não fique preso
        if driver is not None:
            try: 
                driver.quit()
            except: 
                pass
        raise

# --------------------------
# Buscar contato / abrir chat
# --------------------------
def procurar_contato_grupo(driver, target, logger=None, timeout=2):
    """
    Busca e abre a conversa com o contato/grupo pelo nome exato.
    Tenta vários seletores da caixa de busca; se falhar tenta clicar primeiro chat.
    """
    try:
        _log(logger, f"Procurando contato/grupo: {target}")

        search_candidates = [
            (By.XPATH, "//div[@contenteditable='true' and (@data-tab='3' or @data-tab='1')]"),
            (By.XPATH, "//div[contains(@aria-label,'Pesquisar') or contains(@aria-label,'Pesquisar ou começar')]"),
            (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"),
        ]

        search_box, sel = _find(driver, search_candidates)
        if not search_box:
            _log(logger, "Campo de busca não encontrado via seletores comuns. Tentando abrir primeiro chat como fallback...")
            # fallback: abrir primeiro chat da lista
            first_chat = _wait_clickable(driver, By.CSS_SELECTOR, "div[role='listitem']", timeout=2)
            if first_chat:
                try:
                    first_chat.click()
                    _log(logger, "Primeiro chat aberto como fallback (não pesquisado).")
                    return True
                except Exception:
                    pass
            raise Exception("Caixa de pesquisa não encontrada (XPaths testados).")

        # focar, limpar e digitar
        try:
            search_box.click()
        except Exception:
            driver.execute_script("arguments[0].focus();", search_box)
        time.sleep(0.2)
        try:
            # limpar (Ctrl+A + Del)
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
        except Exception:
            # fallback: executar script para limpar
            driver.execute_script("arguments[0].innerText = '';", search_box)
        time.sleep(0.2)
        search_box.send_keys(target)
        time.sleep(SHORT_DELAY)
        search_box.send_keys(Keys.ENTER)
        time.sleep(MID_DELAY)

        _log(logger, "Contato/grupo aberto.")
        return True
    except Exception as e:
        _log(logger, f"Erro procurar_contato_grupo: {str(e)}")
        _log(logger, traceback.format_exc())
        raise

# --------------------------
# Mensagem de texto
# --------------------------
def enviar_mensagem_simples(driver, message, logger=None, timeout=4):
    """
    Envia apenas mensagem de texto no chat já aberto.
    """
    try:
        _log(logger, "Enviando mensagem de texto...")
        msg_candidates = [
            (By.XPATH, "//div[@role='textbox' and @contenteditable='true' and @aria-label='Digite uma mensagem']"),
            (By.XPATH, "//div[@contenteditable='true' and (@data-tab='10' or @data-tab='6')]"),
            (By.CSS_SELECTOR, "footer div[contenteditable='true']"),
        ]
        msg_box, sel = _find(driver, msg_candidates)
        if not msg_box:
            raise Exception("Campo de mensagem não encontrado.")

        try:
            msg_box.click()
        except Exception:
            driver.execute_script("arguments[0].focus();", msg_box)
        time.sleep(0.2)
        msg_box.send_keys(message)
        time.sleep(0.3)

        # tentar clicar no botão de enviar (setinha) primeiro; se não, enviar Enter
        send_btn = _wait(driver, By.XPATH, "//span[@data-icon='wds-ic-send-filled']", timeout=2)
        if not send_btn:
            send_btn = _wait(driver, By.CSS_SELECTOR, "span[data-icon='send']", timeout=2)
        if not send_btn:
            logger_msg = "Botão de enviar não encontrado; enviando com Enter."
            _log(logger, logger_msg)
            raise Exception(logger_msg)
            try:
                send_btn.click()
            except Exception as e:
                msg_box.send_keys(Keys.ENTER)
        else:
            msg_box.send_keys(Keys.ENTER)

        time.sleep(SHORT_DELAY)
        _log(logger, "Mensagem enviada.")
        return True
    except Exception as e:
        _log(logger, f"Erro enviar_mensagem_simples: {str(e)}")
        _log(logger, traceback.format_exc())
        raise

# --------------------------
# Funções de anexos / upload
# --------------------------
def clicar_clip(driver, logger=None):
    """
    Clica no botão de anexar (clip). Usa seletor baseado em data-icon ou fallback por role.
    """
    candidates = [
        (By.XPATH, "//span[@data-icon='plus-rounded']"),
        (By.CSS_SELECTOR, "button[aria-label='Anexar']"),
        (By.CSS_SELECTOR, "span[data-icon='plus-rounded']"),
        (By.CSS_SELECTOR, "div[title='Anexar']"),
        (By.CSS_SELECTOR, "div[title='Anexar']")
    ]
    el, sel = _find(driver, candidates)
    if not el:
        raise Exception("Botão de anexar (clip) não encontrado.")
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)
    time.sleep(0.6)
    _log(None, f"clicar_clip: clique realizado ({sel}).")
    return True

def clicar_botao_documento(driver, logger=None):
    """
    Clica na opção 'Documento' dentro do painel de anexos.
    Usa o texto visível 'Documento' como referência (mais estável).
    """
    # tenta localizar span com texto "Documento" e subir para o pai clicável
    try:
        el = _wait(driver, By.XPATH, "//span[normalize-space()='Documento']/parent::div", timeout=3)
        if not el:
            # fallback: localizar elemento pelo title/text parcial
            el = _wait(driver, By.XPATH, "//*[normalize-space()='Documento']", timeout=2)
            if el:
                el = el.find_element(By.XPATH, "./ancestor::div[1]")
        if not el:
            raise Exception("Botão 'Documento' não encontrado no painel de anexos.")
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)
        time.sleep(0.5)
        _log(logger, "Opção 'Documento' clicada.")
        return True
    except Exception as e:
        _log(logger, f"Erro clicar_botao_documento: {e}")
        raise

def localizar_input_file(driver, logger=None, timeout=2.5):
    """
    Retorna o input[type='file'] mais provável (último no DOM), que é o que o WhatsApp usa.
    """
    try:
        # procura por inputs do tipo file e retorna o último
        els = driver.find_elements(By.XPATH, "//input[@type='file']")
        if not els:
            # fallback por css
            els = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if not els:
            return None
        # escolher o último criado
        input_file = els[-1]
        return input_file
    except Exception as e:
        _log(logger, f"Erro localizar_input_file: {e}")
        return None

def upload_arquivo(driver, file_path, logger=None, timeout=6.3):
    """
    Envia caminho ao input[type=file].
    """
    try:
        input_file = localizar_input_file(driver, logger=logger, timeout=timeout)
        if not input_file:
            raise Exception("input[type='file'] não encontrado (após abrir painel).")
        # send_keys com caminho absoluto
        input_file.send_keys(file_path)
        time.sleep(1.2)  # dar tempo para o preview ser processado
        _log(logger, f"upload_arquivo: arquivo enviado ao input ({file_path}).")
        return True
    except Exception as e:
        _log(logger, f"Erro upload_arquivo: {e}")
        _log(logger, traceback.format_exc())
        raise

def clicar_enviar_arquivo(driver, logger=None, timeout=6.7):
    """
    Clica no botão verde de enviar arquivo (preview).
    """
    try:
        # Tentativa direta: botão com aria-label="Enviar"
        send_btn = _wait(driver, By.XPATH, "//div[@role='button' and @aria-label='Enviar']", timeout=2)
        if not send_btn:
            # fallback: span com ícone de send dentro do preview
            send_btn = _wait(driver, By.XPATH, "//span[@data-icon='wds-ic-send-filled' or @data-icon='send']", timeout=2)
        if not send_btn:
            # fallback: botão verde genérico
            send_btn = _wait(driver, By.CSS_SELECTOR, "button[aria-label='Enviar']", timeout=2)
        if not send_btn:
            raise Exception("Botão para confirmar envio do arquivo não encontrado.")
        try:
            send_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", send_btn)
        time.sleep(1.0)
        _log(logger, "clicar_enviar_arquivo: clique realizado.")
        return True
    except Exception as e:
        _log(logger, f"Erro clicar_enviar_arquivo: {e}")
        _log(logger, traceback.format_exc())
        raise

# --------------------------
# Funções de envio
# --------------------------

def enviar_arquivo(driver, file_path, message=None, headless=False, logger=None):
    """
    Envia apenas o arquivo (sem legenda).
    Ajustado para funcionar em modo visível (clicando) e Headless (direto).
    """
    try:
        _log(logger, f"Anexando arquivo: {file_path}")
        
        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            raise Exception(f"Arquivo não encontrado: {file_path}")
        
        _log(logger, f"Tamanho do arquivo: {os.path.getsize(file_path) / 1024:.2f} KB")
        
        # Localiza o input (funciona mesmo invisível)
        input_file = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        
        # Envia o caminho absoluto do arquivo
        abs_path = os.path.abspath(file_path)
        input_file.send_keys(abs_path)
        _log(logger, f"Arquivo enviado ao input: {abs_path}")
        
        # Aguarda o preview carregar - tempo maior para headless
        wait_time = 8 if headless else 4
        _log(logger, f"Aguardando {wait_time}s para preview carregar...")
        time.sleep(wait_time)
        
        # Verifica se o preview abriu (presença do botão de enviar)
        try:
            send_btn = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='button' and @aria-label='Enviar']"))
            )
            _log(logger, "✓ Preview do arquivo detectado")
        except:
            # Fallback: tenta outros seletores
            try:
                send_btn = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//span[@data-icon='send' or @data-icon='wds-ic-send-filled']"))
                )
                _log(logger, "✓ Preview do arquivo detectado (fallback)")
            except Exception as e:
                _log(logger, f"❌ Preview não detectado: {e}")
                raise Exception("Preview do arquivo não abriu - WhatsApp pode não ter processado o arquivo")
        
        # Aguarda o botão ficar clicável
        send_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send'] | //span[@data-icon='wds-ic-send-filled'] | //div[@role='button' and @aria-label='Enviar']"))
        )
        
        _log(logger, "Clicando no botão de enviar...")
        try:
            send_btn.click()
        except:
            # Se o clique normal falhar, usa JavaScript
            driver.execute_script("arguments[0].click();", send_btn)
        
        _log(logger, "✓ Clique no botão de enviar realizado")
        
        # CRUCIAL: Aguarda o arquivo realmente enviar
        # Estratégia 1: Aguarda o preview fechar (botão desaparecer)
        _log(logger, "Aguardando confirmação de envio (até 60s)...")
        preview_fechou = False
        try:
            WebDriverWait(driver, 60).until_not(
                EC.presence_of_element_located((By.XPATH, "//div[@role='button' and @aria-label='Enviar']"))
            )
            preview_fechou = True
            _log(logger, "✓ Preview fechado - arquivo enviado")
        except:
            _log(logger, "⚠️ Timeout aguardando preview fechar")
        
        # Estratégia 2: Verifica se voltou para a tela de chat normal
        if not preview_fechou:
            _log(logger, "Verificando se retornou à tela de chat...")
            try:
                chat_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='textbox' and @contenteditable='true']"))
                )
                _log(logger, "✓ Retornou à tela de chat - arquivo provavelmente enviado")
            except:
                _log(logger, "⚠️ Não foi possível confirmar o envio")
        
        # Tempo adicional de segurança
        time.sleep(5)
        _log(logger, "✓ Processo de envio de arquivo concluído")
        return True

    except Exception as e:
        _log(logger, f"❌ Erro enviar_arquivo: {e}")
        _log(logger, traceback.format_exc())
        raise

def enviar_arquivo_com_mensagem(driver, file_path, message, headless=False, logger=None):
    """
    Envia arquivo com legenda (mensagem).
    Funciona via injeção direta no input[type='file'], que é o método mais estável.
    """
    try:
        _log(logger, f"Anexando arquivo com legenda: {os.path.basename(file_path)}")
        
        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            raise Exception(f"Arquivo não encontrado: {file_path}")
        
        _log(logger, f"Tamanho do arquivo: {os.path.getsize(file_path) / 1024:.2f} KB")
        
        # 1. Localiza o input (funciona mesmo invisível)
        input_file = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        
        # Envia o caminho absoluto
        abs_path = os.path.abspath(file_path)
        input_file.send_keys(abs_path)
        _log(logger, f"Arquivo enviado ao input: {abs_path}")
        
        # 2. Aguarda o WhatsApp carregar o preview - tempo maior para headless
        wait_time = 8 if headless else 4
        _log(logger, f"Aguardando {wait_time}s para preview carregar...")
        time.sleep(wait_time)

        # 3. Verifica se o preview abriu
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='button' and @aria-label='Enviar']"))
            )
            _log(logger, "✓ Preview do arquivo detectado")
        except Exception as e:
            _log(logger, f"❌ Preview não detectado: {e}")
            raise Exception("Preview do arquivo não abriu")

        # 4. Localiza e preenche a legenda (se houver)
        if message:
            try:
                _log(logger, "Procurando campo de legenda...")
                # Tenta vários seletores para o campo de legenda
                caption_box = None
                selectors = [
                    "//div[@role='textbox' and @aria-label='Adicionar legenda']",
                    "//div[@role='textbox' and @contenteditable='true' and @data-tab='10']",
                    "//div[@contenteditable='true' and contains(@class, 'copyable-text')]"
                ]
                
                for selector in selectors:
                    try:
                        caption_box = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        if caption_box:
                            _log(logger, f"✓ Campo de legenda encontrado: {selector}")
                            break
                    except:
                        continue
                
                if caption_box:
                    # Tenta focar e inserir texto
                    try:
                        caption_box.click()
                    except:
                        driver.execute_script("arguments[0].focus();", caption_box)
                    
                    time.sleep(0.5)
                    caption_box.send_keys(message)
                    _log(logger, f"✓ Legenda inserida: {message[:50]}...")
                    time.sleep(1)
                else:
                    _log(logger, "⚠️ Campo de legenda não encontrado")
                    
            except Exception as e:
                _log(logger, f"⚠️ Erro ao inserir legenda: {e}")

        # 5. Localiza o botão de enviar do Preview
        _log(logger, "Procurando botão de enviar...")
        send_xpath = "//div[@role='button' and @aria-label='Enviar'] | //span[@data-icon='send'] | //span[@data-icon='wds-ic-send-filled']"
        send_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, send_xpath))
        )
        
        _log(logger, "Clicando no botão de enviar...")
        try:
            send_btn.click()
        except:
            driver.execute_script("arguments[0].click();", send_btn)
        
        _log(logger, "✓ Clique no botão de enviar realizado")
        
        # 6. CRUCIAL: Aguarda o arquivo realmente enviar
        _log(logger, "Aguardando confirmação de envio (até 60s)...")
        preview_fechou = False
        try:
            WebDriverWait(driver, 60).until_not(
                EC.presence_of_element_located((By.XPATH, "//div[@role='button' and @aria-label='Enviar']"))
            )
            preview_fechou = True
            _log(logger, "✓ Preview fechado - arquivo enviado")
        except:
            _log(logger, "⚠️ Timeout aguardando preview fechar")
        
        # Verifica se voltou para tela de chat
        if not preview_fechou:
            _log(logger, "Verificando se retornou à tela de chat...")
            try:
                chat_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='textbox' and @contenteditable='true']"))
                )
                _log(logger, "✓ Retornou à tela de chat - arquivo provavelmente enviado")
            except:
                _log(logger, "⚠️ Não foi possível confirmar o envio")
        
        # 7. Tempo adicional de segurança
        time.sleep(5)
        _log(logger, "✓ Processo de envio concluído")
        return True

    except Exception as e:
        _log(logger, f"❌ Erro enviar_arquivo_com_mensagem: {e}")
        _log(logger, traceback.format_exc())
        raise

def executar_envio(userdir, target, mode, message=None, file_path=None, logger=None, headless=True):
    """
    Função mestre: inicializa driver, procura contato e decide qual envio executar.
    mode: 'text', 'file', 'file_text'
    """
    driver = None
    perfil_final = None

    try:
        # Define o diretório base do perfil
        if userdir is None:
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            userdir = os.path.join(base_dir, "perfil_bot_whatsapp")

        # CRUCIAL: Cria a cópia para não conflitar com o seu Chrome aberto
        perfil_final = criar_perfil_temporario(userdir, logger)

        # Inicia o driver com a CÓPIA do perfil e o modo headless correto
        driver = iniciar_driver(userdir=perfil_final, headless=headless, logger=logger)
        
        # Log de execução
        vezes_executadas = contador_execucao(incrementar=False)
        if logger:
            logger(f'Execução número {vezes_executadas}')
            if headless:
                logger('Rodando em modo headless (segundo plano).')

        # Procura o contato/grupo
        procurar_contato_grupo(driver, target, logger=logger)
        time.sleep(2.0)  # Aumentado para garantir que o chat abriu

        # Executa o modo selecionado
        if mode == "text":
            if not message:
                raise Exception("Modo 'text' selecionado mas nenhuma mensagem fornecida.")
            enviar_mensagem_simples(driver, message, logger=logger)
            
        elif mode == "file":
            if not file_path:
                raise Exception("Modo 'file' selecionado mas nenhum arquivo fornecido.")
            enviar_arquivo(driver, file_path, message=None, headless=headless, logger=logger)
            
        elif mode == "file_text":
            if not file_path:
                raise Exception("Arquivo necessário para modo 'file_text'.")
            enviar_arquivo_com_mensagem(driver, file_path, message or "", headless=headless, logger=logger)
            
        else:
            raise Exception("Modo desconhecido.")
        
        # Tempo adicional após o envio bem-sucedido
        _log(logger, "Aguardando confirmação final...")
        time.sleep(8)
        
        _log(logger, "=" * 50)
        _log(logger, "✓✓✓ ENVIO CONCLUÍDO COM SUCESSO ✓✓✓")
        _log(logger, "=" * 50)
        
        return True
        
    except Exception as e:
        _log(logger, f"❌ Erro em executar_envio: {str(e)}")
        _log(logger, traceback.format_exc())
        raise
        
    finally:
        # Fecha o driver
        if driver:
            try:
                _log(logger, "Aguardando antes de fechar (10s)...")
                time.sleep(10)  # Tempo extra para garantir
                _log(logger, "Finalizando driver...")
                driver.quit()
                _log(logger, "Driver finalizado.")
            except Exception as e:
                _log(logger, f"Erro ao fechar driver: {e}")
        
        # Remove o perfil temporário
        if perfil_final and perfil_final != userdir:
            try:
                time.sleep(3)
                shutil.rmtree(perfil_final, ignore_errors=True)
                _log(logger, f"Perfil temporário removido: {perfil_final}")
            except Exception as e:
                _log(logger, f"Aviso: Não foi possível remover perfil temporário: {e}")


'''def enviar_arquivo(driver, file_path, message=None, headless=False, logger=None):
    """
    Envia apenas o arquivo (sem legenda).
    Ajustado para funcionar em modo visível (clicando) e Headless (direto).
    """
    try:
        _log(logger, f"Anexando arquivo: {file_path}")
        input_file = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        input_file.send_keys(file_path)
        time.sleep(3.5)
        # Botão de enviar (ícone de aviãozinho)
        send_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send'] | //span[@data-icon='wds-ic-send-filled'] | //div[@role='button' and @aria-label='Enviar']"))
        )
        
        send_btn.click()
        return True
        if not headless:
            # Modo Visível: Segue o fluxo de cliques para o usuário ver
            try:
                clicar_clip(driver, logger=logger)
                clicar_botao_documento(driver, logger=logger)
                time.sleep(1) # Pequena pausa para o input carregar no DOM
            except Exception as e:
                _log(logger, f"Aviso: Falha no fluxo de cliques, tentando injeção direta: {e}")
        
        # Localiza o input (comum a ambos os modos, mas essencial no Headless)
        # Usamos presence_of_element_located porque no Headless o input costuma ficar oculto (display:none)
        input_file = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )

        if not input_file:
            raise Exception("input[type='file'] não encontrado")

        # Upload do arquivo (o send_keys funciona mesmo com o input invisível)
        input_file.send_keys(file_path)
        
        # Espera o arquivo carregar na tela de preview (fundamental no Headless)
        time.sleep(2)

        # Encontrar o botão de enviar (aviãozinho)
        # Tenta os XPaths conhecidos do WhatsApp
        send_btn = None
        try:
            send_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-label='Enviar']"))
            )
        except:
            try:
                send_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send' or @data-icon='wds-ic-send-filled']"))
                )
            except:
                pass

        if not send_btn:
            raise Exception("Botão de envio do arquivo não encontrado no preview")

        # Clica para enviar
        send_btn.click()
        
        _log(logger, "Arquivo enviado com sucesso")
        time.sleep(2) # Garante que o upload complete antes de fechar/mudar
        return True

    except Exception as e:
        _log(logger, f"Erro enviar_arquivo: {e}")
        raise

def enviar_arquivo_com_mensagem(driver, file_path, message, headless=False, logger=None):
    """
    Envia arquivo com legenda (mensagem).
    Funciona via injeção direta no input[type='file'], que é o método mais estável.
    """
    try:
        _log(logger, f"Anexando arquivo com legenda: {os.path.basename(file_path)}")
        
        # 1. Localiza o input (funciona mesmo invisível)
        input_file = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        input_file.send_keys(file_path)
        
        # 2. Aguarda o WhatsApp carregar o preview do arquivo e o campo de legenda
        time.sleep(3.5)

        # 3. Localiza e preenche a legenda (se houver)
        if message:
            try:
                # O seletor de legenda no preview costuma ser este:
                caption_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='textbox' and (@aria-label='Adicionar legenda' or @aria-label='Digite uma mensagem')]"))
                )
                caption_box.send_keys(message)
                time.sleep(1)
            except Exception as e:
                _log(logger, f"⚠️ Aviso: Não foi possível inserir a legenda: {e}")

        # 4. Localiza o botão de enviar do Preview (aviãozinho verde)
        # Combinamos vários XPaths em um só para maior velocidade
        send_xpath = "//div[@role='button' and @aria-label='Enviar'] | //span[@data-icon='send'] | //span[@data-icon='wds-ic-send-filled']"
        send_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, send_xpath))
        )
        
        send_btn.click()
        _log(logger, "✓ Arquivo e legenda enviados com sucesso.")
        
        # 5. Tempo de segurança para garantir que o upload saia do computador
        time.sleep(4) 
        return True

    except Exception as e:
        _log(logger, f"Erro enviar_arquivo_com_mensagem: {e}")
        raise'''

'''def enviar_arquivo_com_mensagem(driver, file_path, message, headless=False, logger=None):
    """
    Envia arquivo com legenda (mensagem).
    Ajustado para ignorar cliques de interface no modo Headless.
    """
    try:
        _log(logger, f"Anexando arquivo com legenda: {os.path.basename(file_path)}")
        

        if not headless:
            # Modo Visível: Clica nos botões da interface
            clicar_clip(driver, logger=logger)
            try:
                clicar_botao_documento(driver, logger=logger)
            except Exception:
                _log(logger, "Botão 'Documento' não encontrado, tentando seguir com injeção")
        
        # Localiza o input (Crucial: funciona em ambos os modos, mas é o único que funciona no Headless)
        input_file = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        
        if not input_file:
            raise Exception("Não foi possível localizar input[type='file']")

        # Injeta o arquivo
        input_file.send_keys(file_path)
        
        # No Headless, o WhatsApp precisa de um tempo para carregar a prévia e mostrar o campo de legenda
        time.sleep(2.5)

        # Candidatos para a caixa de legenda (Preview)
        caption_candidates = [
            (By.XPATH, "//div[@role='textbox' and @aria-label='Adicionar legenda']"), # Novo padrão
            (By.XPATH, "//div[@role='textbox' and @aria-label='Digite uma mensagem']"),
            (By.XPATH, "//div[@contenteditable='true' and @data-tab='10']"), # Tab index da legenda costuma ser alto
            (By.CSS_SELECTOR, "div[contenteditable='true']")
        ]

        # Tenta encontrar a caixa de legenda com uma espera curta
        caption_box = None
        for by, value in caption_candidates:
            try:
                caption_box = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((by, value))
                )
                if caption_box:
                    break
            except:
                continue

        if not caption_box:
            _log(logger, "Caixa de legenda não encontrada — enviando sem legenda")
        else:
            try:
                # No Headless, clicar às vezes falha; send_keys direto costuma ser mais seguro
                if message:
                    caption_box.send_keys(message)
                    time.sleep(0.5)
            except Exception as e:
                _log(logger, f"Falha ao inserir legenda: {e}")

        # Busca o botão de enviar (aviãozinho)
        send_btn = None
        try:
            send_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-label='Enviar']"))
            )
        except:
            try:
                send_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send' or @data-icon='wds-ic-send-filled']"))
                )
            except:
                pass

        if not send_btn:
            raise Exception("Botão de envio não encontrado na tela de prévia")

        # Clique final para enviar
        send_btn.click()

        _log(logger, "Arquivo + mensagem enviados com sucesso")
        time.sleep(2) # Espera o envio processar
        return True

    except Exception as e:
        _log(logger, f"Erro enviar_arquivo_com_mensagem: {e}")
        raise'''
# --------------------------
# Função mestre
# --------------------------
'''def executar_envio(userdir, target, mode, message=None, file_path=None, logger=None, headless=True):
    """
    Função mestre: inicializa driver, procura contato e decide qual envio executar.
    mode: 'text', 'file', 'file_text'
    """
    driver = None
    perfil_final = None

    try:
        if userdir is None:
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            userdir = os.path.join(base_dir, "perfil_bot_whatsapp")

        # CRUCIAL: Cria a cópia para não conflitar com o seu Chrome aberto
        perfil_final = criar_perfil_temporario(userdir, logger)

        # Inicia o driver com a CÓPIA do perfil
        driver = iniciar_driver(userdir=perfil_final, headless=headless, logger=logger)
        vezes_executadas = contador_execucao(incrementar=False)
        if logger:
            logger(f'Execução número {vezes_executadas}')
            if headless:
                logger('Rodando em headless (segundo plano).')

        procurar_contato_grupo(driver, target, logger=logger)
        time.sleep(1.0)

        if mode == "text":
            if not message:
                raise Exception("Modo 'text' selecionado mas nenhuma mensagem fornecida.")
            enviar_mensagem_simples(driver, message, logger=logger)
        elif mode == "file":
            if not file_path:
                raise Exception("Modo 'file' selecionado mas nenhum arquivo fornecido.")
            enviar_arquivo(driver, file_path, message=None, headless=headless, logger=logger)
        elif mode == "file_text":
            if not file_path:
                raise Exception("Arquivo necessário para modo 'file_text'.")
            enviar_arquivo_com_mensagem(driver, file_path, message or "", headless=headless, logger=logger)
        else:
            raise Exception("Modo desconhecido.")
        return True
    except Exception as e:
        _log(logger, f"Erro em executar_envio: {str(e)}")
        _log(logger, traceback.format_exc())
        raise
    finally:
        # SIMPLES: Fecha o driver se ele existir
        if driver:
            try:
                time.sleep(10)  # Espera 10 segundos antes de fechar para caso envie um arquivo maior
                driver.close()
                driver.quit()
                _log(logger, "Driver finalizado.")
            except Exception as e:
                _log(logger, f"Erro ao finalizar driver: {e}")

        if perfil_final and perfil_final != userdir:
            try:
                time.sleep(2)  # Aguarda o Chrome fechar completamente
                shutil.rmtree(perfil_final, ignore_errors=True)
                _log(logger, f"Perfil temporário removido: {perfil_final}")
            except Exception as e:
                _log(logger, f"Aviso: Não foi possível remover perfil temporário: {e}")'''