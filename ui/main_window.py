import os
import sys
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
    QMessageBox, QComboBox, QDateTimeEdit
)
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QIcon
from core.windows_scheduler import create_task_bat, create_windows_task
from core.db import db
from core import automation
from core.automation import contador_execucao 

# icone
'''INTERNAL_DIR = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
'''
if getattr(sys, 'frozen', False):
    INTERNAL_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    # EXTERNAL_DIR é a pasta onde o usuário colocou o .exe
    EXTERNAL_DIR = os.path.dirname(sys.executable)
else:
    # Se for script Python normal
    INTERNAL_DIR = os.path.dirname(os.path.abspath(__file__))
    # Sobe um nível para sair da pasta 'ui' e ir para a raiz do projeto
    EXTERNAL_DIR = os.path.dirname(INTERNAL_DIR)
if getattr(sys, 'frozen', False):
    # Se for o EXE, pega a pasta onde o .exe está
    EXTERNAL_DIR = os.path.dirname(sys.executable)
else:
    # Se for script, pega a pasta raiz do projeto
    EXTERNAL_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

PROFILE_DIR = os.path.join(EXTERNAL_DIR, "perfil_bot_whatsapp")

def _get_icon_path():
    return os.path.join(INTERNAL_DIR, "resources", "Taty_s-English-Logo.ico")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study Practices - WhatsApp Automation")
        self.setMinimumSize(500, 750)

        self.tema_atual = 'claro'
        self.file_path = None
        icon_path = _get_icon_path()
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self._build_ui()
        self._aplicar_tema('claro')
        
        # Verifica status e atualiza contador na inicialização
        self.verificar_status_agendamentos()
        self.atualizar_contador_exibicao()

    def _aplicar_tema(self, modo):
        """Define as cores do app, incluindo os botões roxos com efeito hover"""
        if modo == 'escuro':
            bg_color = "#2b2b2b"
            text_color = "#ffffff"
            input_bg = "#3d3d3d"
            border = "#555"
            label_color = "#eeeeee"
        else:
            bg_color = "#f0f2f5"
            text_color = "#000000"
            input_bg = "#ffffff"
            border = "#ccc"
            label_color = "#333333"

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {bg_color}; }}
            QWidget {{ background-color: {bg_color}; color: {text_color}; }}
            
            QLineEdit, QTextEdit, QDateTimeEdit, QComboBox {{ 
                background-color: {input_bg}; 
                color: {text_color}; 
                border: 1px solid {border}; 
                border-radius: 4px; 
                padding: 5px;
            }}

            QLabel {{ color: {label_color}; }}

            /* BOTÕES ROXOS ESTILIZADOS */
            QPushButton {{
                background-color: #b39ddb; /* Roxo mais claro (Pastel) */
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
                border: none;
            }}

            QPushButton:hover {{
                background-color: #7e57c2; /* Roxo mais forte ao passar o mouse */
            }}

            QPushButton:pressed {{
                background-color: #5e35b1;
            }}

            QPushButton:disabled {{
                background-color: #d1d1d1;
                color: #888;
            }}
        """)

    def _toggle_tema(self):
        if self.tema_atual == "claro":
            self.tema_atual = "escuro"
            self.theme_btn.setText("☀️ Modo Claro")
        else:
            self.tema_atual = "claro"
            self.theme_btn.setText("🌙 Modo Escuro")
        self._aplicar_tema(self.tema_atual)

    def atualizar_contador_exibicao(self):
        """Atualiza a label de execuções lendo o arquivo de log"""
        print(f'DEBUG: Tentando ler contador em: {EXTERNAL_DIR}')
        try:
            # Tenta obter o número de execuções sem incrementar
            count = contador_execucao(incrementar=False)
            self.count_label.setText(f"Execuções totais: {count}")
        except Exception as e:
            print(f"Erro ao ler contador na UI: {e}")
            self.count_label.setText("Execuções totais: 0")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()

        # ===== BARRA SUPERIOR (Contador e Tema) =====
        top_bar = QHBoxLayout()
        self.count_label = QLabel("Execuções: 0")
        self.count_label.setStyleSheet("font-size: 11px; color: #888; font-weight: bold;")
        
        self.theme_btn = QPushButton("🌙 Modo Escuro")
        self.theme_btn.setFixedWidth(120)
        self.theme_btn.clicked.connect(self._toggle_tema)
        
        top_bar.addWidget(self.count_label)
        top_bar.addStretch()
        top_bar.addWidget(self.theme_btn)
        layout.addLayout(top_bar)

        # ===== ÁREA DE STATUS =====
        self.status_label = QLabel("Sistema pronto")
        self.status_label.setStyleSheet("padding: 5px; color: #555; border-bottom: 1px solid #ddd; margin-bottom: 10px;")
        layout.addWidget(self.status_label)

        # ===== CAMPOS DE ENTRADA =====
        layout.addWidget(QLabel("Contato / Número:"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Ex: 5511999999999 ou Nome do Contato")
        layout.addWidget(self.target_input)

        layout.addWidget(QLabel("Modo de envio:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Somente texto", "text")
        self.mode_combo.addItem("Somente arquivo", "file")
        self.mode_combo.addItem("Arquivo + texto", "file_text")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_change)
        layout.addWidget(self.mode_combo)

        layout.addWidget(QLabel("Mensagem:"))
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Digite sua mensagem aqui...")
        layout.addWidget(self.message_input)

        file_layout = QHBoxLayout()
        self.file_label = QLabel("Nenhum arquivo selecionado")
        self.file_btn = QPushButton("Selecionar Arquivo")
        self.file_btn.clicked.connect(self._select_file)
        file_layout.addWidget(self.file_btn)
        file_layout.addWidget(self.file_label)
        layout.addLayout(file_layout)

        layout.addWidget(QLabel("Data e hora do envio:"))
        self.datetime_picker = QDateTimeEdit()
        self.datetime_picker.setCalendarPopup(True)
        self.datetime_picker.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.datetime_picker.setMinimumDateTime(QDateTime.currentDateTime())
        self.datetime_picker.setDateTime(QDateTime.currentDateTime().addSecs(300))
        layout.addWidget(self.datetime_picker)

        # ===== BOTÕES DE AÇÃO =====
        buttons_layout = QHBoxLayout()
        self.send_now_btn = QPushButton("Enviar agora")
        self.send_now_btn.clicked.connect(self._send_now)
        buttons_layout.addWidget(self.send_now_btn)

        self.schedule_btn = QPushButton("Agendar")
        self.schedule_btn.clicked.connect(self._schedule_task)
        buttons_layout.addWidget(self.schedule_btn)
        layout.addLayout(buttons_layout)

        # ===== DICAS =====
        info_label = QLabel(
            "💡 Dica: O PC deve estar ligado no horário do envio.\n"
            "O Chrome abrirá automaticamente para realizar a automação."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 11px; padding: 10px;")
        layout.addWidget(info_label)

        central.setLayout(layout)
        self._on_mode_change()

    def verificar_status_agendamentos(self):
        logs_dir = os.path.join(EXTERNAL_DIR, "logs")
        if not os.path.exists(logs_dir): return
        hoje = datetime.now().strftime('%Y-%m-%d')
        log_path = os.path.join(logs_dir, f"auto_{hoje}.log")

        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    conteudo = f.read()
                    if "✓ AUTOMAÇÃO FINALIZADA COM SUCESSO" in conteudo:
                        self.status_label.setText("✅ Último agendamento concluído com sucesso!")
                        self.status_label.setStyleSheet("padding: 5px; color: green; font-weight: bold;")
                    elif "❌ ERRO CRÍTICO" in conteudo:
                        self.status_label.setText("⚠️ Falha detectada no último agendamento")
                        self.status_label.setStyleSheet("padding: 5px; color: red; font-weight: bold;")
            except: pass

    def _on_mode_change(self):
        mode = self.mode_combo.currentData()
        self.message_input.setEnabled(mode in ("text", "file_text"))
        self.file_btn.setEnabled(mode in ("file", "file_text"))
        self.file_label.setEnabled(mode in ("file", "file_text"))

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo", "", "Todos os arquivos (*.*)")
        if path:
            self.file_path = path
            self.file_label.setText(os.path.basename(path))

    def _send_now(self):
        target = self.target_input.text().strip()
        mode = self.mode_combo.currentData()
        message = self.message_input.toPlainText().strip()
        file_path = self.file_path

        if not self._validate_fields(target, mode, message, file_path): return

        self.send_now_btn.setEnabled(False)
        self.schedule_btn.setEnabled(False)

        try:
            # 1. Executa o envio via Selenium
            automation.executar_envio(
                userdir=PROFILE_DIR, 
                target=target, 
                mode=mode,
                message=message if mode in ("text", "file_text") else None,
                file_path=file_path if mode in ("file", "file_text") else None,
                logger=lambda m: print(f"[LOG] {m}")
            )
            
            # 2. Incrementa o contador MANUALMENTE aqui para garantir a sincronia
            # Isso garante que a UI sabe exatamente quando o arquivo mudou
            contador_execucao(incrementar=True)
            
            QMessageBox.information(self, "Sucesso", "Mensagem enviada!")
            self._clear_form()
            import time
            time.sleep(0.5)
            
            # 3. Atualiza a tela
            self.atualizar_contador_exibicao()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha no envio:\n{str(e)}")
        finally:
            self.send_now_btn.setEnabled(True)
            self.schedule_btn.setEnabled(True)

    def _schedule_task(self):
        target = self.target_input.text().strip()
        mode = self.mode_combo.currentData()
        message = self.message_input.toPlainText().strip()
        file_path = self.file_path
        
        qdt = self.datetime_picker.dateTime()
        schedule_time = qdt.toString("HH:mm")
        schedule_date = qdt.toString("dd/MM/yyyy")

        if not self._validate_fields(target, mode, message, file_path): return

        self.send_now_btn.setEnabled(False)
        self.schedule_btn.setEnabled(False)

        try:
            dt_python = datetime(
                qdt.date().year(), qdt.date().month(), qdt.date().day(),
                qdt.time().hour(), qdt.time().minute()
            )
            
            task_id = db.adicionar(
                task_name=f"WA_Task_{int(QDateTime.currentMSecsSinceEpoch())}",
                target=target,
                mode=mode,
                message=message if mode in ("text", "file_text") else None,
                file_path=file_path if mode in ("file", "file_text") else None,
                scheduled_time=dt_python
            )

            json_config = {
                "task_id": str(task_id),
                "task_name": f"WA_Task_{task_id}",
                "target": target,
                "mode": mode,
                "message": message,
                "file_path": file_path or "",
                "schedule_time": schedule_time
            }
            create_task_bat(task_id, json_config["task_name"], json_config)
            sucesso, msg = create_windows_task(task_id, json_config["task_name"], schedule_time, schedule_date)

            if sucesso:
                QMessageBox.information(self, "Sucesso", f"✓ Agendado para {schedule_date} às {schedule_time}")
                self._clear_form()
            else:
                raise Exception(msg)

        except Exception as e:
            QMessageBox.critical(self, "Erro no Agendamento", str(e))
        finally:
            self.send_now_btn.setEnabled(True)
            self.schedule_btn.setEnabled(True)

    def _validate_fields(self, target, mode, message, file_path):
        if not target:
            QMessageBox.warning(self, "Campo obrigatório", "Informe o contato.")
            return False
        if mode in ("text", "file_text") and not message:
            QMessageBox.warning(self, "Campo obrigatório", "Digite a mensagem.")
            return False
        if mode in ("file", "file_text") and not file_path:
            QMessageBox.warning(self, "Campo obrigatório", "Selecione o arquivo.")
            return False
        return True

    def _clear_form(self):
        self.target_input.clear()
        self.message_input.clear()
        self.file_label.setText("Nenhum arquivo selecionado")
        self.file_path = None
        self.datetime_picker.setDateTime(QDateTime.currentDateTime().addSecs(300))