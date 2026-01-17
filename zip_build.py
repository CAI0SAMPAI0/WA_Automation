import os
import shutil
import subprocess
import zipfile

def realizar_build():
    print("--- Iniciando processo de Build ---")
    
    # 1. Executa o PyInstaller
    try:
        subprocess.run(["pyinstaller", "--clean", "app.spec"], check=True)
        print("\n[OK] Build concluído com sucesso.")
    except subprocess.CalledProcessError:
        print("\n[ERRO] Falha ao executar o PyInstaller.")
        return

    # 2. Configurações de caminhos
    nome_projeto = "Study Practices"
    pasta_dist = os.path.join("dist", nome_projeto)
    arquivo_instrucoes = "Instruções.txt"
    arquivo_zip_final = f"{nome_projeto}.zip"

    # 3. Copia o arquivo Instruções.txt para dentro da pasta dist antes de zipar
    if os.path.exists(arquivo_instrucoes):
        shutil.copy(arquivo_instrucoes, pasta_dist)
        print(f"[OK] {arquivo_instrucoes} copiado para a pasta de distribuição.")
    else:
        print(f"[AVISO] Arquivo {arquivo_instrucoes} não encontrado na raiz!")

    # 4. Cria o arquivo ZIP
    print(f"--- Criando arquivo ZIP: {arquivo_zip_final} ---")
    with zipfile.ZipFile(arquivo_zip_final, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for raiz, pastas, arquivos in os.walk(pasta_dist):
            for arquivo in arquivos:
                caminho_completo = os.path.join(raiz, arquivo)
                # Mantém a estrutura de pastas correta dentro do ZIP
                caminho_relativo = os.path.relpath(caminho_completo, os.path.join("dist"))
                zipf.write(caminho_completo, caminho_relativo)

    print(f"\n[SUCESSO] Processo finalizado! O arquivo '{arquivo_zip_final}' está pronto para envio.")

if __name__ == "__main__":
    realizar_build()