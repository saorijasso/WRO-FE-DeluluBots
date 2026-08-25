WRO 2026 Future Engineers - DeluluBots
====

## Table Of Contents
1. [Team](#1-team)
2. [Challenge Overview](#2-challenge-overview)
3. [Our Robot](#3-our-robot)
4. [Hardware](#4-hardware)
    * 4.1. [Mobility Management](#41-mobility-management)
    * 4.2. [Power and Sense Management](#42-power-and-sense-management)
5. [Software](5-software)
    * 5.1. [Computer Vision](#51-computer-vision)
    * 5.2. [Vehicle Control](#52-vehicle-control)
6. [License](#6-license)

## 1. Team

## 2. Challenge Overview

## 3. Our Robot

## 4. Hardware

### 4.1. Mobility Management

### 4.2. Power and Sense Management

## 5. Software

### 5.1. Computer Vision

#### HSV calibration

##### Overview

Reliable color detection is essential for autonomous navigation. Different lighting conditions can significantly alter the appearance of objects on the field, making fixed color values unsuitable.

To solve this problem, a calibration tool was developed to adjust and store HSV ranges for each element of the competition.

The tool allows users to tune the HSV thresholds in real time and immediately visualize the resulting mask.

---

##### Calibration Interface

The interface includes:

- HSV sliders.
- Real-time camera preview.
- Binary mask visualization.
- Configuration saving.

Each color can be adjusted independently.

---

##### Calibration Workflow

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
│  Threshold Adjustment    │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│      Mask Preview        │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│    Save Configuration    │
└──────────────────────────┘
```

---

##### HSV Color Space

The calibration system converts each frame from BGR to HSV:

```python
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
```

HSV was selected because it separates color information from illumination, allowing the system to adapt more easily to different environments.

---

##### Mask Generation

The binary mask is generated using:

```python
mask = cv2.inRange(
    hsv,
    np.array(low),
    np.array(high)
)
```

Pixels inside the selected range are preserved, while all other pixels are discarded.

---

##### Configuration Storage

The calibrated HSV ranges are stored in:

```text
config/
└── saved_ranges.py
```

These values are later loaded by the vision pipeline and used during obstacle detection and navigation.

##### Detection Examples

###### Red Signs

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

###### Green Signs

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

###### Blue Lines

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

###### Orange Lines

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

###### Parking Walls

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

###### White Space

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

#### Element detection

##### Overview

The computer vision system processes the images captured by the camera and detects the different elements present on the competition field.

The HSV ranges used by the detection algorithms are generated using the calibration tool described in [`calibration`](#hsv-calibration).

The system currently detects:

- Red signs.
- Green signs.
- Blue lines.
- Orange lines.
- Pink parking walls.
- Track space.

---

##### Vision Pipeline

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

##### Detection

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

##### Sign Detection

Red and green signs are processed using:

```python
VisionUtils.select_target_pillar()
```

The selected target is determined according to:

1. Contour area.
2. Vertical position.

When both signs have similar areas, the sign located lower in the image is considered closer to the robot.

---

##### Line Detection

Blue and orange lines are processed using:

```python
VisionUtils.select_target_line()
```

Unlike signs, line detection prioritizes the vertical position because perspective distortion affects their apparent size.

If both lines are located at similar heights, contour area is used as a secondary criterion.

---

##### Track Detection

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

##### Software Structure

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

### 5.2. Vehicle Control

#### Obstacle challenge logic
#### Lap counting
#### Parking procedure

## 6. License