import os
import time
import traceback
import sys
import undetected_chromedriver as uc
import json
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
            logger=lambda m: print(f"[AUTO-LOG] {m}")
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
        # fallback simples para stdout
        print(msg)

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
def iniciar_driver(userdir=None, headless=False, timeout=60, logger=None):
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

        # --- HEADLESS ---
        '''if headless:
            if logger: logger("Modo invisível (headless) ativado para esta execução.")
            options.add_argument('--headless=new')
            options.add_argument("--window-size=1920,1080")
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-setuid-sandbox')
            options.add_argument('--remote-debugging-pipe')
            options.add_argument('--no-first-run')
            options.add_argument('--no-default-browser-check')
        else:
            options.add_argument("--start-maximized")'''

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
# Funções públicas de envio
# --------------------------
def enviar_arquivo(driver, file_path, logger=None):
    """
    Envia apenas o arquivo (sem legenda).
    Fluxo:
    - clicar clip
    - clicar Documento (ou outra opção necessária)
    - localizar input[type=file] e enviar caminho
    - clicar botão de enviar do preview
    """
    try:
        _log(logger, f"Anexando arquivo: {file_path}")

        clicar_clip(driver, logger=logger)

        try:
            clicar_botao_documento(driver, logger=logger)
        except Exception:
            _log(logger, "Opção 'Documento' não encontrada — tentando upload pelo input")

        # upload do arquivo
        input_file = localizar_input_file(driver, logger)
        if not input_file:
            raise Exception("input[type='file'] não encontrado para upload do arquivo")

        input_file.send_keys(file_path)
        time.sleep(1.2)

        # encontrar o botão de enviar arquivo
        send_btn = _wait(driver, By.XPATH, "//div[@role='button' and @aria-label='Enviar']", timeout=2)
        if not send_btn:
            send_btn = _wait(driver, By.XPATH, "//span[@data-icon='wds-ic-send-filled' or @data-icon='send']", timeout=2)

        if not send_btn:
            raise Exception("Botão de envio do arquivo não encontrado")

        try:
            send_btn.click()
        except Exception as e:
            _log(logger, "Falha ao clicar botão de enviar arquivo")
            raise e

        _log(logger, "Arquivo enviado com sucesso")
        return True

    except Exception as e:
        _log(logger, f"Erro enviar_arquivo: {e}")
        raise
    time.sleep(2)

def enviar_arquivo_com_mensagem(driver, file_path, message, logger=None):
    """
    Envia arquivo com legenda (mensagem).
    Observação: alguns campos de legenda só aparecem após upload; usamos espera.
    """
    try:
        _log(logger, f"Anexando arquivo com legenda: {file_path}")

        clicar_clip(driver, logger=logger)

        try:
            clicar_botao_documento(driver, logger=logger)
        except Exception:
            _log(logger, "Documento não obrigatório — seguindo")

        input_file = localizar_input_file(driver, logger)
        if not input_file:
            raise Exception("Não foi possível localizar input[type='file']")

        input_file.send_keys(file_path)
        time.sleep(1.0)

        caption_candidates = [
            (By.XPATH, "//div[@role='textbox' and @aria-label='Digite uma mensagem']"),
            (By.XPATH, "//div[@contenteditable='true' and @data-tab='6']"),
            (By.CSS_SELECTOR, "div[contenteditable='true']")
        ]

        caption_box, sel = _find(driver, caption_candidates)
        if not caption_box:
            _log(logger, "Caixa de legenda não encontrada — ignorando legenda")
        else:
            try:
                caption_box.click()
                if message:
                    caption_box.send_keys(message)
                    time.sleep(0.4)
            except Exception as e:
                raise Exception("Falha ao inserir legenda")

        send_btn = _wait(driver, By.XPATH, "//div[@role='button' and @aria-label='Enviar']", timeout=2)
        if not send_btn:
            send_btn = _wait(driver, By.XPATH, "//span[@data-icon='wds-ic-send-filled' or @data-icon='send']", timeout=2)

        if not send_btn:
            raise Exception("Botão de envio do arquivo+mensagem não encontrado")

        try:
            send_btn.click()
        except Exception as e:
            _log(logger, "Falha ao clicar botão de envio de arquivo + mensagem")
            raise e

        _log(logger, "Arquivo + mensagem enviados com sucesso")
        return True

    except Exception as e:
        _log(logger, f"Erro enviar_arquivo_com_mensagem: {e}")
        raise
    time.sleep(3)

# --------------------------
# Função mestre
# --------------------------
def executar_envio(userdir, target, mode, message=None, file_path=None, logger=None):
    """
    Função mestre: inicializa driver, procura contato e decide qual envio executar.
    mode: 'text', 'file', 'file_text'
    """
    driver = None

    try:
        vezes_executadas = contador_execucao(incrementar=False)
        usar_headless = False #if vezes_executadas >=3 else False

        if logger:
            logger(f'Execução número {vezes_executadas}')
            '''if usar_headless:
                logger('A partir de agora, as automações rodarão em segundo plano.')'''

        driver = iniciar_driver(userdir=userdir, headless=usar_headless, logger=logger)
        procurar_contato_grupo(driver, target, logger=logger)
        time.sleep(1.0)

        if mode == "text":
            if not message:
                raise Exception("Modo 'text' selecionado mas nenhuma mensagem fornecida.")
            enviar_mensagem_simples(driver, message, logger=logger)
        elif mode == "file":
            if not file_path:
                raise Exception("Modo 'file' selecionado mas nenhum arquivo fornecido.")
            enviar_arquivo(driver, file_path, logger=logger)
        elif mode == "file_text":
            if not file_path:
                raise Exception("Arquivo necessário para modo 'file_text'.")
            enviar_arquivo_com_mensagem(driver, file_path, message or "", logger=logger)
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
            except:
                pass  # Se der erro ao fechar, continua
