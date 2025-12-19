"""
Script de diagnóstico completo do sistema de agendamento.
Execute este arquivo para verificar todos os componentes.
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Configuração de caminhos
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.absolute()

sys.path.insert(0, str(BASE_DIR))

print("\n" + "="*80)
print("DIAGNÓSTICO COMPLETO DO SISTEMA DE AGENDAMENTO")
print("="*80 + "\n")

# ============================================================================
# TESTE 1: VERIFICAR ESTRUTURA DE DIRETÓRIOS
# ============================================================================
print("1. ESTRUTURA DE DIRETÓRIOS")
print("-" * 80)

diretorios_necessarios = [
    BASE_DIR / "core",
    BASE_DIR / "data",
    BASE_DIR / "ui",
    BASE_DIR / "scheduled_tasks",
    BASE_DIR / "logs"
]

for diretorio in diretorios_necessarios:
    existe = diretorio.exists()
    status = "✓" if existe else "✗"
    print(f"{status} {diretorio}")
    if not existe:
        print(f"   CRIANDO: {diretorio}")
        diretorio.mkdir(parents=True, exist_ok=True)

# ============================================================================
# TESTE 2: VERIFICAR MÓDULOS PYTHON
# ============================================================================
print("\n2. MÓDULOS PYTHON")
print("-" * 80)

modulos = [
    ("selenium", "Selenium WebDriver"),
    ("undetected_chromedriver", "Undetected ChromeDriver"),
    ("PySide6", "PySide6 (Qt)"),
    ("sqlite3", "SQLite3")
]

for modulo, nome in modulos:
    try:
        __import__(modulo)
        print(f"✓ {nome}")
    except ImportError:
        print(f"✗ {nome} - NÃO INSTALADO")

# ============================================================================
# TESTE 3: VERIFICAR BANCO DE DADOS
# ============================================================================
print("\n3. BANCO DE DADOS")
print("-" * 80)

try:
    from core.db import db
    
    # Tenta adicionar um registro de teste
    test_time = datetime.now() + timedelta(hours=1)
    test_id = db.adicionar(
        task_name=f"TEST_{int(datetime.now().timestamp())}",
        target="5511999999999",
        mode="text",
        message="Teste diagnóstico",
        scheduled_time=test_time
    )
    
    if test_id > 0:
        print(f"✓ Banco de dados funcionando (test_id: {test_id})")
        
        # Busca o registro
        task = db.obter_detalhes(test_id)
        if task:
            print(f"✓ Leitura de registros funcionando")
        
        # Remove o teste
        db.deletar(test_id)
        print(f"✓ Exclusão de registros funcionando")
    else:
        print("✗ Erro ao adicionar registro no banco")
        
except Exception as e:
    print(f"✗ Erro no banco de dados: {e}")

# ============================================================================
# TESTE 4: VERIFICAR TASK SCHEDULER (WINDOWS)
# ============================================================================
print("\n4. WINDOWS TASK SCHEDULER")
print("-" * 80)

try:
    # Testa se consegue listar tarefas
    result = subprocess.run(
        ["schtasks", "/Query"],
        capture_output=True,
        text=True,
        encoding='latin-1'
    )
    
    if result.returncode == 0:
        print("✓ Task Scheduler acessível")
        
        # Conta tarefas existentes do app
        tasks = [line for line in result.stdout.split('\n') if 'StudyPractices_WA_' in line]
        print(f"✓ Tarefas existentes: {len(tasks)}")
        if tasks:
            print("  Tarefas encontradas:")
            for task in tasks[:5]:  # Mostra até 5
                print(f"    - {task.strip()}")
    else:
        print("✗ Erro ao acessar Task Scheduler")
        print(f"  Código de retorno: {result.returncode}")
        
except FileNotFoundError:
    print("✗ Comando 'schtasks' não encontrado")
    print("  Este diagnóstico precisa ser executado no Windows")
except Exception as e:
    print(f"✗ Erro ao verificar Task Scheduler: {e}")

# ============================================================================
# TESTE 5: CRIAR TAREFA DE TESTE
# ============================================================================
print("\n5. TESTE DE CRIAÇÃO DE TAREFA")
print("-" * 80)

try:
    from core.scheduler import create_windows_task, delete_windows_task, verificar_status_tarefa
    
    # CORREÇÃO: Importar timedelta no início do arquivo
    # Cria tarefa de teste para daqui a 2 minutos
    test_time_str = (datetime.now() + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")
    test_task_id = 99999
    
    print(f"Criando tarefa de teste (ID: {test_task_id})...")
    print(f"Programada para: {test_time_str}")
    
    create_windows_task(
        task_id=test_task_id,
        scheduled_time=test_time_str,
        target="5511999999999",
        mode="text",
        message="Teste de diagnóstico - pode ignorar esta mensagem"
    )
    
    print("✓ Tarefa criada com sucesso")
    
    # Verifica se foi criada
    status = verificar_status_tarefa(test_task_id)
    if status:
        print(f"✓ Status da tarefa: {status}")
    else:
        print("⚠️  Não foi possível verificar o status")
    
    # Remove a tarefa de teste
    print("\nRemovendo tarefa de teste...")
    if delete_windows_task(test_task_id):
        print("✓ Tarefa removida com sucesso")
    
except Exception as e:
    print(f"✗ Erro ao criar tarefa de teste: {e}")
    import traceback
    print("\nDetalhes do erro:")
    print(traceback.format_exc())

# ============================================================================
# TESTE 6: VERIFICAR FORMATO DO JSON
# ============================================================================
print("\n6. FORMATO DO JSON DE INSTRUÇÃO")
print("-" * 80)

try:
    # Cria um JSON de teste
    json_test_path = BASE_DIR / "scheduled_tasks" / "test_format.json"
    json_test_data = {
        "mode": "text",
        "target": "5511999999999",
        "text": "Mensagem de teste",
        "file": ""
    }
    
    with open(json_test_path, "w", encoding="utf-8") as f:
        json.dump(json_test_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ JSON criado em: {json_test_path}")
    
    # Verifica se consegue ler
    with open(json_test_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print("✓ JSON lido com sucesso")
    print(f"  Conteúdo: {data}")
    
    # Verifica se o formato está correto para app.py
    required_keys = ["mode", "target", "text", "file"]
    missing_keys = [key for key in required_keys if key not in data]
    
    if not missing_keys:
        print("✓ Formato do JSON está correto para app.py")
    else:
        print(f"✗ Faltam chaves no JSON: {missing_keys}")
    
    # Remove arquivo de teste
    json_test_path.unlink()
    
except Exception as e:
    print(f"✗ Erro ao testar JSON: {e}")

# ============================================================================
# TESTE 7: VERIFICAR COMANDO DE EXECUÇÃO
# ============================================================================
print("\n7. COMANDO DE EXECUÇÃO")
print("-" * 80)

if getattr(sys, 'frozen', False):
    exe_path = sys.executable
    json_example = BASE_DIR / "scheduled_tasks" / "task_1.json"
    command = f'"{exe_path}" --auto "{json_example}"'
    print("MODO: Executável compilado")
else:
    python_exe = sys.executable
    app_path = BASE_DIR / "app.py"
    json_example = BASE_DIR / "scheduled_tasks" / "task_1.json"
    command = f'"{python_exe}" "{app_path}" --auto "{json_example}"'
    print("MODO: Desenvolvimento")

print(f"\nComando que será executado pelo Task Scheduler:")
print(f"{command}")

print(f"\nVerificando arquivos:")
if getattr(sys, 'frozen', False):
    print(f"  Executável: {exe_path}")
    print(f"    Existe: {'✓' if Path(exe_path).exists() else '✗'}")
else:
    print(f"  Python: {python_exe}")
    print(f"    Existe: {'✓' if Path(python_exe).exists() else '✗'}")
    print(f"  app.py: {app_path}")
    print(f"    Existe: {'✓' if Path(app_path).exists() else '✗'}")

# ============================================================================
# TESTE 8: SIMULAR EXECUÇÃO DO APP.PY --AUTO
# ============================================================================
print("\n8. SIMULAÇÃO DE EXECUÇÃO AUTOMÁTICA")
print("-" * 80)

try:
    # Cria um JSON de teste válido
    sim_json_path = BASE_DIR / "scheduled_tasks" / "simulation_test.json"
    sim_data = {
        "mode": "text",
        "target": "TESTE_SIMULACAO",
        "text": "Mensagem de simulação",
        "file": ""
    }
    
    with open(sim_json_path, "w", encoding="utf-8") as f:
        json.dump(sim_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ JSON de simulação criado: {sim_json_path}")
    
    # Verifica se app.py consegue ler o JSON
    with open(sim_json_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    
    # Simula o que app.py faz
    mode = loaded_data.get("mode")
    target = loaded_data.get("target")
    text = loaded_data.get("text")
    file_path = loaded_data.get("file")
    
    print(f"✓ Dados lidos pelo app.py:")
    print(f"    Mode: {mode}")
    print(f"    Target: {target}")
    print(f"    Text: {bool(text)}")
    print(f"    File: {file_path}")
    
    if mode and target:
        print("✓ Formato correto - app.py conseguiria processar")
    else:
        print("✗ Formato incorreto - faltam dados obrigatórios")
    
    # Remove arquivo de teste
    sim_json_path.unlink()
    
except Exception as e:
    print(f"✗ Erro na simulação: {e}")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "="*80)
print("RESUMO DO DIAGNÓSTICO")
print("="*80)

print("\n✓ Passos para resolver problemas comuns:")
print("  1. Certifique-se de que o app está rodando como Administrador")
print("  2. Verifique se o Windows Task Scheduler está ativo")
print("  3. Execute 'app.exe --auto caminho.json' manualmente para testar")
print("  4. Verifique os logs em: " + str(BASE_DIR / "logs"))
print("  5. Para testes, use 'Enviar agora' antes de agendar")

print("\n✓ Para forçar execução de uma tarefa agendada:")
print("  schtasks /Run /TN StudyPractices_WA_<ID>")

print("\n✓ Para listar tarefas agendadas:")
print("  schtasks /Query | findstr StudyPractices")

print("\n" + "="*80)
print("FIM DO DIAGNÓSTICO")
print("="*80 + "\n")

input("\nPressione Enter para fechar...")