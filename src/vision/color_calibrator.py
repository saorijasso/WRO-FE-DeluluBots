import cv2
import numpy as np
import sys
import os

default_hsv_ranges = {
    "Red": [(0,120,70),(10,255,255)],
    "Green": [(40,50,50),(80,255,255)],
    "Blue": [(90,50,50),(130,255,255)],
    "Orange": [(10,100,100),(25,255,255)],
    "Pink": [(140,50,50),(170,255,255)],
    "White": [(0,0,200),(179,50,255)]
}

bg_color = (240, 240, 240)

button_colors = {
    "Red": (180, 180, 255),
    "Green": (180, 255, 180),
    "Blue": (255, 200, 150),
    "Orange": (180, 220, 255),
    "Pink": (230, 200, 255),
    "White": (255, 255, 255),
    "Reset": (198, 162, 200),
    "Save & Quit": (198, 162, 200)
}

# FILE LOAD CONFIG
if os.path.exists("color_ranges.py"):
    from color_ranges import color_ranges
else:
    color_ranges = default_hsv_ranges

# IMAGE LOADING
#image = cv2.imread("vision2.png")
#hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# WINDOW
cv2.namedWindow("Mask")
cv2.namedWindow("Controls")

def nothing(x): 
    pass

# TRACKBARS
for name, maxv in zip(["H","S","V"], [179,255,255]):
    cv2.createTrackbar(f"Low {name}", "Controls", 0, maxv, nothing)
    cv2.createTrackbar(f"High {name}", "Controls", maxv, maxv, nothing)

# BUTTON UI 
buttons_img = np.zeros((420, 520, 3), np.uint8)

button_w, button_h = 200, 60
gap_x, gap_y = 40, 20
start_x, start_y = 40, 40

order = ["Red","Green","Blue","Orange","Pink","White"]

positions = {}

# GRID
for i, name in enumerate(order):
    col = i % 2
    row = i // 2
    x = start_x + col*(button_w + gap_x)
    y = start_y + row*(button_h + gap_y)
    positions[name] = (x, y)


bottom_y = start_y + 3*(button_h + gap_y) + 10
positions["Reset"] = (start_x, bottom_y)
positions["Save & Quit"] = (start_x + button_w + gap_x, bottom_y)


def round_button(img, x, y, w, h, color):
    radius = 15

    # CENTRE
    cv2.rectangle(img, (x+radius, y), (x+w-radius, y+h), color, -1)
    cv2.rectangle(img, (x, y+radius), (x+w, y+h-radius), color, -1)

    # CORNERS
    cv2.circle(img, (x+radius, y+radius), radius, color, -1)
    cv2.circle(img, (x+w-radius, y+radius), radius, color, -1)
    cv2.circle(img, (x+radius, y+h-radius), radius, color, -1)
    cv2.circle(img, (x+w-radius, y+h-radius), radius, color, -1)

def draw_buttons():
    img = np.full((420, 520, 3), bg_color, dtype=np.uint8)

    for text, (x,y) in positions.items():

        color = button_colors.get(text, (200, 235, 200))

        round_button(img, x, y, button_w, button_h, color)

        (tw, th), _ = cv2.getTextSize(text,
                                     cv2.FONT_HERSHEY_DUPLEX,
                                     0.7, 1)

        tx = x + (button_w - tw)//2
        ty = y + (button_h + th)//2

        cv2.putText(img, text,
                    (tx, ty),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.7,
                    (60,60,60), 1)

    return img

buttons_img = draw_buttons()

# SAVE RANGES 
def save_ranges():
    with open("color_ranges.py", "w") as f:
        f.write("color_ranges = {\n")
        for k,v in color_ranges.items():
            f.write(f'    "{k}": {tuple(v)},\n')
        f.write("}")
    print("Saved config")

current_selected_color = None

# MOUSE DETECTION 
def mouse(event, x, y, flags, param):
    global current_selected_color 
    if event == cv2.EVENT_LBUTTONDOWN:
        for name,(bx,by) in positions.items():
            if bx <= x <= bx+button_w and by <= y <= by+button_h:

                if name in color_ranges:
                    current_selected_color = name
                    low, high = color_ranges[name]

                    cv2.setTrackbarPos("Low H","Controls",low[0])
                    cv2.setTrackbarPos("Low S","Controls",low[1])
                    cv2.setTrackbarPos("Low V","Controls",low[2])
                    cv2.setTrackbarPos("High H","Controls",high[0])
                    cv2.setTrackbarPos("High S","Controls",high[1])
                    cv2.setTrackbarPos("High V","Controls",high[2])

                    print(f"Loaded {name}")

                elif name == "Reset":
                    cv2.setTrackbarPos("Low H","Controls",0)
                    cv2.setTrackbarPos("Low S","Controls",0)
                    cv2.setTrackbarPos("Low V","Controls",0)
                    cv2.setTrackbarPos("High H","Controls",179)
                    cv2.setTrackbarPos("High S","Controls",255)
                    cv2.setTrackbarPos("High V","Controls",255)

                elif name == "Save & Quit":
                    save_ranges()
                    cv2.destroyAllWindows()
                    sys.exit()

cv2.setMouseCallback("Controls", mouse)

# LOOP
while True:
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        ret, image = cap.read()

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        low = (
            cv2.getTrackbarPos("Low H","Controls"),
            cv2.getTrackbarPos("Low S","Controls"),
            cv2.getTrackbarPos("Low V","Controls")
        )
        high = (
            cv2.getTrackbarPos("High H","Controls"),
            cv2.getTrackbarPos("High S","Controls"),
            cv2.getTrackbarPos("High V","Controls")
        )

        if current_selected_color is not None:
            color_ranges[current_selected_color] = [
                (low[0], low[1], low[2]),
                (high[0], high[1], high[2])
            ]

        mask = cv2.inRange(hsv, low, high)

        down_width = 700
        down_height = 350
        down_points = (down_width, down_height)
        resized_mask = cv2.resize(mask, down_points, interpolation = cv2.INTER_LINEAR)

        cv2.imshow("Mask", resized_mask)
        cv2.imshow("Controls", buttons_img)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    break