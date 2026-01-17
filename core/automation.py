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
import pyperclip


# Delays (ajustáveis)
WHATSAPP_LOAD = 20
SHORT_DELAY = 1.0
MID_DELAY = 2.0
LONG_DELAY = 3.0

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

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        current_profile = os.path.join(base_dir, "perfil_bot_whatsapp")

        # Chama a função mestre com modo_execucao='auto'
        executar_envio(
            userdir=current_profile,
            target=target,
            mode=mode,
            message=message,
            file_path=file_path,
            logger=lambda m: print(f"[AUTO-LOG] {m}"),
            modo_execucao='auto'  # ← ADICIONADO
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

def _wait(driver, by, selector, timeout=2):
    """Espera por presença de elemento e retorna WebElement ou None."""
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
    except Exception:
        return None

def _wait_clickable(driver, by, selector, timeout=2):
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
            el = _wait(driver, by, sel, timeout=2)
            if el:
                return el, (by, sel)
        except Exception:
            continue
    return None, None


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
def iniciar_driver(userdir=None, modo_execucao='manual', timeout=20, logger=None):
    """
    Inicia undetected_chromedriver com perfil persistente.
    
    Args:
        modo_execucao: 'manual' = Chrome visível | 'auto' = fake headless
    """
    try:
        if userdir is None:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                base_dir = os.path.join(base_dir, "..")

            userdir = os.path.join(base_dir, "perfil_bot_whatsapp")

        if not os.path.exists(userdir):
            os.makedirs(userdir)
            if logger:
                logger(f"Criado novo perfil Chrome em: {userdir}")

        if logger:
            logger(f"Iniciando Chrome com profile: {userdir} | modo: {modo_execucao}")

        # DEBUG EXPLÍCITO
        print(f"========================================")
        print(f"DEBUG iniciar_driver():")
        print(f"  modo_execucao recebido: '{modo_execucao}'")
        print(f"  userdir: {userdir}")
        print(f"========================================")

        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={userdir}")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--js-flags="--max-old-space-size=512"')
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")

        # ==============================
        # MODO DE EXECUÇÃO
        # ==============================
        if modo_execucao == 'auto':
            # FAKE HEADLESS (janela fora da tela) - SOMENTE NO MODO AUTO
            print(f"  ✓ APLICANDO FAKE HEADLESS (modo auto)")
            options.add_argument("--window-position=9999,9999")
            options.add_argument("--window-size=800,600")
            #options.add_argument('--minimize-window')
            options.add_argument("--disable-backgrounding-occluded-windows")
            if logger:
                logger("⚙️ Chrome configurado em FAKE HEADLESS (modo automático).")
        else:
            # MODO MANUAL (janela visível) - NÃO ADICIONA NADA ESPECIAL
            print(f"  ✓ MODO VISÍVEL (modo manual) - SEM fake headless")
            options.add_argument("--start-maximized")
            options.add_argument("--window-position=0,0")
            if logger:
                logger("⚙️ Chrome configurado em modo VISÍVEL (execução manual).")
        
        print(f"========================================\n")

        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.browser_pid = driver.browser_pid
        driver.set_page_load_timeout(10)
        #driver.maximize_window()
        if modo_execucao != 'auto':
            driver.set_window_position(0, 0)
            driver.maximize_window()

        if logger:
            logger("Chrome iniciado. Acessando WhatsApp Web...")
        time.sleep(2)
        driver.get("https://web.whatsapp.com")
        wait_time = 20
        if logger:
            logger(f"Aguardando {wait_time} segundos para carregar WhatsApp...")
        time.sleep(wait_time)

        try:
            driver.find_element(By.XPATH, "//div[@role='textbox']")
            if logger:
                logger("✓ WhatsApp Web carregado (DOM ativo).")
        except:
            if logger:
                logger("⚠️ WhatsApp Web pode não estar autenticado.")

        return driver

    except Exception as e:
        if logger:
            logger(f"❌ ERRO ao iniciar Chrome: {e}")
            logger(traceback.format_exc())
        raise


# --------------------------
# Buscar contato / abrir chat
# --------------------------
def procurar_contato_grupo(driver, target, logger=None, timeout=1):
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
            first_chat = _wait_clickable(driver, By.CSS_SELECTOR, "div[role='listitem']")
            time.sleep(0.01)
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
        time.sleep(0.5)
        try:
            # limpar (Ctrl+A + Del)
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
        except Exception:
            # fallback: executar script para limpar
            driver.execute_script("arguments[0].innerText = '';", search_box)
        time.sleep(0.5)
        search_box.send_keys(target)
        time.sleep(1)
        search_box.send_keys(Keys.ENTER)
        time.sleep(0.5)

        _log(logger, "Contato/grupo aberto.")
        return True
    except Exception as e:
        _log(logger, f"Erro procurar_contato_grupo: {str(e)}")
        _log(logger, traceback.format_exc())
        raise

# --------------------------
# Mensagem de texto
# --------------------------

def enviar_mensagem_simples(driver, message, logger=None, timeout=1):
    """
    Envia mensagem de texto no chat aberto, respeitando quebras de linha com Shift+Enter.
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
        
        time.sleep(0.5)

        # --- CORREÇÃO: Envia linha por linha com SHIFT+ENTER ---
        linhas = message.split('\n')
        for i, linha in enumerate(linhas):
            msg_box.send_keys(linha)
            if i < len(linhas) - 1:  # Se não for a última linha, pula para a próxima
                msg_box.send_keys(Keys.SHIFT + Keys.ENTER)
        
        # Removido: msg_box.send_keys(message) <- Isso duplicaria o texto
        time.sleep(0.5)

        # Tentar localizar o botão de enviar (ícone da setinha)
        send_btn = _wait(driver, By.XPATH, "//span[@data-icon='wds-ic-send-filled']", timeout=1)
        if not send_btn:
            send_btn = _wait(driver, By.CSS_SELECTOR, "span[data-icon='send']", timeout=1)

        # Se achar o botão, clica. Se não, usa o Enter para enviar.
        if send_btn:
            try:
                send_btn.click()
                _log(logger, "Mensagem enviada via clique no botão.")
            except Exception:
                msg_box.send_keys(Keys.ENTER)
                _log(logger, "Botão encontrado mas sem clique; enviado via Enter.")
        else:
            msg_box.send_keys(Keys.ENTER)
            _log(logger, "Botão de enviar não encontrado; enviado via Enter.")

        time.sleep(SHORT_DELAY)
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
    time.sleep(0.5)
    _log(None, f"clicar_clip: clique realizado ({sel}).")
    return True

def clicar_botao_documento(driver, file_path, logger=None):
    """
    Diferencia entre WhatsApp Normal e Business para garantir o envio como mídia.
    """
    try:
        ext = os.path.splitext(file_path.lower())[1]
        is_media = ext in ['.jpg', '.jpeg', '.png', '.gif', '.mp4']
        
        if is_media:
            _log(logger, "Selecionando Fotos e Vídeos (Business)...")
            tipo_candidates = [
                (By.CSS_SELECTOR, "div[role='button'] span[data-icon='attach-image']"), # Universal
                (By.XPATH, "//div[contains(@aria-label, 'Fotos')]"), # Acessibilidade
                (By.XPATH, "/html/body/div[1]/div/div/div/div/span[6]/div/ul/div/div/div[2]/li"), # Seu XPath
                (By.CSS_SELECTOR, "li:nth-child(2) div span") # Seu CSS simplificado
            ]
        else:
            _log(logger, "Selecionando Documentos (Business)...")
            tipo_candidates = [
                (By.CSS_SELECTOR, "div[role='button'] span[data-icon='attach-document']"),
                (By.XPATH, "/html/body/div[1]/div/div/div/div/span[6]/div/ul/div/div/div[1]/li"), # Seu XPath
                (By.CSS_SELECTOR, "li:nth-child(1) div span") # Seu CSS
            ]

        el, sel = _find(driver, tipo_candidates)
        
        if not el:
            # Fallback para WhatsApp Normal (caso os seletores acima falhem)
            _log(logger, "Tentando fallback para WhatsApp Normal...")
            el = _wait(driver, By.XPATH, "//span[contains(., 'Fotos')] | //span[contains(., 'Documento')]", timeout=2)

        if not el:
            raise Exception("Não foi possível encontrar a opção de anexo no menu.")
        
        # Clica via JavaScript para garantir que o clique aconteça mesmo se o menu estiver animando
        driver.execute_script("arguments[0].click();", el)
        time.sleep(2)
        return True
    except Exception as e:
        _log(logger, f"Erro clicar_botao_documento: {e}")
        raise

def localizar_input_file(driver, logger=None, timeout=2):
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

def upload_arquivo(driver, file_path, logger=None, timeout=1):
    """
    Envia caminho ao input[type=file].
    """
    try:
        input_file = localizar_input_file(driver, logger=logger, timeout=timeout)
        if not input_file:
            raise Exception("input[type='file'] não encontrado (após abrir painel).")
        # send_keys com caminho absoluto
        input_file.send_keys(file_path)
        time.sleep(2)  # dar tempo para o preview ser processado
        _log(logger, f"upload_arquivo: arquivo enviado ao input ({file_path}).")
        return True
    except Exception as e:
        _log(logger, f"Erro upload_arquivo: {e}")
        _log(logger, traceback.format_exc())
        raise

def enviar_arquivo(driver, file_path, logger=None):
    """
    Envia arquivos um por um para evitar o erro 'invalid argument'.
    """
    try:
        # Garante que file_path seja uma lista, mesmo que venha do agendamento como string
        paths = file_path.split('\n') if isinstance(file_path, str) else file_path
        
        for p in paths:
            p = p.strip()
            if not p or not os.path.exists(p): continue
            
            _log(logger, f"Anexando individualmente: {os.path.basename(p)}")
            clicar_clip(driver, logger=logger)
            clicar_botao_documento(driver, p, logger=logger)

            input_file = localizar_input_file(driver, logger)
            if not input_file: raise Exception("Input file não encontrado")
            
            # Envia o caminho absoluto de apenas UM arquivo por vez
            input_file.send_keys(os.path.abspath(p))
            time.sleep(2.0) 

            # Botão de enviar (seta verde) - Seletor híbrido para Business e Normal
            send_btn = _wait(driver, By.XPATH, "//div[@role='button' and @aria-label='Enviar'] | //span[@data-icon='send']", timeout=5)
            
            if send_btn:
                driver.execute_script("arguments[0].click();", send_btn)
                time.sleep(2.0) 
            else:
                _log(logger, "Botão de enviar não encontrado após upload.")

        return True
    except Exception as e:
        _log(logger, f"Erro enviar_arquivo: {e}")
        raise

def enviar_arquivo_com_mensagem(driver, file_path, message, logger=None):
    try:
        # 1. Preparação dos arquivos 
        paths = [os.path.abspath(p.strip()) for p in file_path.split('\n') if p.strip()] if isinstance(file_path, str) else [os.path.abspath(p) for p in file_path]
        full_paths_string = "\n".join(paths)

        # 2. Abrir menu de anexo
        clicar_clip(driver, logger=logger)
        
        # --- LÓGICA HÍBRIDA PARA BOTÃO DE FOTOS/VÍDEOS ---
        _log(logger, "Localizando botão de Fotos e Vídeos...")
        seletores_fotos = [
            (By.XPATH, "/html/body/div[1]/div/div/div/div/span[6]/div/ul/div/div/div[2]/li"), # Business
            (By.XPATH, '//*[@id="app"]/div/div/div[4]/div/div/div[1]/div[1]/div/div/div/div/div[1]/div[2]/div[1]/div[2]/span'), # Normal XPath
            (By.CSS_SELECTOR, "#app > div > div > div:nth-child(11) > div > div > div.xu96u03.xm80bdy.x10l6tqk.x13vifvy.xoz0ns6.x1gslohp > div.html-div.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu.xyri2b.x18d9i69.x1c1uobl > div > div > div > div > div.x78zum5.xdt5ytf.x1iyjqo2.x1n2onr6 > div:nth-child(2) > div.x6s0dn4.xlr9sxt.xvvg52n.xwd4zgb.xq8v1ta.x78zum5.xu0aao5.xh8yej3 > div.x78zum5.xdt5ytf.x1iyjqo2.xde1mab > span"), # Normal CSS
            (By.XPATH, "//span[@data-icon='attach-image']/parent::div/parent::li") # Fallback Universal
        ]
        
        btn_fotos, _ = _find(driver, seletores_fotos)
        
        if not btn_fotos:
            raise Exception("Não foi possível encontrar o botão de Fotos em nenhuma das versões.")
            
        driver.execute_script("arguments[0].click();", btn_fotos)
        time.sleep(2)

        # 3. Enviar arquivos (Injeção direta no input oculto)
        input_file = localizar_input_file(driver, logger)
        input_file.send_keys(full_paths_string)
        
        _log(logger, "Aguardando preview das imagens...")
        time.sleep(6) # Tempo essencial para o WA montar o álbum

        # 4. Inserir Legenda via Ctrl+V 
        if message:
            _log(logger, "Colando legenda...")
            # Unindo seus candidatos do Business com o normal
            caption_candidates = [
                (By.XPATH, "//*[@id='app']/div/div/div[3]/div/div[3]/div[2]/div/span/div/div/div/div[2]/div/div[1]/div[3]/div/div/div[1]/div[1]/div[1]/p"), # Business/Normal XPath
                (By.CSS_SELECTOR, "div.lexical-rich-text-input div[contenteditable='true']"), # CSS Geral
                (By.XPATH, "//div[contains(@aria-label, 'legenda')]"), # Atributo Acessibilidade
                (By.CSS_SELECTOR, "#app > div > div > div.x78zum5.xdt5ytf.x5yr21d > div > div.x10l6tqk.x13vifvy.x1o0tod.x78zum5.xh8yej3.x5yr21d.x6ikm8r.x10wlt62.x47corl > div.x9f619.x1n2onr6.x5yr21d.x6ikm8r.x10wlt62.x17dzmu4.x1i1dayz.x2ipvbc.xjdofhw.xyyilfv.x1iyjqo2.xpilrb4.x1t7ytsu.x1vb5itz.x12xzxwr > div > span > div > div > div > div.x1n2onr6.xupqr0c.x78zum5.x1r8uery.x1iyjqo2.xdt5ytf.x1hc1fzr.x6ikm8r.x10wlt62.x1anedsm > div > div.x78zum5.x1iyjqo2.xs83m0k.x1r8uery.xdt5ytf.x1qughib.x6ikm8r.x10wlt62 > div.x1c4vz4f.xs83m0k.xdl72j9.x1g77sc7.x78zum5.xozqiw3.x1oa3qoh.x12fk4p8.xeuugli.x2lwn1j.xl56j7k.x1q0g3np.x6s0dn4.x1n2onr6.xo8q3i6.x1y1aw1k.xwib8y2.x1c1uobl.xyri2b > div > div > div.x1c4vz4f.xs83m0k.xdl72j9.x1g77sc7.x78zum5.xozqiw3.x1oa3qoh.x12fk4p8.xeuugli.x2lwn1j.x1nhvcw1.x1q0g3np.x1cy8zhl.x9f619.xh8yej3.x1ba4aug.x1tiyuxx.xvtqlqk.x1nbhmlj.xdx6fka.x1od0jb8.xyi3aci.xwf5gio.x1p453bz.x1suzm8a > div.x1n2onr6.xh8yej3.x1k70j0n.x14z9mp.xzueoph.x1lziwak.xisnujt.x14ug900.x1vvkbs.x126k92a.x1hx0egp.lexical-rich-text-input > div.x1hx0egp.x6ikm8r.x1odjw0f.x1k6rcq7.x1lkfr7t > p") # CSS Normal
            ]
            
            caption_box, _ = _find(driver, caption_candidates)
            
            if caption_box:
                pyperclip.copy(message)
                caption_box.click()
                time.sleep(0.5)
                
                # Técnica Ctrl+A + Backspace + Ctrl+V
                caption_box.send_keys(Keys.CONTROL + "a")
                caption_box.send_keys(Keys.BACKSPACE)
                caption_box.send_keys(Keys.CONTROL + "v")
                time.sleep(1)
            else:
                _log(logger, "Aviso: Caixa de legenda não encontrada para colar texto.")

        # 5. Clique no Enviar (Seta Verde)
        # Sendo redundante com seletores de ícone e de label
        send_btn_candidates = [
            (By.XPATH, "//span[@data-icon='send']"),
            (By.XPATH, "//div[@role='button' and @aria-label='Enviar']"),
            (By.XPATH, "//*[@id='app']/div/div/div[3]/div/div[3]/div[2]/div/span/div/div/div/div[2]/div/div[2]/div[2]/span/div/div/span"),
            (By.XPATH, "/html/body/div[1]/div/div/div/div/div[3]/div/div[3]/div[2]/div/span/div/div/div/div[2]/div/div[2]/div[2]/span/div/div/span"),
            (By.CSS_SELECTOR, "div[aria-label='Enviar'] span[data-icon='send']"),
            (By.CSS_SELECTOR, "#app > div > div > div.x78zum5.xdt5ytf.x5yr21d > div > div.x10l6tqk.x13vifvy.x1o0tod.x78zum5.xh8yej3.x5yr21d.x6ikm8r.x10wlt62.x47corl > div.x9f619.x1n2onr6.x5yr21d.x6ikm8r.x10wlt62.x17dzmu4.x1i1dayz.x2ipvbc.xjdofhw.xyyilfv.x1iyjqo2.xpilrb4.x1t7ytsu.x1vb5itz.x12xzxwr > div > span > div > div > div > div.x1n2onr6.xupqr0c.x78zum5.x1r8uery.x1iyjqo2.xdt5ytf.x1hc1fzr.x6ikm8r.x10wlt62.x1anedsm > div > div.x78zum5.x1c4vz4f.x2lah0s.x1helyrv.x6s0dn4.x1qughib.x178xt8z.x13fuv20.xx42vgk.x1y1aw1k.xwib8y2.xf7dkkf.xv54qhq > div.x1247r65.xng8ra > span > div > div > span")
        ]
        send_btn, _ = _find(driver, send_btn_candidates)
        
        if send_btn:
            driver.execute_script("arguments[0].click();", send_btn)
            _log(logger, "Botão enviar clicado.")
        else:
            _log(logger, "Falha ao encontrar botão de envio final.")

        _log(logger, "Lote enviado com sucesso.")
        time.sleep(2)
        return True

    except Exception as e:
        _log(logger, f"Erro crítico na função: {e}")
        raise

# --------------------------
# Funções para múltiplos arquivos
# --------------------------

def enviar_arquivos_multiplos(driver, lista_file_paths, logger=None):
    """
    Envia vários arquivos de uma vez.
    lista_file_paths: deve ser uma lista de caminhos, ex: ['c:/img1.png', 'c:/img2.jpg']
    """
    try:
        # Transforma a lista em uma string única separada por \n
        files_string = "\n".join(lista_file_paths)
        primeiro_arquivo = lista_file_paths[0]

        _log(logger, f"Anexando {len(lista_file_paths)} arquivos...")
        clicar_clip(driver, logger=logger)
        
        # Usa o primeiro arquivo apenas para decidir se abre 'Fotos' ou 'Documentos'
        clicar_botao_documento(driver, primeiro_arquivo, logger=logger)

        input_file = localizar_input_file(driver, logger)
        if not input_file: 
            raise Exception("Input file não encontrado")
        
        # O segredo está aqui: enviar a string com todos os arquivos
        input_file.send_keys(files_string)
        
        # Tempo maior para carregar múltiplos previews
        time.sleep(4.0) 

        send_btn = _wait(driver, By.XPATH, "//div[@role='button' and @aria-label='Enviar']", timeout=3)
        if not send_btn:
            send_btn = _wait(driver, By.XPATH, "//span[@data-icon='send' or @data-icon='wds-ic-send-filled']", timeout=2)
        
        driver.execute_script("arguments[0].click();", send_btn)
        _log(logger, "Envio múltiplo concluído.")
        return True
    except Exception as e:
        _log(logger, f"Erro enviar_arquivos_multiplos: {e}")
        raise

def enviar_arquivos_multiplos_com_mensagem(driver, lista_file_paths, message, logger=None):
    """
    Envia vários arquivos e uma única legenda que vale para todos.
    """
    try:
        files_string = "\n".join(lista_file_paths)
        primeiro_arquivo = lista_file_paths[0]

        clicar_clip(driver, logger=logger)
        clicar_botao_documento(driver, primeiro_arquivo, logger=logger)

        input_file = localizar_input_file(driver, logger)
        input_file.send_keys(files_string)
        
        # Aguarda carregar todos os arquivos no preview
        time.sleep(5.0) 

        caption_candidates = [
            (By.XPATH, "//div[@role='textbox' and contains(@aria-label, 'mensagem')]"),
            (By.XPATH, "//div[@contenteditable='true' and @data-tab='10']"),
            (By.CSS_SELECTOR, "div[contenteditable='true']")
        ]
        
        caption_box, sel = _find(driver, caption_candidates)
        
        if caption_box:
            driver.execute_script("arguments[0].focus();", caption_box)
            caption_box.click()
            time.sleep(1)
            if message:
                caption_box.send_keys(message)
                time.sleep(1)

        send_btn = _wait(driver, By.XPATH, "//div[@role='button' and @aria-label='Enviar']", timeout=3)
        driver.execute_script("arguments[0].click();", send_btn)
        return True
    except Exception as e:
        _log(logger, f"Erro envio múltiplo com mensagem: {e}")
        raise

# --------------------------
# Função mestre
# --------------------------
def executar_envio(userdir, target, mode, message=None, file_path=None, logger=None, modo_execucao='manual'):
    """
    Função mestre: inicializa driver, procura contato e decide qual envio executar.
    
    Args:
        mode: 'text', 'file', 'file_text'
        modo_execucao: 'manual' (visível) ou 'auto' (fake headless)
    """
    driver = None

    try:
        vezes_executadas = contador_execucao(incrementar=False)

        # DEBUG EXPLÍCITO
        print(f"\n{'='*60}")
        print(f"DEBUG executar_envio():")
        print(f"  modo_execucao recebido: '{modo_execucao}'")
        print(f"  target: {target}")
        print(f"  mode: {mode}")
        print(f"  execuções anteriores: {vezes_executadas}")
        print(f"{'='*60}\n")

        if logger:
            logger(f'Execução número {vezes_executadas}')
            logger(f'Modo de execução: {modo_execucao}')

        driver = iniciar_driver(userdir=userdir, modo_execucao=modo_execucao, logger=logger)
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
        if driver:
            try:
                time.sleep(10) 
                # 1. Captura o PID enquanto o driver ainda está ativo
                pid_bot = getattr(driver, 'browser_pid', None) 
                
                # 2. Tenta o fechamento padrão
                driver.close()
                driver.quit()
                time.sleep(5)
                
                # 3. Mata o processo remanescente se ele ainda existir
                if pid_bot:
                    import psutil
                    if psutil.pid_exists(pid_bot):
                        processo = psutil.Process(pid_bot)
                        processo.terminate()
                
                _log(logger, "Driver e processos encerrados com sucesso.")
            except Exception as e:
                _log(logger, f"Aviso ao fechar: {e}")