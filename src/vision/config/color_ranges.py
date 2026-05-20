import os

default_hsv_ranges = {
    "Red": [(0,120,70),(10,255,255)],
    "Green": [(40,50,50),(80,255,255)],
    "Blue": [(90,50,50),(130,255,255)],
    "Orange": [(10,100,100),(25,255,255)],
    "Pink": [(140,50,50),(170,255,255)],
    "White": [(0,0,200),(179,50,255)]
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "saved_ranges.py")

class ColorRangeManager:

    def __init__(self):
        self.color_ranges = self.load_ranges()

    def load_ranges(self):
        if os.path.exists(SAVE_PATH):
            ranges = {}
            with open(SAVE_PATH, "r") as f:
                content = f.read()
            exec(content, ranges)
            return ranges["color_ranges"]
        return default_hsv_ranges

    def save_ranges(self):

        with open(SAVE_PATH, "w") as f:
            f.write("color_ranges = {\n")
            for k, v in self.color_ranges.items():
                low = tuple(v[0])
                high = tuple(v[1])
                f.write(f'    "{k}": ({low}, {high}),\n')
            f.write("}\n")