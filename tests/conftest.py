import sys
from pathlib import Path

# Make api/ and pipeline/ importable when pytest runs from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent))
