# AI Illustrator Workflow

[English](README.md) | 简体中文

这是一个 Codex 插件，用于设计配图方案，并把选定的参考图重构为可编辑的 Adobe Illustrator 文件。它适用于科研原理图、商业插画、技术示意图、信息图和其他二维图形任务。

如果你从文字需求开始，工作流会先生成五张候选图供你选择。已有认可的参考图时，则直接进入重构。最终文件使用 Illustrator 原生路径、文字、编组、渐变和剪切蒙版。

## 在 Codex 中安装

先登记这个仓库的插件市场，再安装插件：

```powershell
codex plugin marketplace add Yi-Wang798/ai-illustrator-workflow --ref main
codex plugin add ai-illustrator-workflow@yi-wang-plugins
```

安装后新建一个 Codex 任务，输入技能名称和需求：

```text
$ai-illustrator-workflow:scientific-ai-illustrator

根据下面的原理和要求设计配图。先给我五张候选图，选定后再重构为可编辑的 Illustrator 文件。
```

如果已有参考图，可以要求保留布局和重复部件的一致性，交付分层 `.ai` 文件和 PNG 预览。也可以直接用自然语言描述任务，这个 Skill 支持自动调用。

## 工作流程

1. 确定图片要表达的信息、阅读顺序、各区域作用和已知信息的边界。科研机制图还要记录实体状态、颜色、连接关系和前后变化。
2. 提前规划关键部件的 Illustrator 画法。规则结构优先用标准图形和母版；连接或重复结构要求较高时，先制作简单的几何草图。
3. 从同一套部件定义编译五条独立提示词，用 Codex 内置生图工具生成方案。逐张检查含义、物理可信度、可读性和能否重构，再展示候选图。
4. 用户选定后，将参考图放在锁定图层中。测量布局，逐项制作原生对象，并按区域对照校准。
5. 检查全图，每轮修改交付一个带版本号的 `.ai` 文件和一张干净 PNG。删除本轮临时草稿，保留以前的最终版本。

期刊风格需求会落实到主次层级、语义配色、简短标注和留白。具体期刊的尺寸、字体和投稿要求应写在项目需求中。只说“Nature 风格”还不足以确定机制内容或证明图片符合投稿要求。

## 使用条件与当前限制

- Codex 客户端需要支持插件和本地 Skill。生成新方案时，还需要内置生图工具可用。
- 随附的原生绘图执行器需要 Windows、已安装的 Adobe Illustrator、Python 3.10 或更新版本，以及 `pywin32`。规范校验和 JSX 生成可以在没有 Illustrator 的环境中运行。
- 默认字体是 Noto Sans SC。请安装该字体，或在需求中指定其他字体。
- 工作流优先使用当前环境里偏画质的最新生图能力。工具提供模型身份时，会说明实际型号；工具没有模型选择参数时，插件无法强制指定型号。

生图仍可能出现颜色漂移、重复细节不一致或关系画错。工作流要求检查实际图像，并使用经过确认的原生母版保证精确重复。提示词编译脚本只检查输入说明，不能验证科学事实或生成的像素。几何脚本检查已经声明的关系，也不能覆盖所有绘图缺陷。

## 随附工具

提示词编译器可以生成五条方案记录，本身不调用 API：

```powershell
python plugins/ai-illustrator-workflow/skills/scientific-ai-illustrator/scripts/concept_prompt.py concept-contract.json --output concept-prompts.json
```

输入字段和检查方法见[前期生图说明](plugins/ai-illustrator-workflow/skills/scientific-ai-illustrator/references/concept-generation.md)。

绘图构建器用于校验规范并生成 Illustrator 脚本：

```powershell
python plugins/ai-illustrator-workflow/scripts/sciai.py validate examples/basic-layout.json
python plugins/ai-illustrator-workflow/scripts/sciai.py build examples/basic-layout.json --output outputs/example
```

在 Windows 上添加 `--run`，可以在 Illustrator 中执行并保存 AI 文件和 PNG。需要时先安装可选依赖，并检查环境：

```powershell
python -m pip install pywin32
python plugins/ai-illustrator-workflow/scripts/sciai.py doctor
```

Skill 还包含几何关系检查、文字视觉居中和修改版本清理工具。描边面板箭头等部分 Illustrator 设置，可能需要通过动作、图形样式或面板操作完成。

## 市场登记文件与目录

市场登记文件是 [.agents/plugins/marketplace.json](.agents/plugins/marketplace.json)。它定义了 `yi-wang-plugins` 市场，并指向 `plugins/ai-illustrator-workflow`。有了这个文件，用户可以把本仓库添加为自定义插件市场；它不代表插件已经进入公开精选插件目录。

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

公开包不包含私有项目规范、客户图稿和本地检查记录。

## 更新与本地修改

获取发布后的新版本：

```powershell
codex plugin marketplace upgrade yi-wang-plugins
codex plugin add ai-illustrator-workflow@yi-wang-plugins
```

更新后新建任务即可加载新版。做本地开发时，先克隆仓库，修改 `plugins/` 下的源文件，再运行：

```powershell
python -m pip install pytest pyyaml
python -m pytest -q
```

发布前检查配置文件和引用路径，为分发更新修改插件版本号，再从本地市场重新安装并在新任务中测试。修改源目录即可，不要直接修改 Codex 的安装缓存。具体课题或客户的验收要求仍保存在对应项目中。

## 绘图参考

前期方案流程参考了 [academic-figures](https://github.com/sai-tv/academic-figures)、[nature-figure](https://github.com/Yuan1z0825/nature-skills) 和 [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) 中的信息组织与部件规划思路。插件使用自己的 Illustrator 构建器和 Codex 内置生图工具。具体来源链接保存在前期生图说明中。
