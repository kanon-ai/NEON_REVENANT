"""Build the shared public prototype package, including both variants and notices."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[2]/'tools/package.py'),run_name='__main__')
