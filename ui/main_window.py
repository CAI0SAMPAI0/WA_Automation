import os
import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
    QMessageBox, QComboBox, QDateTimeEdit
)
from PySide6.QtCore import QDateTime
from PySide6.QtGui import QIcon

# CORREÇÃO: Importar do módulo correto
from core.scheduler import create_windows_task
from core.db import db
from core import automation

def _get_icon_path():
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, "resources", "Taty_s-English-Logo.ico")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study Practices - WhatsApp Automation")
        self.setMinimumSize(500, 650)

        self.file_path = None
        icon_path = _get_icon_path()
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()

        # ===== CONTATO =====
        layout.addWidget(QLabel("Contato / Número:"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Ex: 5511999999999 ou Nome do Contato")
        layout.addWidget(self.target_input)

        # ===== MODO =====
        layout.addWidget(QLabel("Modo de envio:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Somente texto", "text")
        self.mode_combo.addItem("Somente arquivo", "file")
        self.mode_combo.addItem("Arquivo + texto", "file_text")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_change)
        layout.addWidget(self.mode_combo)

        # ===== MENSAGEM =====
        layout.addWidget(QLabel("Mensagem:"))
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Digite sua mensagem aqui...")
        layout.addWidget(self.message_input)

        # ===== ARQUIVO =====
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Nenhum arquivo selecionado")
        self.file_btn = QPushButton("Selecionar Arquivo")
        self.file_btn.clicked.connect(self._select_file)
        file_layout.addWidget(self.file_btn)
        file_layout.addWidget(self.file_label)
        layout.addLayout(file_layout)

        # ===== DATA/HORA =====
        layout.addWidget(QLabel("Data e hora do envio:"))
        self.datetime_picker = QDateTimeEdit()
        self.datetime_picker.setCalendarPopup(True)
        self.datetime_picker.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.datetime_picker.setMinimumDateTime(QDateTime.currentDateTime())
        self.datetime_picker.setDateTime(QDateTime.currentDateTime().addSecs(300))
        layout.addWidget(self.datetime_picker)

        # ===== BOTÕES =====
        buttons_layout = QHBoxLayout()

        self.send_now_btn = QPushButton("Enviar agora")
        self.send_now_btn.clicked.connect(self._send_now)
        buttons_layout.addWidget(self.send_now_btn)

        self.schedule_btn = QPushButton("Agendar")
        self.schedule_btn.clicked.connect(self._schedule_task)
        buttons_layout.addWidget(self.schedule_btn)

        layout.addLayout(buttons_layout)

        # ===== INFORMAÇÕES =====
        info_label = QLabel(
            "💡 Dica: Use 'Enviar agora' para testar antes de agendar.\n"
            "O agendamento executará automaticamente na data/hora definida."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 11px; padding: 10px;")
        layout.addWidget(info_label)

        central.setLayout(layout)
        self._on_mode_change()

    def _on_mode_change(self):
        mode = self.mode_combo.currentData()

        if mode == "text":
            self.message_input.setEnabled(True)
            self.file_btn.setEnabled(False)
            self.file_label.setEnabled(False)

        elif mode == "file":
            self.message_input.setEnabled(False)
            self.file_btn.setEnabled(True)
            self.file_label.setEnabled(True)

        elif mode == "file_text":
            self.message_input.setEnabled(True)
            self.file_btn.setEnabled(True)
            self.file_label.setEnabled(True)

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Selecionar arquivo",
            "",
            "Todos os arquivos (*.*)"
        )
        if path:
            self.file_path = path
            self.file_label.setText(os.path.basename(path))

    def _send_now(self):
        target = self.target_input.text().strip()
        mode = self.mode_combo.currentData()
        message = self.message_input.toPlainText().strip()
        file_path = self.file_path

        if not self._validate_fields(target, mode, message, file_path):
            return

        self.send_now_btn.setEnabled(False)
        self.schedule_btn.setEnabled(False)

        def logger(msg):
            print(f"[AUTOMAÇÃO] {msg}")

        try:
            automation.executar_envio(
                userdir=None,
                target=target,
                mode=mode,
                message=message if mode in ("text", "file_text") else None,
                file_path=file_path if mode in ("file", "file_text") else None,
                logger=logger
            )
            
            QMessageBox.information(
                self, 
                "Sucesso", 
                "Mensagem enviada com sucesso!"
            )
            self._clear_form()
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Erro na automação", 
                f"Ocorreu um erro ao enviar:\n\n{str(e)}"
            )
        finally:
            self.send_now_btn.setEnabled(True)
            self.schedule_btn.setEnabled(True)

    def _schedule_task(self):
        target = self.target_input.text().strip()
        mode = self.mode_combo.currentData()
        message = self.message_input.toPlainText().strip()
        file_path = self.file_path
        
        # Formato correto da data/hora
        scheduled_time = self.datetime_picker.dateTime().toString("yyyy-MM-dd HH:mm:ss")

        if not self._validate_fields(target, mode, message, file_path):
            return

        self.send_now_btn.setEnabled(False)
        self.schedule_btn.setEnabled(False)

        try:
            # 1. Adiciona no banco de dados
            # Converte QDateTime para datetime Python
            dt_python = datetime(
                self.datetime_picker.dateTime().date().year(),
                self.datetime_picker.dateTime().date().month(),
                self.datetime_picker.dateTime().date().day(),
                self.datetime_picker.dateTime().time().hour(),
                self.datetime_picker.dateTime().time().minute(),
                self.datetime_picker.dateTime().time().second()
            )
            
            task_id = db.adicionar(
                task_name=f"WA_Task_{int(QDateTime.currentMSecsSinceEpoch())}",
                target=target,
                mode=mode,
                message=message if mode in ("text", "file_text") else None,
                file_path=file_path if mode in ("file", "file_text") else None,
                scheduled_time=dt_python
            )

            if task_id == -1:
                raise Exception("Erro ao criar registro no banco de dados")

            # 2. Cria tarefa no Windows Task Scheduler
            create_windows_task(
                task_id=task_id,
                scheduled_time=scheduled_time,
                target=target,
                mode=mode,
                message=message if mode in ("text", "file_text") else None,
                file_path=file_path if mode in ("file", "file_text") else None
            )

            # 3. Sucesso!
            QMessageBox.information(
                self,
                "Agendamento criado",
                f"✓ Tarefa #{task_id} agendada com sucesso!\n\n"
                f"Data/Hora: {self.datetime_picker.dateTime().toString('dd/MM/yyyy HH:mm')}\n"
                f"Contato: {target}\n"
                f"Modo: {mode}\n\n"
                f"A automação será executada automaticamente."
            )

            self._clear_form()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro no Agendamento",
                f"Falha ao criar agendamento:\n\n{str(e)}\n\n"
                f"Verifique:\n"
                f"- Permissões de administrador\n"
                f"- Task Scheduler está ativo\n"
                f"- Caminho do executável está correto"
            )
        finally:
            self.send_now_btn.setEnabled(True)
            self.schedule_btn.setEnabled(True)

    def _validate_fields(self, target, mode, message, file_path):
        if not target:
            QMessageBox.warning(
                self, 
                "Campo obrigatório", 
                "Por favor, informe o contato ou número."
            )
            return False

        if mode == "text" and not message:
            QMessageBox.warning(
                self, 
                "Campo obrigatório", 
                "Por favor, digite uma mensagem."
            )
            return False

        if mode == "file" and not file_path:
            QMessageBox.warning(
                self, 
                "Campo obrigatório", 
                "Por favor, selecione um arquivo."
            )
            return False

        if mode == "file_text":
            if not message:
                QMessageBox.warning(
                    self, 
                    "Campo obrigatório", 
                    "Por favor, digite uma mensagem."
                )
                return False
            if not file_path:
                QMessageBox.warning(
                    self, 
                    "Campo obrigatório", 
                    "Por favor, selecione um arquivo."
                )
                return False

        if file_path and not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                "Arquivo não encontrado",
                f"O arquivo selecionado não existe:\n{file_path}"
            )
            return False

        return True

    def _clear_form(self):
        self.target_input.clear()
        self.message_input.clear()
        self.file_label.setText("Nenhum arquivo selecionado")
        self.file_path = None
        self.datetime_picker.setDateTime(QDateTime.currentDateTime().addSecs(300))