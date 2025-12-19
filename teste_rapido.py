"""
Teste rápido do sistema de agendamento.
Execute este arquivo para testar se tudo está funcionando.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Adiciona o diretório raiz ao path
BASE_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(BASE_DIR))

print("\n" + "="*70)
print("TESTE RÁPIDO - SISTEMA DE AGENDAMENTO")
print("="*70 + "\n")

# ============================================================================
# TESTE 1: Importações
# ============================================================================
print("1. Verificando importações...")

try:
    from core.scheduler import create_windows_task, delete_windows_task
    print("✓ core.scheduler importado")
except ImportError as e:
    print(f"✗ Erro ao importar core.scheduler: {e}")
    input("\nPressione Enter para sair...")
    sys.exit(1)

try:
    from core.db import db
    print("✓ core.db importado")
except ImportError as e:
    print(f"✗ Erro ao importar core.db: {e}")
    input("\nPressione Enter para sair...")
    sys.exit(1)

# ============================================================================
# TESTE 2: Banco de Dados
# ============================================================================
print("\n2. Testando banco de dados...")

try:
    # Tenta adicionar um registro de teste
    test_time = datetime.now() + timedelta(hours=1)
    test_id = db.adicionar(
        task_name=f"TEST_{int(datetime.now().timestamp())}",
        target="5511999999999",
        mode="text",
        message="Teste rápido",
        scheduled_time=test_time
    )
    
    if test_id > 0:
        print(f"✓ Banco funcionando (ID: {test_id})")
        db.deletar(test_id)
        print("✓ Registro de teste removido")
    else:
        print("✗ Erro ao adicionar no banco")
        
except Exception as e:
    print(f"✗ Erro no banco: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TESTE 3: Task Scheduler
# ============================================================================
print("\n3. Testando Windows Task Scheduler...")

try:
    import subprocess
    
    result = subprocess.run(
        ["schtasks", "/Query"],
        capture_output=True,
        text=True,
        encoding='latin-1'
    )
    
    if result.returncode == 0:
        print("✓ Task Scheduler acessível")
    else:
        print("✗ Erro ao acessar Task Scheduler")
        
except Exception as e:
    print(f"✗ Erro: {e}")

# ============================================================================
# TESTE 4: Criar e remover tarefa de teste
# ============================================================================
print("\n4. Criando tarefa de teste...")

try:
    test_time_str = (datetime.now() + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    test_task_id = 99999
    
    print(f"   Criando tarefa ID {test_task_id} para {test_time_str}")
    
    create_windows_task(
        task_id=test_task_id,
        scheduled_time=test_time_str,
        target="5511999999999",
        mode="text",
        message="Teste rápido - pode ignorar"
    )
    
    print("✓ Tarefa criada com sucesso")
    
    # Aguarda 2 segundos
    import time
    time.sleep(2)
    
    # Remove a tarefa
    print("\n   Removendo tarefa de teste...")
    if delete_windows_task(test_task_id):
        print("✓ Tarefa removida com sucesso")
    else:
        print("⚠️  Não foi possível remover a tarefa")
    
except Exception as e:
    print(f"✗ Erro: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# RESULTADO FINAL
# ============================================================================
print("\n" + "="*70)
print("TESTE CONCLUÍDO")
print("="*70)

print("\n✓ Se todos os testes passaram, o sistema está funcionando!")
print("✓ Você pode compilar o executável com: pyinstaller app.spec --clean")
print("✓ Para testar o app gráfico, execute: python app.py")

print("\n⚠️  Se algum teste falhou:")
print("   1. Verifique se está executando como Administrador")
print("   2. Verifique se Task Scheduler está ativo")
print("   3. Execute: pip install -r requirements.txt")

input("\nPressione Enter para sair...")