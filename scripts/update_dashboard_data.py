import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


SCRIPTS_TO_RUN = [
    "seed_games_rawg.py",
    "collect_steam_reviews.py",
    "calculate_steam_community_scores.py",
]


REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "RAWG_API_KEY",
]


def load_local_env() -> None:
    env_path = PROJECT_ROOT / ".env"

    if load_dotenv is None:
        print("Aviso: python-dotenv não está instalado. Pulando leitura do .env.")
        return

    if env_path.exists():
        print(f"Carregando variáveis locais de: {env_path}")
        load_dotenv(env_path)
    else:
        print("Arquivo .env local não encontrado. Usando apenas variáveis do ambiente.")


def validate_environment() -> None:
    print("Validando variáveis de ambiente da automação...")

    missing_vars = []

    for env_var in REQUIRED_ENV_VARS:
        if not os.getenv(env_var):
            missing_vars.append(env_var)

    if missing_vars:
        print("Erro: variáveis ausentes no ambiente:")

        for env_var in missing_vars:
            print(f"- {env_var}")

        print(
            "\nNo computador local, confira se o arquivo .env existe na raiz do projeto.\n"
            "No GitHub Actions, confira se os Repository Secrets foram criados."
        )

        raise RuntimeError("Variáveis obrigatórias não foram encontradas.")

    print("Variáveis de ambiente encontradas.")


def run_script(script_name: str) -> None:
    script_path = PROJECT_ROOT / "scripts" / script_name

    if not script_path.exists():
        raise FileNotFoundError(f"Script não encontrado: {script_path}")

    print("\n========================================")
    print(f"Executando: {script_name}")
    print("========================================\n")

    environment = os.environ.copy()

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        text=True,
        env=environment,
    )

    if result.returncode != 0:
        raise RuntimeError(f"O script {script_name} falhou.")


def main() -> None:
    print("Iniciando atualização automática do Oráculo de Hype...")

    load_local_env()
    validate_environment()

    for script_name in SCRIPTS_TO_RUN:
        run_script(script_name)

    print("\n========================================")
    print("Atualização finalizada com sucesso.")
    print("========================================")


if __name__ == "__main__":
    main()