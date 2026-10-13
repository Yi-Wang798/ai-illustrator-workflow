# Underlay reconstruction gates

## Component worksheet

Record these fields for every source component before construction:

| Field | Requirement |
|---|---|
| Region and bounds | Exact `[left, top, right, bottom]` in source pixels |
| Geometry | Regular primitives with fitted source-pixel parameters and residual, or explicit irregular control points |
| Topology | Fused, contained, adjacent, connected, separated, masked, intersecting, or repeated |
| Construction | Shape Builder, Pathfinder, offset path, Pen/Curvature, Align/Distribute, Blend, symbol, pattern, mask, effect, or Transform Again |
| Appearance | Fill, outline role, inner-line role, cap/join, opacity, blend mode, and effects |
| Color model | Solid, gradient, pattern, texture, transparency, or effect; record native parameters |
| Text | Content, semantic level, font, alignment anchor, optical center, and clearance |
| Acceptance | An observable feature that proves the component matches the reference or brief |
| Status | `pending`, `passed`, or `failed` |

Do not export while any status is `pending` or `failed`.

## Required comparison passes

1. Silhouette: proportions, bounds, contour rhythm, and major negative spaces.
2. Path quality: anchor count, extrema, genuine inflection points, handle collinearity, endpoint tangency, corner type, caps/joins, and absence of wobbles or protruding segments.
3. Topology: fused/separate relationships, openings, masks, intersections, and connection points.
4. Repetition: count, gap, density, direction, and per-instance variation. Unchanged recurring graphics must resolve to one declared master and differ only by allowed whole-instance transforms.
5. Appearance: colors, gradients, patterns, strokes, caps, joins, transparency, and effects.
6. Typography: Noto Sans SC by default unless the user specifies another family; verify semantic sizes, weights, outlined-glyph optical centering, alignment, line breaks, and clearance. Do not accept `TextFrame.visibleBounds` as glyph evidence.
7. Full composition: every region checked, including components not mentioned in feedback.

## Rebuild isolation

For a from-scratch request:

- Start from a blank artboard and a new build/spec file.
- Set `source_objects_reused` to `false`.
- Derive every layout coordinate from the current source underlay.
- Use a rejected drawing only as evidence of failure modes; never use it as a coordinate or object source.
- Use a new output stem so comparison files remain separate.

## General geometry gates

- Open and closed paths must match the source topology; do not close an intentionally open contour or leave a required enclosure open.
- Circles, ellipses, rectangles, rounded rectangles, and straight axes must be fitted from sampled source edges. Store the fitted source-pixel parameters and residual; a mapped coordinate guessed by eye is not calibrated geometry.
- Composite shapes must be fused, cut, intersected, masked, or kept separate according to the reference. Visual overlap is not a substitute for correct construction.
- Resolve the front-to-back stack before adjusting local endpoints. Rear geometry may remain internally symmetric while its visible portion is asymmetric because a front component covers it. Validate important overlaps with `occlusion_stack`: rear first, hidden segments covered/clipped, front fill and final outline above, and zero visible protrusions.
- Detect axial, radial, rotational, and point symmetry before construction. Build one half/sector from the underlay, reflect/rotate it about the fitted axis or center, and validate paired extrema, endpoints, junctions, and band thickness with `mirror_symmetry`. Independently positioned left/right ends fail even when each end is individually smooth.
- Do not validate a composite or freeform path with the bounding box of an ideal primitive. Record and inspect the actual final PathItem anchors, handles, segment count, and primitive junctions. When a regular composite is built from a circular arc and straight segments, require direct shared junction anchors and forbid unplanned transition anchors.
- For a partly regular shape, document the primitive set and the segment/corner edits before using a freeform path. Prefer shape tools, direct selection, Live Corners, Shape Builder/Pathfinder, or deliberate covering.
- For an enclosing shape, record the interior clipping/intersection method and stacking order. Interior objects must be contained by the enclosure, and a duplicate/final boundary stroke must sit above them so the full perimeter remains continuous. Check the entire perimeter in isolation; hidden, doubled, or protruding segments fail the topology pass.
- Repeated arrays must match count, pitch, distribution, alignment, and any deliberate per-instance variation.
- Unchanged recurring graphics must be duplicates or symbol instances of one grouped master. Permit only position, uniform scale, and whole-instance rotation when orientation requires it; reject internal anchor, proportion, stroke, color, or component edits.
- Multi-part motifs must be grouped before transformation so their internal geometry remains intact.
- Every contained object must pass a transformed-bounds containment check with an explicit clearance. Text, arrows, motifs, and clipped artwork that touch or cross an unintended boundary fail.
- Smooth connected segments must share both an endpoint and a tangent. Reject extra anchors, non-collinear smooth handles, unintended inflection points, exposed seams, and arrow shafts protruding through their heads.
- Nested outlines, rims, shadows, highlights, and insets must use measured offsets and intentional stroke/appearance hierarchy.
- Stacked elliptical/cylindrical parts must share a fitted center and ellipse family. Generate both side endpoints and every front/back arc from the same radii; validate each band with `ellipse_band` so the two ends have the declared equal drop and the arc terminates exactly at both sides.
- For any stroke that visually terminates at an enclosure, calculate the endpoint from the actual final enclosure path. Use exact contact or a deliberate underlap with the final outline above it, and validate the junction with `boundary_attachment`.
- Constant-thickness handles, loops, frames, and rims must come from offset/compound geometry. Validate all visible insets with `offset_ring`; independent inner and outer freehand contours fail even if their bounding boxes look similar.
- First classify depth rendering as `shaded_2d` or `actual_extrusion`. A shaded two-dimensional illustration must preserve one unchanged silhouette and place every highlight, midtone, rim shade, and recess shadow inside that silhouette; validate it with `shaded_2d_illusion`. Do not add an offset outer contour merely to make it look three-dimensional. Only an explicitly extruded reference may use translated geometry and `translated_depth_copy`. Both modes still require a consistent light vector and intentional highlight/base/shadow ordering.
- Curved-surface highlights must use at least a soft falloff layer and a narrower core layer, track the same projected contour as the host, taper or round their ends, and remain clipped to the host enclosure. Validate with `specular_highlight`; reject wide opaque white strips or highlights unrelated to the surface curvature.
- Keep the final enclosing stroke on a dedicated topmost contour layer when attached interior strokes, gradients, highlights, or masks could otherwise create gaps or protrusions.
- Rounded bottoms attached to straight or tapered sides must retain a standard circle/ellipse provenance and exact line-to-arc tangency. Use `tangent_circle_base`; do not approximate the base with a chain of visually adjusted Bézier anchors.
- Repeated curved edges in a skirt, collar, or cap band must be a source ellipse/path plus an exact translated duplicate, cropped to common side limits. Use `parallel_ellipse_strip`; unequal vertical drops, independently adjusted curves, or a protruding side are automatic failures.
- Any fill that should visually meet an outline must bleed beneath and be clipped by the same enclosure geometry. Validate the underlap and stacking with `fill_boundary_underlap`; a visible white slit is an automatic failure.
- Hidden connectors must end just beneath the covering boundary and must not cross a visible seam. Validate the endpoint with `occlusion_trim`, then isolate every possible gap before approval.
- Text must not collide with shapes or become visually assigned to the wrong component.
- Project-specific geometry gates must live in the project's audit manifest. Do not add subject-specific examples to this reusable reference.

## Isolated layer calibration

Give each planned region one Illustrator layer. For region `n`:

1. Show `00_Reference` and region `n` only.
2. Hide all other drawing regions.
3. Compare bounding box, anchor location, scale, rotation, stroke width, repeated spacing, topology, appearance, and text position.
4. When the region contains an enclosure, temporarily use a high-contrast overlay and inspect its full perimeter plus every interior-to-boundary junction before accepting the region.
5. Apply mapping corrections, normalize the region back to translation `[0,0]`, scale `[100,100]`, rotation `0`, and stroke scale `1.0`, then mark it passed.
6. Continue only after the isolated overlay passes.

## Revision cleanup

Keep working previews and partial AI files in a revision-specific temporary folder. When one final AI/PNG pair is promoted, delete that folder. Preserve the prior conversation's promoted final and create a new numbered final in the next conversation.
