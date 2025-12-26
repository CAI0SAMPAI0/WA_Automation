import sys
import os
import traceback
import datetime
import time
from core import automation

# =========================
# BASE DIR (compatível com EXE)
# =========================
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# =========================
# IMPORTS INTERNOS
# =========================
from data.database import (
    get_task_by_id,
    update_status,
    increment_attempts,
    update_last_error
)

from core.logger import get_logger
from core.automation import executar_envio

# =========================
# CONFIG
# =========================
DEFAULT_UPLOAD_DELAY = 2.5  # segundos extras para arquivos grandes

# =========================
# CHROME PROFILE FIXO
# =========================
def get_user_chrome_profile_dir():
    base_dir = os.environ.get("LOCALAPPDATA")

    if not base_dir:
        base_dir = os.path.expanduser("~")

    profile = os.path.join(
        base_dir,
        "WhatsAppAutomation",
        "perfil_bot_whatsapp"
    )

    os.makedirs(profile, exist_ok=True)
    return profile



# =========================
# MAIN
# =========================
def main(task_id: str):
    # ===== LOG =====
    log_date = datetime.datetime.now().strftime("%Y-%m-%d")
    LOG_DIR = os.path.join(BASE_DIR, "logs", log_date)
    os.makedirs(LOG_DIR, exist_ok=True)

    log_file = os.path.join(LOG_DIR, f"task_{task_id}.log")
    logger = get_logger(task_id, log_file)

    logger.info("=" * 70)
    logger.info(f"EXECUTOR INICIADO | task_id={task_id}")
    logger.info(f"BASE_DIR={BASE_DIR}")

    try:
        # ===== SET RUNNING =====
        update_status(task_id, "RUNNING")

        # ===== LOAD TASK =====
        task = get_task_by_id(task_id)
        if not task:
            raise RuntimeError(f"Tarefa {task_id} não encontrada")

        logger.info(
            f"TASK | target={task['target']} | "
            f"mode={task['mode']} | "
            f"file={task['file_path']}"
        )

        # ===== CHROME PROFILE =====
        user_profile_dir = get_user_chrome_profile_dir()
        logger.info(f"Chrome profile: {user_profile_dir}")

        # ===== DELAY EXTRA =====
        time.sleep(DEFAULT_UPLOAD_DELAY)

        # ===== EXECUÇÃO =====
        executar_envio(
            userdir=user_profile_dir,
            target=task["target"],
            mode=task["mode"],
            message=task.get("message"),
            file_path=task.get("file_path"),
            logger=logger,
            modo_execucao='auto'
        )

        # ===== FINALIZA =====
        update_status(task_id, "COMPLETED")
        logger.info("Tarefa concluída com sucesso")
        logger.info("=" * 70)

        sys.exit(0)

    except Exception as e:
        logger.error("ERRO DURANTE EXECUÇÃO")
        logger.error(traceback.format_exc())

        increment_attempts(task_id)
        update_last_error(task_id, str(e))
        update_status(task_id, "FAILED")

        sys.exit(1)


# =========================
# ENTRYPOINT
# =========================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: executor.exe <task_id>")
        sys.exit(2)

    main(sys.argv[1])
