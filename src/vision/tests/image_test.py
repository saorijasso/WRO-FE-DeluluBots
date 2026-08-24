import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from processing.image_manager import ImageManager

image = ImageManager()
image.run_test()

#To test using an image, uncomment the line below and change the last parameter to the file's path
#image.run_test_from_image(os.path.join(os.path.dirname(__file__), "vision1.png")) 