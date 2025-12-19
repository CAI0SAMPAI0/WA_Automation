"""
Sistema de agendamento usando Windows Task Scheduler.

Fluxo:
1. Criar arquivo JSON com instruções de envio
2. Criar tarefa no Windows Task Scheduler
3. Na hora agendada, Task Scheduler executa: app.py --auto caminho.json
4. app.py lê o JSON e executa a automação
"""

import subprocess
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


# =============================
# CONFIGURAÇÃO DE CAMINHOS
# =============================
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.absolute()

TASKS_DIR = BASE_DIR / "scheduled_tasks"
TASKS_DIR.mkdir(parents=True, exist_ok=True)


def create_task_json(
    task_id: int,
    target: str,
    mode: str,
    message: Optional[str] = None,
    file_path: Optional[str] = None
) -> Path:
    """
    Cria arquivo JSON com instruções para execução automática.
    IMPORTANTE: O formato deve corresponder ao esperado por app.py
    """
    json_filename = f"task_{task_id}.json"
    json_path = TASKS_DIR / json_filename
    
    # FORMATO CORRETO esperado por app.py (linha 62-65)
    task_data = {
        "mode": mode,
        "target": target,
        "text": message or "",  # app.py espera "text", não "message"
        "file": file_path or ""  # app.py espera "file", não "file_path"
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(task_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ JSON criado: {json_path}")
    print(f"  Conteúdo: {task_data}")
    return json_path


def create_windows_task(
    task_id: int,
    scheduled_time: str,
    target: str,
    mode: str,
    message: Optional[str] = None,
    file_path: Optional[str] = None
) -> bool:
    """
    Cria tarefa agendada no Windows Task Scheduler.
    """
    
    # =============================
    # 1. CRIA JSON DE INSTRUÇÃO
    # =============================
    json_path = create_task_json(task_id, target, mode, message, file_path)
    
    # =============================
    # 2. FORMATA DATA/HORA
    # =============================
    dt = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
    run_date = dt.strftime("%d/%m/%Y")
    run_time = dt.strftime("%H:%M")
    
    # =============================
    # 3. DETERMINA COMANDO
    # =============================
    if getattr(sys, 'frozen', False):
        # EXECUTÁVEL COMPILADO
        exe_path = sys.executable
        # Garante que o caminho está entre aspas para lidar com espaços
        task_command = f'"{exe_path}" --auto "{json_path}"'
    else:
        # MODO DESENVOLVIMENTO
        python_exe = sys.executable
        app_path = BASE_DIR / "app.py"
        task_command = f'"{python_exe}" "{app_path}" --auto "{json_path}"'
    
    task_name = f"StudyPractices_WA_{task_id}"
    
    # =============================
    # 4. MONTA COMANDO SCHTASKS
    # =============================
    schtasks_command = [
        "schtasks",
        "/Create",
        "/F",
        "/SC", "ONCE",
        "/SD", run_date,
        "/ST", run_time,
        "/TN", task_name,
        "/TR", task_command,
        "/RL", "HIGHEST"  # Necessário para automação
    ]
    
    # =============================
    # 5. DEBUG: MOSTRA O QUE SERÁ EXECUTADO
    # =============================
    print(f"\n{'='*70}")
    print(f"CRIANDO TAREFA NO WINDOWS TASK SCHEDULER")
    print(f"{'='*70}")
    print(f"Nome da tarefa: {task_name}")
    print(f"Data/Hora: {run_date} {run_time}")
    print(f"Comando que será executado:")
    print(f"  {task_command}")
    print(f"JSON de instruções: {json_path}")
    print(f"{'='*70}\n")
    
    # =============================
    # 6. EXECUTA
    # =============================
    try:
        result = subprocess.run(
            schtasks_command,
            check=True,
            shell=False,
            capture_output=True,
            text=True,
            encoding='latin-1'
        )
        
        print("✓ Tarefa criada com sucesso no Task Scheduler!")
        if result.stdout:
            print(f"Output: {result.stdout}")
        
        # VERIFICAÇÃO: Tenta confirmar que a tarefa foi criada
        verificacao = verificar_status_tarefa(task_id)
        if verificacao:
            print(f"✓ Tarefa verificada. Status: {verificacao}")
        else:
            print("⚠️  Aviso: Não foi possível verificar a tarefa")
        
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Erro ao criar tarefa no Windows:\n"
        error_msg += f"Código: {e.returncode}\n"
        if e.stdout:
            error_msg += f"Saída: {e.stdout}\n"
        if e.stderr:
            error_msg += f"Erro: {e.stderr}"
        
        print(f"✗ {error_msg}")
        raise Exception(error_msg)
    except Exception as e:
        print(f"✗ Erro inesperado: {e}")
        raise


def delete_windows_task(task_id: int) -> bool:
    """Remove tarefa do Windows Task Scheduler."""
    task_name = f"StudyPractices_WA_{task_id}"
    
    command = [
        "schtasks",
        "/Delete",
        "/TN", task_name,
        "/F"
    ]
    
    try:
        subprocess.run(
            command,
            check=True,
            shell=False,
            capture_output=True,
            text=True,
            encoding='latin-1'
        )
        
        print(f"✓ Tarefa removida: {task_name}")
        
        # Remove JSON
        json_path = TASKS_DIR / f"task_{task_id}.json"
        if json_path.exists():
            json_path.unlink()
            print(f"✓ JSON removido: {json_path}")
        
        return True
        
    except subprocess.CalledProcessError:
        print(f"⚠️  Tarefa {task_name} não encontrada")
        return False
    except Exception as e:
        print(f"⚠️  Erro ao deletar: {e}")
        return False


def verificar_status_tarefa(task_id: int) -> Optional[str]:
    """Verifica status de uma tarefa específica."""
    task_name = f"StudyPractices_WA_{task_id}"
    
    command = [
        "schtasks",
        "/Query",
        "/TN", task_name,
        "/FO", "LIST",
        "/V"
    ]
    
    try:
        result = subprocess.run(
            command,
            check=True,
            shell=False,
            capture_output=True,
            text=True,
            encoding='latin-1'
        )
        
        for line in result.stdout.split('\n'):
            if "Status:" in line or "Estado:" in line:
                return line.split(":")[-1].strip()
        
        return None
        
    except subprocess.CalledProcessError:
        return None
    except Exception:
        return None


def executar_tarefa_agora(task_id: int) -> bool:
    """
    Força execução imediata de uma tarefa (útil para testes).
    """
    task_name = f"StudyPractices_WA_{task_id}"
    
    command = [
        "schtasks",
        "/Run",
        "/TN", task_name
    ]
    
    try:
        result = subprocess.run(
            command,
            check=True,
            shell=False,
            capture_output=True,
            text=True,
            encoding='latin-1'
        )
        
        print(f"✓ Tarefa {task_name} executada manualmente")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Erro ao executar tarefa: {e.stderr if e.stderr else 'Desconhecido'}")
        return False


# =============================
# DIAGNÓSTICO
# =============================
def diagnosticar_sistema():
    """
    Executa diagnóstico completo do sistema de agendamento.
    """
    print("\n" + "="*70)
    print("DIAGNÓSTICO DO SISTEMA DE AGENDAMENTO")
    print("="*70 + "\n")
    
    # 1. Verifica caminhos
    print("1. CAMINHOS:")
    print(f"   BASE_DIR: {BASE_DIR}")
    print(f"   TASKS_DIR: {TASKS_DIR}")
    print(f"   Executável: {sys.executable}")
    print(f"   Frozen: {getattr(sys, 'frozen', False)}")
    
    # 2. Verifica se consegue criar tarefa de teste
    print("\n2. TESTE DE CRIAÇÃO:")
    test_time = (datetime.now() + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    test_id = 99999
    
    try:
        create_windows_task(
            task_id=test_id,
            scheduled_time=test_time,
            target="5511999999999",
            mode="text",
            message="Teste diagnóstico"
        )
        print("   ✓ Tarefa de teste criada com sucesso")
        
        # Verifica se foi criada
        status = verificar_status_tarefa(test_id)
        print(f"   Status da tarefa: {status}")
        
        # Remove tarefa de teste
        delete_windows_task(test_id)
        
    except Exception as e:
        print(f"   ✗ Erro ao criar tarefa de teste: {e}")
    
    # 3. Lista tarefas existentes
    print("\n3. TAREFAS EXISTENTES:")
    command = ["schtasks", "/Query", "/FO", "LIST"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='latin-1')
        tasks = [line for line in result.stdout.split('\n') if 'StudyPractices_WA_' in line]
        if tasks:
            for task in tasks:
                print(f"   - {task.strip()}")
        else:
            print("   Nenhuma tarefa encontrada")
    except Exception as e:
        print(f"   ✗ Erro ao listar tarefas: {e}")
    
    print("\n" + "="*70)


# =============================
# TESTES
# =============================
if __name__ == "__main__":
    from datetime import timedelta
    
    print("Escolha uma opção:")
    print("1. Executar diagnóstico")
    print("2. Criar tarefa de teste")
    
    opcao = input("\nOpção: ").strip()
    
    if opcao == "1":
        diagnosticar_sistema()
    elif opcao == "2":
        test_time = (datetime.now() + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
        test_id = int(datetime.now().timestamp())
        
        create_windows_task(
            task_id=test_id,
            scheduled_time=test_time,
            target="5511999999999",
            mode="text",
            message="Mensagem de teste"
        )
        
        print(f"\n✓ Tarefa criada! ID: {test_id}")
        print(f"  Executará em: {test_time}")
        print(f"  Para forçar execução agora: executar_tarefa_agora({test_id})")