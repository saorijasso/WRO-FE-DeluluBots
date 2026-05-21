import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from processing.image_manager import ImageManager

image = ImageManager()
image.run()