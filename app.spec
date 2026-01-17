# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

BASE_DIR = os.getcwd()

# =============================
# COLETA TODAS AS DEPENDÊNCIAS
# =============================

# Coleta dados automáticos para bibliotecas complexas
uc_data = collect_data_files('undetected_chromedriver', include_py_files=False)
selenium_data = collect_data_files('selenium', include_py_files=False)
# tkcalendar e babel são essenciais para o seletor de data funcionar no executável
babel_data = collect_data_files('babel', include_py_files=False)

# Hidden imports críticos para automação e componentes de UI
hiddenimports = [
    'undetected_chromedriver._compat',
    'undetected_chromedriver.patcher',
    'undetected_chromedriver.options',
    'undetected_chromedriver.cdp',
    'selenium.webdriver.common.by',
    'selenium.webdriver.support.ui',
    'selenium.webdriver.support.expected_conditions',
    'websocket._app',
    'websocket._core',
    'websocket._abnf',
    'packaging.version',
    'packaging.specifiers',
    'colorama',
    'colorama.ansi',
    'typing_extensions',
    'http.cookies',
    'http.cookiejar',
    'urllib3',
    'urllib3.contrib',
    'urllib3.contrib.pyopenssl',
    'charset_normalizer',
    'sqlite3',
    'json',
    'pathlib',
    'datetime',
    'tkcalendar',
    'babel.numbers', 
    'babel.localedata', # Localização para datas em PT-BR
]

# Adiciona submódulos para garantir que nada fique de fora
for pkg in ['selenium', 'undetected_chromedriver', 'websocket', 'sqlite3', 'customtkinter', 'babel']:
    hiddenimports.extend(collect_submodules(pkg))

# Definição das pastas e arquivos de dados do projeto
# Incluímos as pastas de sistema para que os caminhos relativos funcionem no PC do cliente
datas = [
    ("ui", "ui"),
    ("core", "core"),
    ("data", "data"),
    ("resources", "resources"),
    ("scheduled_tasks", "scheduled_tasks"),
]

# Verifica se o arquivo de contador existe antes de incluir para evitar erro no build
if os.path.exists("execution_count.txt"):
    datas.append(("execution_count.txt", "."))

# Mescla os dados coletados das bibliotecas
datas += uc_data + selenium_data + babel_data

# =============================
# ANÁLISE
# =============================
a = Analysis(
    ["app.py"],
    pathex=[BASE_DIR],
    binaries=[],  
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "pytest", "unittest", "tkinter.test", "matplotlib", "numpy", 
        "pandas", "scipy", "IPython", "jupyter", "notebook", 
        "test", "tests", "__pycache__"
    ],
    noarchive=False,
    cipher=None,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# =============================
# EXECUTÁVEL (Modo Onedir)
# =============================
exe = EXE(
    pyz,
    a.scripts,
    [],  
    exclude_binaries=True,
    name="Study Practices",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    uac_admin=True, 
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Oculta a janela preta do CMD
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join("resources", "Taty_s-English-Logo.ico"),
)

# =============================
# COLEÇÃO (Geração da Pasta Final)
# =============================
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Study Practices" 
)