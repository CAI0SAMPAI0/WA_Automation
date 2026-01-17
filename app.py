'''import sys
import os
from datetime import datetime
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow
from core.automation import executar_envio, contador_execucao

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROFILE_DIR = os.path.join(BASE_DIR, "perfil_bot_whatsapp")

def ensure_profile_dir():
    os.makedirs(PROFILE_DIR, exist_ok=True)

# Logger para execução automática
def get_file_logger():
    logs_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_path = os.path.join(
        logs_dir, 
        f"auto_{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    def logger(msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        print(line.strip())
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)

    return logger

def run_gui():
    ensure_profile_dir()
    app = QApplication(sys.argv)

    # Ícone (Windows)
    from PySide6.QtGui import QIcon
    icon_path = os.path.join(BASE_DIR, "resources", "Taty_s-English-Logo.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "WhatsAppAutomation"
                )
            except Exception:
                pass

    qss_path = os.path.join(BASE_DIR, "ui", "styles.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    
    sys.exit(app.exec())

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    # Se o argumento --auto estiver presente, roda a automação e fecha
    if "--auto" in sys.argv:
        try:
            print(f"DEBUG: Modo Automático detectado. Argumentos: {sys.argv}")
            # Pega o caminho do JSON que está após o --auto
            index = sys.argv.index("--auto")
            json_path = sys.argv[index + 1]
            
            import json

            with open(json_path, "r", encoding="utf-8") as f:
                dados = json.load(f)

            executar_envio(
                userdir=PROFILE_DIR,
                target=dados["target"],
                mode=dados["mode"],
                message=dados.get("message"),
                file_path=dados.get("file_path"),
                modo_execucao='auto'  # ← FAKE HEADLESS para agendamentos
            )

            print("DEBUG: Automação finalizada. Encerrando processo.")
            sys.exit(0)
        except Exception as e:
            print(f"ERRO CRÍTICO NO MODO AUTO: {e}")
            sys.exit(1)
    
    # Se não for modo auto, abre a interface normal
    else:
        run_gui()'''

# app ctk

import sys
import os
from datetime import datetime
import json
import argparse
# Importando a nova janela
from ui.main_window import App 
from core.automation import executar_envio, contador_execucao
from core.db import db

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROFILE_DIR = os.path.normpath(os.path.abspath(os.path.join(BASE_DIR, "perfil_bot_whatsapp")))

def ensure_profile_dir():
    os.makedirs(PROFILE_DIR, exist_ok=True)

def run_gui():
    ensure_profile_dir()
    app = App()
    app.mainloop()

if __name__ == "__main__":
    # Usando argparse para capturar os argumentos de forma limpa
    parser = argparse.ArgumentParser(description="WhatsApp Automation App")
    parser.add_argument("--auto", help="Caminho do arquivo JSON de configuração")
    parser.add_argument("--task_id", type=int, help="ID da tarefa no banco de dados")
    
    # Ignora argumentos desconhecidos para não quebrar a GUI
    args, unknown = parser.parse_known_args()

    if args.auto:
        task_id = args.task_id
        try:
            # 1. Carrega os dados do JSON
            with open(args.auto, "r", encoding="utf-8") as f:
                dados = json.load(f)

            # 2. Atualiza o status no banco para 'running' (se o task_id existir)
            if task_id:
                db.atualizar_status(task_id, 'running')

            # 3. Executa a automação
            executar_envio(
                userdir=PROFILE_DIR,
                target=dados["target"],
                mode=dados["mode"],
                message=dados.get("message"),
                file_path=dados.get("file_path"),
                modo_execucao='auto'
            )

            # 4. Sucesso: Atualiza o banco e o contador
            if task_id:
                db.atualizar_status(task_id, 'completed')
                
            if callable(contador_execucao):
                contador_execucao(True)
                
            sys.exit(0)

        except Exception as e:
            # 5. Erro: Registra a falha no banco para o usuário ver na UI
            print(f"ERRO CRÍTICO NA EXECUÇÃO AUTO: {e}")
            if task_id:
                db.registrar_erro(task_id, str(e))
            sys.exit(1)
    else:
        # Se não houver flag --auto, abre a interface gráfica normalmente
        run_gui()
