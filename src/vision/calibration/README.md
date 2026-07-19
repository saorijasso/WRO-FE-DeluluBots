# Color Calibration

## Overview

Reliable color detection is essential for autonomous navigation. Different lighting conditions can significantly alter the appearance of objects on the field, making fixed color values unsuitable.

To solve this problem, a calibration tool was developed to adjust and store HSV ranges for each element of the competition.

The tool allows users to tune the HSV thresholds in real time and immediately visualize the resulting mask.

---

## Calibration Interface

The interface includes:

- HSV sliders.
- Real-time camera preview.
- Binary mask visualization.
- Configuration saving.

Each color can be adjusted independently.

---

## Calibration Workflow

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

## HSV Color Space

The calibration system converts each frame from BGR to HSV:

```python
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
```

HSV was selected because it separates color information from illumination, allowing the system to adapt more easily to different environments.

---

## Mask Generation

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

## Configuration Storage

The calibrated HSV ranges are stored in:

```text
config/
└── saved_ranges.py
```

These values are later loaded by the vision pipeline and used during obstacle detection and navigation.

## Detection Examples

### Red Signs

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

### Green Signs

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

### Blue Lines

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

### Orange Lines

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

### Parking Walls

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |

---

### White Space

| Threshold Adjustment | Saving Configuration | Generated Mask |
| :---: | :---: | :---: |
|  |  |  |
