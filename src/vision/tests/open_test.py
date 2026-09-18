import sys
from pathlib import Path
import os

SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))    

from processing.image_manager import ImageManager
#
image = ImageManager()
image.run_open_test()