import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from processing.image_manager import ImageManager

image = ImageManager()
image.run_test()
#image.run_test_from_image(os.path.join(os.path.dirname(__file__), "file_name"))