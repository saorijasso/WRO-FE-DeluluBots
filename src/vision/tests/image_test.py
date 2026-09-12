import sys
from pathlib import Path

# Obtener la ruta raíz de la carpeta 'src'
SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from processing.image_manager import ImageManager

image = ImageManager()
image.run_test()

#To test using an image, uncomment the line below and change the last parameter to the file's path
#image.run_test_from_image(os.path.join(os.path.dirname(__file__), "vision1.png")) 