import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


SCRIPTS_TO_RUN = [
    "seed_games_rawg.py",
    "collect_steam_reviews.py",
    "calculate_steam_community_scores.py",
]


def run_script(script_name: str) -> None:
    script_path = PROJECT_ROOT / "scripts" / script_name

    if not script_path.exists():
        raise FileNotFoundError(f"Script não encontrado: {script_path}")

    print("\n========================================")
    print(f"Executando: {script_name}")
    print("========================================\n")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"O script {script_name} falhou.")


def main() -> None:
    print("Iniciando atualização automática do Oráculo de Hype...")

    for script_name in SCRIPTS_TO_RUN:
        run_script(script_name)

    print("\n========================================")
    print("Atualização finalizada com sucesso.")
    print("========================================")


if __name__ == "__main__":
    main()
    