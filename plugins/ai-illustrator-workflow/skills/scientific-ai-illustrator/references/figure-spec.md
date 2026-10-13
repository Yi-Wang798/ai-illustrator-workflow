# Illustrator Figure Spec

All coordinates use the artboard's top-left corner as the origin. `x` increases rightward, `y` increases downward, and dimensions are in millimetres.

## Top-level fields

| Field | Meaning |
|---|---|
| `title` | Document title and metadata |
| `canvas` | `width_mm`, `height_mm`, and optional `background` |
| `layers` | Layer declarations ordered from bottom to top |
| `objects` | Native object specifications |
| `reference_image` | Optional underlay path, position, size, and opacity |
| `calibration_exports` | Optional one-region-at-a-time overlay preview definitions |

## Common object fields

- `type`, `name`, and `layer` identify the object and destination layer.
- `style.fill`, `style.stroke`, `style.stroke_width_mm`, and `style.opacity` control flat appearance.
- `style.fill_gradient` supports native linear or radial gradients with angle and ordered color/opacity stops.
- `rotation_deg` rotates an object or a complete group as one motif.

## Supported objects

- `ellipse`, `rectangle`, and `rounded_rectangle` use `x`, `y`, `width`, and `height`.
- `open_circular_arch` creates one editable open contour from a circular crown and two straight legs. Use `cx`, `cy`, `radius`, `half_gap`, `left_leg_end_y`, and `right_leg_end_y`; the builder inserts no transition anchors between the arc and legs.
- `line` and `arrow` use `x1`, `y1`, `x2`, and `y2`; arrows may define `head_size`.
- `wave` creates a repeated smooth wave from position, width, amplitude, cycle count, and orientation.
- `bezier_path` defines irregular open or closed contours with explicit anchors and handles.
- `text` supports font, size, color, alignment, and optional `visual_center` for optical centering.
- `group` contains `children`; children inherit the group's layer when omitted.

The validator rejects unknown object types, invalid colors or gradients, non-finite values, duplicate/unknown layers, and malformed geometry. Specifications are data only and cannot execute code.
