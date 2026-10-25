# 网站内容维护

平时更新 `_data/*.json`，页面统一读取这些数据。原始资料先放到工作区根目录的 `02_content_materials/00_inbox/`，确认事实、来源和公开范围后，再把网站用稿及选定图片加入源码。本说明中的路径均以网站目录 `03_website/LogScience.github.io/` 为基准，收件箱路径除外。

## 给下一位协作者的请求

把新资料与填好的 `content-templates/update-request.json` 放在同一个收件箱子文件夹。可以直接这样请求：

> 请读取根目录 AGENTS.md 和相关项目上下文，整理 `02_content_materials/00_inbox/本次资料/`。根据来源更新网站 JSON，保留现有记录和稳定 ID，列出仍待确认的事实，运行内容校验并检查本地预览。只在本地修改，不提交或上传。

每次交付应说明修改的记录 ID、采用的来源、图片出处、仍待确认的事项和校验结果。历史材料中的职位、日期、计划只能作为线索；未确认的学期、毕业去向或定量结论不能补写。未发表研究只介绍已同意公开的目标和方法。

## 常见更新对应位置

| 内容 | 数据文件 | 更新方式 |
| --- | --- | --- |
| 新闻 | `_data/news.json` | 每条独立 ID；日期用 `YYYY-MM-DD`；标题采用课题组视角，摘要依据原文，`url` 保留来源链接 |
| 招生和招聘 | `_data/opportunities.json` | 现行公告放 `current` 并在 Contact 显示；历史公告放 `archived`，保留原来源，不混入 News |
| 当前成员和校友 | `_data/team.json` | 当前成员放在对应 `groups[].members`；离组后按确认信息移入 `alumni`；保留成员 ID 以维持研究引用 |
| 论文 | `_data/group_publications.json` | 按用户确认的收录范围更新；保存完整作者顺序、通信作者标记、DOI 与书目信息 |
| 研究和项目 | `_data/research.json` | `people[].id` 引用成员，`paper_ids` 引用论文；项目角色保留 `PI`、`Co-PI`、`Co-I` |
| 首页精选 | `_data/home.json` | 用论文 ID 配置精选；`news_limit` 控制最近新闻条数；`contact_heading`、`contact_text` 控制首页联系文案 |
| 名称、联系与首页文案 | `_data/lab.json` | 集中维护名称、简介、公开邮箱、地址及 `homepage`、`assets`；未知办公室允许为 `null` |
| 图片优化映射 | `_data/delivery_images.json` | 图片流程生成的原图 URL → 优化图信息；更新原图后重新生成，避免手工改字节数和尺寸 |

`content-templates/` 提供单条记录示例，**不会自动出现在网站上**。复制到目标数组前，替换所有 `REPLACE`、中文提示及 `null` 占位符。新增记录使用新 ID；修改记录沿用旧 ID；删除成员或论文时同步检查研究和首页引用。人数、新闻数和论文数可随经过确认的更新变化，校验工具不把当前数量固定为永久规则。

新闻可增加 `title_en`、`summary_en` 和 `category`。推荐分类为 `research`、`recognition`、`fieldwork`、`community`；采用现有页面支持的分类。招生招聘使用独立 Opportunities 数据，不能给 News 记录添加 `opportunities` 分类。英文是原文的忠实转述；未准备好时省略可选字段，不填写空字符串。

### 招生招聘

使用 `content-templates/opportunities.json` 创建单条公告，填写来源日期、标题、摘要、原文链接和图片；`current` 中还需填写确认的 `positions`（岗位或名额）、`intake`（入学或到岗时间）、`research_focus`（研究方向）和 `requirements`（要求数组）。不能把大学通用门槛或其他公告条件自行补为本次岗位要求。

现行公告结束或被替换后，把原记录从 `current` 移到 `archived`，保留原 ID、原文链接、日期和完整历史内容，不再当作当前开放岗位。历史公告不要求补齐当时未整理的岗位字段。当前和历史公告之间不能有重复 ID 或来源链接，也不能与 News 重复。当前 Contact 模板只显示一条现行公告，`current` 最多一条；需要多个并行公告时先扩展模板，校验器会阻止静默漏显。允许 `current` 为空，不能为保持版面而虚构开放岗位。当前已确认的博士招生公告归 Contact；2025 年研究助理公告仅保留在历史记录。

### 成员当前身份与经历

成员放在哪个 `groups` 由当前身份决定；过去的组内阶段可写入 `note` 和 `education`，不为了保留经历把同一个人重复放入当前组和校友表。所有当前Postdoc、PhD与RA的 `entry` 按入组年份写为 `2023-now`，不是当前岗位开始年份；Xinke原2024年MPhil入组，因此为 `2024-now`，2026年转RA写在经历说明。Postdoc也统一最早入组年份-now；Hongkai为2022-now。博士后任职起点和博士教育经历单独写入note/education；未知入学学期不自行添加Spring/Fall。教育经历 `education` 为字符串；联合博士后导师使用 `postdoc_supervisors` 数组，每项含 `name` 和 `institution`，仅在用户确认时填写。`content-templates/postdoc-member.json` 提供相应字段示例。

目前用户已确认 Hongkai QI 是课题组首位博士生，22Fall 入学、2025 年毕业并于 25Fall 留组做博士后；联合博士后导师为 Prof. Jianping GAN（HKUST）和 Prof. Yi LIU（HKUST(GZ)）。这些经历保留在其 Postdoc 记录的 `note`、`education`、`postdoc_supervisors` 中。其他成员不能按此类推补全学期或联合导师。

论文 `year` 控制展示分组，`online_year` 可记录与卷期年不同的首次在线年份；遵循项目已确认的年份规则。DOI 使用 `10.…/…` 原始格式，链接使用对应 `https://doi.org/…`。`is_pi` 和 `corresponding` 是 JSON 布尔值 `true`/`false`。`order` 是排序整数，允许 `0` 或负数，不是论文 ID，也不必等于 CV 编号。

## 图片

仅将已确认可公开的图片复制到网站 `images/` 下的对应目录，保留活动素材区原件和来源说明。`image` 使用 `/images/…`，不写 Windows 绝对路径或线上域名。新闻和研究图填写具体 `image_alt`；已知尺寸可填 `image_width`、`image_height`。研究示意图用 `contain`，人物或活动照片按版式需要用 `cover`。

现有图片流程通过 `delivery_images.json` 选择优化版本并回退原图。单条记录也可选填 `image_web`，校验工具会检查该路径存在；是否优先使用该字段取决于对应模板。不能仅改扩展名来假装完成格式转换。

## 本地检查

在网站目录运行，要求 Python 3.9 及以上，无需安装第三方 Python 包：

```powershell
python tools/check_content.py
python -m unittest discover -s tests -v
```

当前机器若 `python` 指向不可用的 Windows 应用商店别名，可以使用 Codex 的运行时：

```powershell
$contentPython = 'C:\Users\14467\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $contentPython tools/check_content.py
& $contentPython -m unittest discover -s tests -v
```

在现有 Docker/Jekyll 流程生成最新 `_site` 后，额外检查六个核心页面：

```powershell
python tools/check_content.py --site-dir _site
python tools/check_content.py --site-dir _site --json
```

项目站预览可显式覆盖配置中的地址前缀和站点域名，例如：

```powershell
python tools/check_content.py --site-dir _site --baseurl /preview --site-url https://example.github.io
```

源码检查覆盖 JSON 结构、重复键、ID/来源链接、真实日期、DOI、引用关系、本地图片、招聘与 News 的重复和分流规则、可选教育及导师字段。构建检查仅从 `/`、`/research/`、`/team/`、`/publications/`、`/news/`、`/contact/` 出发，检查重复 HTML ID、页面与资源路径、HTML 锚点、`srcset`，支持目录 `index.html` 和 `baseurl`。链接到的其他本地页面会核对存在性和锚点，不继续遍历历史页面。工具不请求远程链接，也不验证外部网页内容或图片版权。

退出码 `0` 表示通过，`1` 表示发现内容问题；命令参数错误为 `2`。`--json` 输出含 `ok`、`counts`、`errors` 的报告。错误会指出数据位置或页面路径。通过后仍需在 `http://localhost:4000/` 检查桌面、手机宽度以及文字和图片效果。

本地检查与预览不构成上传授权。按照工作区约定，与老师确认稿件且用户明确要求上传后，才执行 GitHub 上传与正式发布流程。

## 图片与交互检查命令

```powershell
node tools/optimize_images.cjs --modules /path/to/node_modules
node tools/optimize_images.cjs --modules /path/to/node_modules --check
node --test tests/test_lab_state.cjs
```

图片脚本依赖 Sharp；当前 Codex 捆绑运行时的 `dependencies/node/node_modules` 已安装。它生成 WebP 副本和映射，保留原图。更新后重启 `docker compose restart jekyll-site` 并等构建完成；本机挂载目录的自动监测不可靠。

用户已于 2026-10-26 明确要求遥感方向使用其大湾区整体尺度地图，选用第三稿 Fig10 v02，来源记录在活动素材区 `04_research/gba-map/SOURCE.md`。这张已选图允许在本地网站展示；其余未发表原稿和结果不因此自动加入网站。

机构标识在lab.affiliations中，每条有稳定id、name、image/image_alt和官方url。首页只显示用户提供的原图，保留比例/颜色；2号为HKUST/Earth-HK，不能标为HKUST(GZ)。导航背景为官方HKUST Blue #003366，白字，当前页金色细线。

人物新闻可设置image_fit为contain、image_shape为portrait：桌面较高竖图，手机原比例完整显示。课程等参考资料可移至素材reference_only，不自动发布为News。
