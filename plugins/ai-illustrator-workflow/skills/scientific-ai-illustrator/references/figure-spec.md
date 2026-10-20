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
| `layout` | Optional simple horizontal/vertical layout, never used with a reference underlay |
| `connections` | Optional computed axis-aligned arrows between named primitives |

## Common object fields

- `type`, `name`, and `layer` identify the object and destination layer.
- `id` is a unique stable identity used by connections and actual-document readback. Omitted IDs are generated from object-tree positions; supply explicit IDs for objects that will be referenced or revised.
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

## Optional simple-flow compilation

See [the runnable example](../../../../../examples/automatic-flow.json) in the source repository (installed packages may not include examples).

`layout` uses `direction` (`horizontal` or `vertical`), ordered `node_ids`, `origin: [x,y]`, and `gap_mm`. Nodes must be top-level unrotated rectangles, rounded rectangles, or ellipses with explicit dimensions. Their `x`/`y` may be omitted; cross-axis centers are aligned. Canvas size remains explicit and overflowing nodes are rejected. Existing coordinates are unchanged when `layout` is absent. A reference underlay plus automatic reflow is rejected.

Each `connections` entry has `source`, `target` (node IDs), `layer`, and optional `id`, `name`, `head_size`, `clearance_mm`, and `style`. Endpoints are computed from the exact geometric boundary along the common center axis, then offset by clearance. Use a connector layer above the nodes. Diagonal routes, overlapping nodes, insufficient arrow space, and routes through unrelated node boxes are rejected rather than guessed. For bends or complex geometry, use explicit paths and project-specific geometry checks.

A text object can set `container_id` to a top-level unrotated rectangle/rounded rectangle ID and optional `padding_mm` (default 1). The compiler centers actual glyph contours, preserves editable text, and checks the final glyph bounds against the container's inset rectangular bounds. Rounded corners and irregular containers still need visual clearance inspection. Long labels are not silently shrunk or rewritten: wrap or resize them deliberately if the readback fails.

## Actual-document evidence

Before final saving, the generated script reads native objects from `doc.pageItems`, resolves stable IDs stored in `note`, and checks exactly one match per expected object. Its UTF-8 `audits/<stem>.json` records native type counts, object types/names/layers/visibility, path anchor counts/closed state, bounds, actual text/fonts, glyph-center error, and failures. Unrotated primitive bounds are compared within 0.02 mm; glyph centers within 0.1 mm. Parent-transformed text is checked for actual bounds/text, but not against its untransformed center coordinates. Temporary glyph outlines are removed.

Bounds must stay inside the artboard unless an object explicitly sets `allow_outside_canvas: true` for intentional bleed. A contained label must always remain inside its container; this cannot be disabled by artboard bleed. The report does not infer scientific correctness, unseen occlusion, arbitrary-path tangency, or publisher compliance. Keep it with project audits, outside temporary cleanup, and reuse it instead of duplicating manual evidence.
