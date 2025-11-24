from src.pipeline import atualizar_guias

if __name__ == "__main__":
    print("🔄 Iniciando atualização automática via GitHub Actions...")
    novos = atualizar_guias()
    print(f"✅ Atualização concluída. Novos registros: {novos}")
