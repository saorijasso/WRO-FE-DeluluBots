# Element Detection

## Overview

The computer vision system processes the images captured by the camera and detects the different elements present on the competition field.

The HSV ranges used by the detection algorithms are generated using the calibration tool described in [`calibration`](../calibration/README.md).

The system currently detects:

- Red signs.
- Green signs.
- Blue lines.
- Orange lines.
- Pink parking walls.
- Track space.

---

## Vision Pipeline

```text
┌──────────────────────────┐
│       Camera Frame       │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│      HSV Conversion      │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│      Color Filtering     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Morphological Operations │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│    Contour Detection     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Bounding Box Generation  │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│     Target Selection     │
└──────────────────────────┘
```

---

## Element Detection

The `process_elements()` method performs the detection process for signs and lines.

For each frame:

1. The image is converted to HSV.
2. A binary mask is generated.
3. Morphological operations remove noise.
4. Contours are extracted.
5. Small contours are discarded.
6. A target element is selected.

Each detected element stores:

- Color.
- Binary mask.
- Contour.
- Area.
- Bounding rectangle.

---

## Pillar Detection

Red and green signs are processed using:

```python
VisionUtils.select_target_pillar()
```

The selected target is determined according to:

1. Contour area.
2. Vertical position.

When both signs have similar areas, the pillar located lower in the image is considered closer to the robot.

---

## Line Detection

Blue and orange lines are processed using:

```python
VisionUtils.select_target_line()
```

Unlike signs, line detection prioritizes the vertical position because perspective distortion affects their apparent size.

If both lines are located at similar heights, contour area is used as a secondary criterion.

---

## Track Detection

Track detection uses a different pipeline.

Before processing, red and green objects are replaced to avoid interference:

```python
image = VisionUtils.replace_color(
    frame,
    saved_ranges.color_ranges,
    ["Red", "Green"]
)
```

The image then follows the following steps:

```text
┌──────────────────────────┐
│          Resize          │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│   Grayscale conversion   │
└────────────┬─────────────┘
             │
             ▼ 
┌──────────────────────────┐
│    Bilateral filtering   │
└────────────┬─────────────┘
             │
             ▼    
┌──────────────────────────┐
│       Thresholding       │
└────────────┬─────────────┘
             │
             ▼       
┌──────────────────────────┐
│  Morphological closing   │
└────────────┬─────────────┘
             │
             ▼    
┌──────────────────────────┐
│     Largest countour     |
|        extraction        │
└──────────────────────────┘
```

The largest valid contour is preserved and used as the track representation.

---

## Software Structure

```text
ImageManager
    │
    ├── process_walls()
    ├── process_elements()
    ├── show_results()
    ├── run_test()
    └── run_test_from_image()

VisionUtils
    │
    ├── detect_element()
    ├── select_target_pillar()
    ├── select_target_line()
    ├── draw_element()
    ├── keep_largest_white()
    └── replace_color()
```