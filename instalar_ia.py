"""
Script para instalar dependências opcionais de IA
Instala apenas as bibliotecas necessárias para funcionalidades de IA
"""

import subprocess
import sys

def instalar_pacote(pacote, nome_amigavel):
    """Tenta instalar um pacote"""
    print(f"\n{'='*60}")
    print(f"Instalando {nome_amigavel}...")
    print(f"{'='*60}")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pacote], 
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"[OK] {nome_amigavel} instalado com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao instalar {nome_amigavel}")
        print(f"   Erro: {e}")
        return False

def verificar_pacote(pacote):
    """Verifica se um pacote está instalado"""
    try:
        __import__(pacote)
        return True
    except ImportError:
        return False

def main():
    """Função principal"""
    print("=" * 60)
    print("INSTALADOR DE DEPENDENCIAS DE IA")
    print("=" * 60)
    print()
    print("Este script instala as bibliotecas opcionais de IA:")
    print("  - scikit-learn (Machine Learning)")
    print("  - prophet (Previsão de séries temporais)")
    print("  - transformers (Processamento de linguagem natural)")
    print()
    
    # Lista de pacotes para instalar
    pacotes = [
        ("sklearn", "scikit-learn", "scikit-learn>=1.3.0"),
        ("prophet", "Prophet", "prophet>=1.1.4"),
        ("transformers", "Transformers", "transformers>=4.30.0"),
    ]
    
    # Verifica quais já estão instalados
    print("Verificando pacotes instalados...")
    print()
    
    para_instalar = []
    ja_instalados = []
    
    for modulo, nome, pacote_pip in pacotes:
        if verificar_pacote(modulo):
            print(f"[OK] {nome} ja esta instalado")
            ja_instalados.append(nome)
        else:
            print(f"[FALTANDO] {nome} nao esta instalado")
            para_instalar.append((pacote_pip, nome))
    
    if not para_instalar:
        print()
        print("=" * 60)
        print("[OK] Todas as dependencias de IA ja estao instaladas!")
        print("=" * 60)
        return 0
    
    print()
    print(f"Pacotes a instalar: {len(para_instalar)}")
    print()
    
    resposta = input("Deseja instalar os pacotes faltantes? (s/n): ").lower()
    
    if resposta != 's':
        print("Instalacao cancelada.")
        return 0
    
    # Instala os pacotes
    sucessos = 0
    falhas = 0
    
    for pacote_pip, nome in para_instalar:
        if instalar_pacote(pacote_pip, nome):
            sucessos += 1
        else:
            falhas += 1
    
    # Resumo
    print()
    print("=" * 60)
    print("RESUMO DA INSTALACAO")
    print("=" * 60)
    print(f"Instalados com sucesso: {sucessos}")
    print(f"Falhas: {falhas}")
    print()
    
    if falhas == 0:
        print("[OK] Todas as dependencias foram instaladas!")
        print()
        print("Proximos passos:")
        print("  1. Reinicie o servidor")
        print("  2. As funcionalidades de IA estarao disponiveis")
    else:
        print("[AVISO] Algumas dependencias falharam ao instalar.")
        print("  O sistema continuara funcionando com metodos simples.")
    
    return 0 if falhas == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

