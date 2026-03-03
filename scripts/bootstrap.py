import os
import subprocess
import sys
from pathlib import Path

def bootstrap():
    """
    Sets up the virtual environment and installs dependencies.
    """
    root_dir = Path(__file__).parent.parent
    venv_dir = root_dir / ".venv"
    cache_dir = root_dir / ".cache" / "pip"
    
    print(f"--- Bootstrapping project in {root_dir} ---")
    
    # 1. Ensure .venv exists
    if not venv_dir.exists():
        print(f"Creating virtual environment in {venv_dir}...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    
    # 2. Determine python executable in venv
    if sys.platform == "win32":
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        python_exe = venv_dir / "bin" / "python"
        
    # 3. Safe to run repeatedly - install dependencies
    print("Installing dependencies...")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        str(python_exe), "-m", "pip", "install", 
        "--cache-dir", str(cache_dir),
        "-e", ".[dev]"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n--- Bootstrap complete! ---")
        print(f"To activate the virtual environment:")
        if sys.platform == "win32":
            print(f"  .venv\\Scripts\\activate")
        else:
            print(f"  source .venv/bin/activate")
    except subprocess.CalledProcessError as e:
        print(f"\nError during dependency installation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    bootstrap()
