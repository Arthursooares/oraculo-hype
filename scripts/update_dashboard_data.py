import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

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


def validate_environment() -> None:
    print("Validando variáveis de ambiente da automação...")

    missing_vars = []

    for env_var in REQUIRED_ENV_VARS:
        if not os.getenv(env_var):
            missing_vars.append(env_var)

    if missing_vars:
        print("Erro: variáveis ausentes no ambiente do GitHub Actions:")

        for env_var in missing_vars:
            print(f"- {env_var}")

        raise RuntimeError("Secrets obrigatórios não foram encontrados.")

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

    validate_environment()

    for script_name in SCRIPTS_TO_RUN:
        run_script(script_name)

    print("\n========================================")
    print("Atualização finalizada com sucesso.")
    print("========================================")


if __name__ == "__main__":
    main()