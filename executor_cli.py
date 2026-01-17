# executor_cli.py
import sys
from core.db import db
from core import automation

def run_task(task_id):
    try:
        # 1. Busca dados no banco
        task = db.obter_por_id(task_id) 
        if not task: return

        db.atualizar_status(task_id, "processando")

        # 2. Executa a automação
        automation.executar_envio(
            userdir=task['userdir'], 
            target=task['target'],
            mode=task['mode'],
            message=task['message'],
            file_path=task['file_path'],
            modo_execucao='background' 
        )

        # 3. Sucesso
        db.atualizar_status(task_id, "sucesso")
        
    except Exception as e:
        db.registrar_erro(task_id, str(e))
        db.atualizar_status(task_id, "falha")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_task(sys.argv[1])