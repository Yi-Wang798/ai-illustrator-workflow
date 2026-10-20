# AI Illustrator Workflow

English | [简体中文](README.zh-CN.md)

A Codex plugin for planning illustrations and rebuilding approved references as editable Adobe Illustrator artwork. It supports scientific schematics, commercial graphics, technical diagrams, infographics and other 2D illustration work.

If you start with a brief, the workflow prepares five image concepts for you to choose from. An approved reference takes you straight to reconstruction. The final drawing uses native Illustrator paths, text, groups, gradients and clipping masks.

## Install in Codex

Register this repository as a plugin marketplace, then install the plugin:

```powershell
codex plugin marketplace add Yi-Wang798/ai-illustrator-workflow --ref main
codex plugin add ai-illustrator-workflow@yi-wang-plugins
```

Start a new Codex task after installation. Invoke the skill by name:

```text
$ai-illustrator-workflow:scientific-ai-illustrator

Create a diagram from the following brief. Show five concepts first, then rebuild my selected concept as an editable Illustrator file.
```

For an existing reference, ask the skill to preserve the layout and recurring components and deliver a layered `.ai` file with a PNG preview. You can also describe the task in ordinary language; the skill allows automatic selection.

## How the workflow runs

1. Define the message, reading order, panel roles and limits of the supplied information. For a scientific mechanism, record each entity's state, domain colors, connections and transitions.
2. Plan each important component's Illustrator construction. Use regular primitives and reusable masters where possible. Prepare a simple geometry scaffold when precise connections or repeated structures matter.
3. Compile five separate prompts from the same component dictionary. Generate concepts with Codex's built-in image tool, then inspect meaning, physical credibility, readability and reconstructability before presenting the choices.
4. After selection, place the reference on a locked layer. Measure its layout, reconstruct the components as native objects and calibrate each affected region against the reference.
5. Check the full composition. Export one versioned `.ai` file and one clean PNG for the revision, remove temporary drafts, and preserve earlier final versions.

Journal-style briefs use clear hierarchy, semantic color, short labels and planned whitespace. Exact publisher requirements belong to the project brief. A request for "Nature style" alone does not define a mechanism or establish submission compliance.

## Requirements and limits

- Use a Codex client that supports plugins and local skills. New concepts need access to the built-in image-generation tool.
- The bundled native runner requires Windows, an installed copy of Adobe Illustrator, Python 3.10 or later, and `pywin32`. Specification validation and JSX generation can run without Illustrator.
- Text defaults to Noto Sans SC. Install that font, or specify another family in the brief.
- The workflow uses the newest quality-focused image capability available to the host. It reports the model when the host exposes its identity. It cannot select a model through a tool that has no model-selection parameter.

Image generation can still change colors, repeat details inconsistently or draw incorrect relationships. The workflow requires visual review and uses canonical native masters for exact repetition. The prompt compiler checks the input contract; it does not validate scientific facts or generated pixels. The geometry checks cover declared relationships, not every possible drawing defect.

## Bundled tools

The concept compiler creates five prompt records without making an API call:

```powershell
python plugins/ai-illustrator-workflow/skills/scientific-ai-illustrator/scripts/concept_prompt.py concept-contract.json --output concept-prompts.json
```

Read [the concept-generation guide](plugins/ai-illustrator-workflow/skills/scientific-ai-illustrator/references/concept-generation.md) for the contract fields and review process.

The drawing builder validates a specification and produces an Illustrator script:

```powershell
python plugins/ai-illustrator-workflow/scripts/sciai.py validate examples/basic-layout.json
python plugins/ai-illustrator-workflow/scripts/sciai.py build examples/basic-layout.json --output outputs/example
```

On Windows, add `--run` to execute the script in Illustrator and save the AI file and PNG. Install the optional dependency first if needed:

```powershell
python -m pip install pywin32
python plugins/ai-illustrator-workflow/scripts/sciai.py doctor
```

The skill also includes helpers for declared geometry checks, optical text centering and revision cleanup. Some Illustrator settings, including Stroke-panel arrowheads, may require an Illustrator action, graphic style or panel operation.

### Precise layout and document readback

For simple new flows, optional `layout` and `connections` fields compute row/column alignment and arrow endpoints from primitive boundaries. Text `container_id` centers actual glyph outlines and checks label clearance. Measured references retain their coordinates; unsupported routes fail explicitly instead of being approximated. Try `examples/automatic-flow.json` with the same build command.

Every native run reads the actual Illustrator document before final export, checking identities, object types/counts, text/font, visibility, bounds and supported primitive geometry. Failed checks block final saving; one machine-readable report is kept in `audits/<stem>.json` beside the build. This report supplements the existing project audit without another manual review stage. Visual occlusion, scientific meaning and complex geometry still require targeted inspection. Details are in [the specification guide](plugins/ai-illustrator-workflow/skills/scientific-ai-illustrator/references/figure-spec.md).

## Marketplace catalog and repository layout

The registration file is [.agents/plugins/marketplace.json](.agents/plugins/marketplace.json). It defines the `yi-wang-plugins` marketplace and points to `plugins/ai-illustrator-workflow`. This catalog makes the repository installable as a custom marketplace; it does not submit the plugin to a public curated catalog.

```text
.agents/plugins/marketplace.json
plugins/ai-illustrator-workflow/
  .codex-plugin/plugin.json
  skills/scientific-ai-illustrator/
    SKILL.md
    references/
    scripts/
  scripts/
examples/basic-layout.json
tests/
README.md
README.zh-CN.md
```

Private project specifications, client artwork and local review artifacts stay outside the published package.

## Updates and development

To fetch a newer published version:

```powershell
codex plugin marketplace upgrade yi-wang-plugins
codex plugin add ai-illustrator-workflow@yi-wang-plugins
```

Start a new task to load the updated skill. For local development, clone the repository, edit the source under `plugins/`, and run:

```powershell
python -m pip install pytest pyyaml
python -m pytest -q
```

Validate the manifests and referenced files, change the plugin version when distributing an update, and reinstall it from the local marketplace before testing in a new task. Edit the source directory rather than Codex's installation cache. Keep project-specific acceptance rules in the user's project.

## Design references

The concept stage adapts narrative and component-planning principles from [academic-figures](https://github.com/sai-tv/academic-figures), [nature-figure](https://github.com/Yuan1z0825/nature-skills) and [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills). The plugin uses its own Illustrator builder and Codex's built-in image tool. Detailed source links are in the concept-generation guide.
