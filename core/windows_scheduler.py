import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def get_app_base_path():
    """Retorna o caminho base do app, funcionando tanto como .py quanto .exe"""
    if getattr(sys, 'frozen', False):
        # Se for executável, aponta para a pasta onde o .exe está
        return Path(sys.executable).parent.absolute()
    else:
        # Se for script, aponta para a raiz do projeto (meu-teste)
        return Path(__file__).parent.parent.absolute()

def create_task_bat(task_id, task_name, json_config):
    """Cria um arquivo .bat para ser executado pelo Agendador do Windows"""
    app_path = get_app_base_path()
    scheduled_tasks_dir = app_path / "scheduled_tasks"
    scheduled_tasks_dir.mkdir(exist_ok=True)
    
    json_filename = f"task_{task_id}.json"
    bat_filename = f"task_{task_id}.bat"
    
    json_path = scheduled_tasks_dir / json_filename
    bat_path = scheduled_tasks_dir / bat_filename
    
    # 1. Salva a configuração da tarefa em JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_config, f, indent=2, ensure_ascii=False)
    
    # 2. Cria o arquivo .bat dinâmico com aspas duplas em todos os caminhos
    if getattr(sys, 'frozen', False):
        exe_path = app_path / "Study Practices.exe" 
        bat_content = f"""@echo off
chcp 65001 >nul
cd /d "{app_path}"
"{exe_path}" --auto "{json_path}" --task_id {task_id}
"""
    else:
        python_path = sys.executable
        script_path = app_path / "app.py"
        bat_content = f"""@echo off
chcp 65001 >nul
cd /d "{app_path}"
"{python_path}" "{script_path}" --auto "{json_path}" --task_id {task_id}
"""
    
    # Grava o BAT com UTF-8 para suportar o comando chcp 65001
    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(bat_content)
    
    return str(bat_path)

def create_windows_task(task_id, task_name, schedule_time, schedule_date=None):
    """
    Cria uma tarefa no Agendador do Windows.
    Retorna (True, "Mensagem") para a interface conseguir 'desempacotar'.
    """
    app_path = get_app_base_path()
    bat_path = app_path / "scheduled_tasks" / f"task_{task_id}.bat"
    
    if len(schedule_time.split(':')) > 2:
        schedule_time = ':'.join(schedule_time.split(':')[:2])
    
    if not schedule_date:
        schedule_date = datetime.now().strftime("%d/%m/%Y")

    # Comando com aspas para o seu caminho 'CAIO MAXIMUS' e privilégio administrativo
    cmd = f'schtasks /create /tn "AutoMessage_{task_id}" /tr "\\"{bat_path}\\"" /sc once /st {schedule_time} /sd {schedule_date} /rl highest /f'    
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        # Retorna False e o erro para a interface
        return False, result.stderr
    
    # Retorna True e sucesso para a interface
    return True, "Agendamento criado com sucesso!"



def delete_windows_task(task_id):
    """Remove a tarefa do agendador usando o padrão de nome correto"""
    task_name = f"AutoMessage_{task_id}"
    cmd = f'schtasks /delete /tn "{task_name}" /f'
    subprocess.run(cmd, shell=True, capture_output=True)