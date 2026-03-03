from pathlib import Path
import os

# Create symbols for easier navigation and type hinting
def create_init_files():
    dirs = [
        "src/imggen_app",
        "src/imggen_app/domain",
        "src/imggen_app/infrastructure",
        "src/imggen_app/infrastructure/search",
        "src/imggen_app/infrastructure/http",
        "src/imggen_app/infrastructure/spreadsheet",
        "src/imggen_app/infrastructure/cache",
        "src/imggen_app/application",
        "src/imggen_app/application/use_cases",
        "src/imggen_app/presentation",
        "src/imggen_app/presentation/qt",
        "src/imggen_app/config",
        "src/imggen_app/utils",
        "tests"
    ]
    for d in dirs:
        p = Path(d)
        p.mkdir(parents=True, exist_ok=True)
        init_file = p / "__init__.py"
        if not init_file.exists():
            init_file.touch()

if __name__ == "__main__":
    create_init_files()
