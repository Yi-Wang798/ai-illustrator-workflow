# Concept generation for editable Illustrator artwork

Read before generating any new candidate composition. The image model receives a drawing plan, not an open-ended request to make a topic look impressive. Use the built-in image-generation tool by default and preserve the user's five-candidate selection stage.

## 1. Establish the message and its limits

Write one sentence describing what the reader must understand. Choose the figure type from the content: mechanism, process, apparatus, comparison, architecture, graphical abstract, or mixed figure. Give each panel one distinct role in that message and an explicit reading order. A mechanism needs state changes; a comparison needs matched conditions; an apparatus needs credible geometry. Do not force all figures into boxes, timelines, or infographic cards.

For scientific work, separate supplied facts from schematic simplifications and unresolved details. Never infer sequences, binding sites, stoichiometry, anatomy, experimental measurements, or causal claims from a request for an attractive picture. Use an explicit symbolic representation when exact molecular or physical detail is unavailable; preserve the relevant connectivity and label the abstraction in the figure legend. Ask only when a missing fact would change the mechanism. Leave real data panels empty or use supplied data; decorative curves and invented micrographs are not evidence.

For commercial or editorial work, use the same message, hierarchy, and construction planning with the user's content and style. Journal rules apply only to journal work.

## 2. Design the components before rendering them

Create a compact concept contract in the project directory. Include:

- message, audience, figure type, aspect ratio, reading order, evidence boundary;
- every recurring entity's ID, literal label, semantic color, and visual representation;
- every entity's Illustrator construction recipe: primitive geometry, operations, layer relationships, and reusable master;
- each panel's role, entity occurrences and states, exact relationships, and state transitions;
- invariants and forbidden implications;
- five candidate layouts, focal elements, label locations, and usable spacing.

The construction recipe must be concrete, such as ellipse family plus translated bands and clipping for a lid, two parallel lines plus repeated rungs for a symbolic duplex, or a native icon master plus uniform transforms. "Draw a beautiful molecule" is not a recipe. If a necessary object cannot be decomposed into a small manageable contour set, use a simpler scientifically valid representation or a measured reference. Do not postpone this decision until tracing.

Use the same entity definitions and palette in all five candidates. Vary composition, grouping, emphasis, or line-versus-fill treatment; retain the mechanism, states, labels, domain colors, and physical relationships. A cycle layout is appropriate only for a genuine cycle. Distinct candidates need separate prompts, not one prompt asking the model for five pictures on a contact sheet.

For geometry-sensitive mechanisms, prepare a simple native/vector scaffold from the contract before generation: place the required objects, connections, and label zones using regular shapes. Render it as a reference input to the built-in tool and describe its role as a geometry/semantic scaffold. Inspect the scaffold first. Ask the model to improve visual hierarchy and finish while preserving connectivity and component identity. Use an author-provided sketch when available. A scaffold is a control input, not a substitute for the five generated candidates or the final native AI file.

Retain the scaffold's canonical component masters as the source of truth for regular contours, repeated tick counts, and internal proportions during native reconstruction. The generated image guides composition and approved appearance; it cannot silently override these masters. Inspect model drift and correct it in candidate review. When exact repetition repeatedly fails in raster generation, make a native corrected preview from the existing masters before calling that candidate accepted; do not trace a different raster variant for each occurrence or claim that another prompt guarantees exact copies.

## 3. Translate journal design logic into concrete visual instructions

Nature/Science-style is not a single preset. When the user requests journal-style work, inspect relevant schematic figures or supplied references for figure type, information density, hierarchy, and reading path; record the specific features to adopt. Learn the visual grammar without copying distinctive artwork. Check official requirements only when dimensions, typography, or submission compliance are part of the deliverable.

For research schematics without a supplied visual style, start with:

- a white or explicitly requested background, an identifiable focal step, and ample space between objects and arrows;
- a small semantic palette with neutral structural elements; reserve stronger color for meaningful distinctions and keep repeated domains consistent;
- crisp standard geometry, restrained strokes, minimal text, and explicit, separated connectors;
- flat fills or a small number of controllable gradients; add 2D depth cues only where they explain a physical surface;
- realistic silhouettes and coherent scale relationships for apparatus; schematic molecular drawings should communicate state and binding rather than imitate photorealistic molecules.

Exclude unrequested glow, bloom, lens effects, glossy blobs, metallic ornament, floating particles, decorative DNA helices, excessive perspective, random soft shadows, and background texture. Avoid arbitrary boxes around every panel and oversized title banners. Do not remove a necessary scientific entity merely to make the image minimal.

Default font remains Noto Sans SC. A user-specified font takes priority. Generated lettering is provisional; rebuild labels as editable native text and verify at final size. Use only the supplied short labels. Do not invent explanatory paragraphs, tick marks, numbers, logos, or measurements.

## 4. Compile the actual built-in generation prompts

Use `python scripts/concept_prompt.py <contract.json>` to validate the contract and produce five prompt records plus review criteria. The helper does not call an API, select a model, generate pixels, or prove scientific correctness. Pass each record's `prompt` to one built-in image-generation call, with any scaffold/reference explicitly identified. Inspect current tool capabilities; do not invent unsupported model, batch, quality, or output-path arguments. Use the newest quality-focused image capability available to the host; honor a user-specified model and disclose hidden model identity.

Each prompt must contain the message, scientific/evidence limits, fixed component dictionary and construction recipes, panel states and relationships, exact labels, this candidate's composition, and the exclusions. Never reduce the prompt to "Nature style, professional, 2D, high quality." Preserve these invariants in targeted edits.

## 5. Inspect candidates before showing them

Open each generated output and inspect the whole image and its critical components. Record each candidate's status as pass, repair, or blocked, with observable evidence. A general beauty score cannot override any of these failures:

1. Meaning: invented/missing entities, wrong state, attachment, chronology, domain color, causality, or unsupported quantitative implication.
2. Physical credibility: impossible silhouette, nonphysical junction, inconsistent projection, misleading molecular structure, or an unexplained scale change.
3. Reconstructability: fuzzy/fused contour, texture-dependent appearance, uncontrolled organic deformation, many tiny unique details, or a critical component with no workable native construction recipe.
4. Communication: unclear reading order, repeated panels with no distinct role, hidden/crossing arrows, labels touching objects, unreadable text, or poor hierarchy at intended size.
5. Consistency: recurring components drift in internal shape, line weight, color, or proportions.

For each critical component, explain its proposed native construction against the generated contour. If this explanation requires arbitrary freehand corrections, repair the candidate before selection. Inspect at intended viewing size as well as magnified; a raster preview cannot certify exact curve geometry or font metrics.

Correct scientific structure first, then physical geometry, then layout, then finish. Issue a targeted image edit with the failed relationship and all invariants restated. If two targeted repairs of a candidate still fail the same constraint, simplify its representation or strengthen the scaffold rather than continue cosmetic rerolls. Keep failed outputs in revision temp storage and report unresolved limitations; do not present them as approved candidates. Deliver five separately numbered accepted candidates and selection controls when supported. User feedback starts a local correction cycle, not a reset of every verified component.

## Design sources

This is an original adaptation of reusable design principles, not a copy of another skill's provider scripts or backend workflow. Reviewed 2026-10-13:

- [academic-figures](https://github.com/sai-tv/academic-figures/blob/master/SKILL.md): narrative, panel roles, layout alternatives, editable components.
- [nature-figure AI graphical-abstract workflow](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-figure/references/ai-graphical-abstract-workflow.md): one message, figure contract, bounded generative role, scientific verification.
- [scientific-visualization](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-visualization/SKILL.md): truthful encoding, semantic color, final-size inspection.
- [scientific-schematics](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-schematics/SKILL.md): explicit components/relationships and generation-review-refinement. Its model score is advisory; this workflow retains concrete geometric and semantic checks.
