# 网站内容维护

平时更新 `_data/*.json`，页面统一读取这些数据。原始资料先放到工作区根目录的 `02_content_materials/00_inbox/`，确认事实、来源和公开范围后，再把网站用稿及选定图片加入源码。本说明中的路径均以网站目录 `03_website/LogScience.github.io/` 为基准，收件箱路径除外。

## 给下一位协作者的请求

把新资料与填好的 `content-templates/update-request.json` 放在同一个收件箱子文件夹。可以直接这样请求：

> 请读取根目录 AGENTS.md 和相关项目上下文，整理 `02_content_materials/00_inbox/本次资料/`。根据来源更新网站 JSON，保留现有记录和稳定 ID，列出仍待确认的事实，运行内容校验并检查本地预览。只在本地修改，不提交或上传。

每次交付应说明修改的记录 ID、采用的来源、图片出处、仍待确认的事项和校验结果。历史材料中的职位、日期、计划只能作为线索；未确认的学期、毕业去向或定量结论不能补写。未发表研究只介绍已同意公开的目标和方法。

## 常见更新对应位置

| 内容 | 数据文件 | 更新方式 |
| --- | --- | --- |
| 新闻 | `_data/news.json` | 每条独立 ID；日期用 `YYYY-MM-DD`；标题采用课题组视角，摘要依据原文；外部新闻保留来源链接，站内新闻使用 `link_type: internal` 与 `/news/slug/` |
| 招生和招聘 | `_data/opportunities.json` | 现行公告放 `current` 并在 Contact 显示；历史公告放 `archived`，保留原来源，不混入 News |
| 当前成员和校友 | `_data/team.json` | 当前成员放在对应 `groups[].members`；离组后按确认信息移入 `alumni`；保留成员 ID 以维持研究引用 |
| 论文 | `_data/group_publications.json` | 按用户确认的收录范围更新；保存完整作者顺序、通信作者标记、DOI 与书目信息 |
| 研究和项目 | `_data/research.json` | `people[].id` 引用成员，`paper_ids` 引用论文；项目角色保留 `PI`、`Co-PI`、`Co-I` |
| 首页精选 | `_data/home.json` | 用论文 ID 配置精选；`news_limit` 控制最近新闻条数；`contact_heading`、`contact_text` 控制首页联系文案 |
| 首页轮播 | `_data/home.json` 的 `gallery` | 原group2合照＋新增五图，共六图；每图image/image_alt/caption保留，首页captions=false隐藏图注。interval=5000（5秒）、controls=dots、autoplay=true、transition=fade（0.5秒）；下方仅六点，当前黑/其他白，五项方法小字已删除。第一张及下一张预加载，保留完整人物 |
| 站内毕业专题 | `_data/milestones.json` 和 `_pages/mphil-graduation-2026.html` | 保存学生、论文题目、答辩时间、地点、委员会及照片；站内新闻必须有匹配 permalink 的源文件 |
| Platform | `_data/platform.json` | 四个 `sections`：监测/模型站点、多层采样器、共享分析条件与方法、遥感数据；`layout`分别为stations、feature、analysis、datasets |
| 名称、联系与首页文案 | `_data/lab.json` | 集中维护名称、简介、公开邮箱、地址及 `homepage`、`assets`；未知办公室允许为 `null` |
| 图片优化映射 | `_data/delivery_images.json` | 图片流程生成的原图 URL → 优化图信息；更新原图后重新生成，避免手工改字节数和尺寸 |

`content-templates/` 提供单条记录示例，**不会自动出现在网站上**。复制到目标数组前，替换所有 `REPLACE`、中文提示及 `null` 占位符。新增记录使用新 ID；修改记录沿用旧 ID；删除成员或论文时同步检查研究和首页引用。人数、新闻数和论文数可随经过确认的更新变化，校验工具不把当前数量固定为永久规则。

新闻可增加 `title_en`、`summary_en` 和 `category`。推荐分类为 `research`、`recognition`、`fieldwork`、`community`；采用现有页面支持的分类。招生招聘使用独立 Opportunities 数据，不能给 News 记录添加 `opportunities` 分类。英文是原文的忠实转述；未准备好时省略可选字段，不填写空字符串。

新闻始终按 `date` 倒序，新增记录不靠插入位置控制顺序。通常用原文发布日期；如用户明确要求用接受日期或活动日期，增加 `date_note_en` / `date_note`（如 Accepted / 论文接受），原推文日期另记 `source_date`。news-27采用接受2026-02-12，推文2026-03-12；news-28采用两场答辩中较晚的2026-07-25并标Thesis defenses，不代表毕业或发稿日。

原生新闻设 `link_type: "internal"`，`url: "/news/slug/"`，正文源文件放 `_pages/` 并声明一致的 `permalink`。外部新闻新标签打开，站内新闻当前页打开，均适配学生Pages子路径。卡片双图可用gallery（image/image_alt/caption），共用轮播组件。新闻仍为前后/Play按钮，手动切换暂停、Play恢复，减少动态效果时默认暂停。首页最新按5秒自动播放、0.5秒交叉淡入淡出，无左右/Play按钮；圆点直接选图，移开后继续。悬停、键盘可见焦点、页面隐藏或离开视口时暂时停止；首页明确要求的播放/过渡设置优先于旧减少动态效果规则。首屏初始化后才启用过渡，避免多图闪现；非当前图aria-hidden/inert，新闻非当前图仍hidden。无JS仍可横向滑动看图。

Platform每个资源项使用 `title`、`summary`；可选 `paragraphs`、`caption`、`kicker`。图片需同时提供 `image_alt`，选图保留完整图例；站点、采样器和方法图可点开本地原尺寸导出图，链接必须经过relative_url。`facts`是label/value数组；`links`是label/url数组，用于论文或方法参考。兼容单个 `url` / `link_label`，外链须HTTP(S)。共享设施写在section.facility，含name/summary/url/equipment_url/image/image_alt及instruments数组（每项title/summary/image/image_alt），不能把学校共享设备写成组内所有。

数据产品 `status` 仅用 `planned`、`in-development` 或 `released`。待发布产品用 `availability_note`说明状态，不编造DOI、精度、许可、发布日期或下载入口。只有 `released` 才能填写 `download_url`并显示下载按钮，校验器会拒绝未发布数据的下载字段。方法学参考仍可放links，文字要明确Reference/About，不能当作本组数据访问入口。`content-templates/planned-dataset.json`提供预告示例；`platform-item.json`供一般资源使用。

当前遥感区按用户要求采用 `compact: true`：卡片只显示 `status_label`、标题和简短summary；`status_label`统一为Ongoing，实际planned/in-development状态与事实/来源仍保留在数据中，界面隐藏参数表、说明及方法链接。将来确有数据发布时再更新状态和展示方式。section.image/image_alt/caption提供两卡下方的公共示例图，不能把HLS示例标成Rrs成果。选定图由原始面板用SVG视口横排，完整保留图例/色标，源图和可复现排版脚本存活动素材区及04_delivery/tools。

当前HLS-WF预告为PRB月尺度2015–2025地表水比例，筹备发布；Sentinel-2/ACOLITE Rrs仅为计划，时间范围/频次未确认。Ducar等2026美国数据论文仅是外部方法参考，不加入本组13篇Publications或冒充PRB数据。当前采样器资料没有专利授权记录，不补专利号或授权状态。

### 招生招聘

使用 `content-templates/opportunities.json` 创建单条公告，填写来源日期、标题、摘要、原文链接和图片；`current` 中还需填写确认的 `positions`（岗位或名额）、`intake`（入学或到岗时间）、`research_focus`（研究方向）和 `requirements`（要求数组）。不能把大学通用门槛或其他公告条件自行补为本次岗位要求。

现行公告结束或被替换后，把原记录从 `current` 移到 `archived`，保留原 ID、原文链接、日期和完整历史内容，不再当作当前开放岗位。历史公告不要求补齐当时未整理的岗位字段。当前和历史公告之间不能有重复 ID 或来源链接，也不能与 News 重复。当前 Contact 模板只显示一条现行公告，`current` 最多一条；需要多个并行公告时先扩展模板，校验器会阻止静默漏显。允许 `current` 为空，不能为保持版面而虚构开放岗位。当前已确认的博士招生公告归 Contact；2025 年研究助理公告仅保留在历史记录。

### 成员当前身份与经历

Alumni按离组或项目结束时期倒序。`sort_order`是由编辑指定的排序整数，值大者靠前；它不代表具体日期。新增成员时同时维护此值和 `period`。同一学期/季节可放在一起，不把Summer/Fall改成未经确认的月份。列表单列便于由上至下阅读。

校友可选填 `destination` 字符串，显示为 `| Destination: ...`；未提供的整段隐藏，包括分隔线，不显示占位符、不猜去向。role在尚未确认时可暂缺，但name/period仍必填；提供的role/destination都须为非空文字。Junkai LING已由用户确认Research Assistant（Summer 2025），去向MPhil, HKUST(GZ)，按时期排在Fall2025之后、Apr2025之前。

成员放在哪个 `groups` 由当前身份决定；过去的组内阶段可写入 `note` 和 `education`，不为了保留经历把同一个人重复放入当前组和校友表。所有当前Postdoc、PhD与RA的 `entry` 按入组年份写为 `2023-now`，不是当前岗位开始年份；Xinke原2024年MPhil入组，因此为 `2024-now`，2026年转RA写在经历说明。Postdoc也统一最早入组年份-now；Hongkai为2022-now。博士后任职起点和博士教育经历单独写入note/education；未知入学学期不自行添加Spring/Fall。教育经历 `education` 为字符串；联合博士后导师使用 `postdoc_supervisors` 数组，每项含 `name` 和 `institution`，仅在用户确认时填写。`content-templates/postdoc-member.json` 提供相应字段示例。

目前用户已确认 Hongkai QI 是课题组首位博士生，22Fall 入学、2025 年毕业并于 25Fall 留组做博士后；联合博士后导师为 Prof. Jianping GAN（HKUST）和 Prof. Yi LIU（HKUST(GZ)）。这些经历保留在其 Postdoc 记录的 `note`、`education`、`postdoc_supervisors` 中。其他成员不能按此类推补全学期或联合导师。

最新确认：Huan WANG在Fall2022以MPhil加入，毕业后继续读PhD，entry为2022-now，不能再用PhD阶段年份覆盖最早入组年，也不猜转博年份。Huanglin LUO在Fall2024以visiting research student加入、Fall2025开始PhD，entry为2024-now。Yuke LI的Alumni显示仅Fall2024入学学期，用户明确不显示其毕业年；毕业新闻保留真实2026经历。

本科项目 `research.undergraduate_projects` 现在为项目组数组，每组独立保存funder/year/role/titles，可选status。当前2025 X-Program三项、2024 UBRTP一项，合计四项；2024项目完成状态保留在数据中，按2026-10-30用户要求不在页面标题显示Completed，不把它放在2025标题下。UBRTP为“Terrestrial contaminant loading to South China Sea via Pearl River discharge”，PI，用户来源记30k RMB/finished；资助额留在上下文记录，网站与其他项目一致不显示金额。Research support保留栏目标题，但不再显示原support_note说明。

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

在现有 Docker/Jekyll 流程生成最新 `_site` 后，额外检查七个核心页面与已登记的站内新闻正文：

```powershell
python tools/check_content.py --site-dir _site
python tools/check_content.py --site-dir _site --json
```

项目站预览可显式覆盖配置中的地址前缀和站点域名，例如：

```powershell
python tools/check_content.py --site-dir _site --baseurl /preview --site-url https://example.github.io
```

源码检查覆盖 JSON 结构、重复键、ID/来源链接、真实日期、DOI、引用关系、本地图片/轮播图、Platform资源、毕业专题、招聘与 News 的重复和分流规则、可选教育及导师字段。构建检查从七个栏目（含 `/platform/`）及已登记的站内新闻正文出发，检查重复 HTML ID、页面与资源路径、HTML 锚点、`srcset`，支持目录 `index.html` 和 `baseurl`。链接到的其他本地页面会核对存在性和锚点，不继续遍历历史页面。工具不请求远程链接，也不验证外部网页内容或图片版权。

退出码 `0` 表示通过，`1` 表示发现内容问题；命令参数错误为 `2`。`--json` 输出含 `ok`、`counts`、`errors` 的报告。错误会指出数据位置或页面路径。通过后仍需在 `http://localhost:4000/` 检查桌面、手机宽度以及文字和图片效果。

本地检查与预览不构成上传授权。按照工作区约定，与老师确认稿件且用户明确要求上传后，才执行 GitHub 上传与正式发布流程。

## 图片与交互检查命令

```powershell
node tools/optimize_images.cjs --modules /path/to/node_modules
node tools/optimize_images.cjs --modules /path/to/node_modules --check
node --test tests/*.cjs
```

图片脚本依赖 Sharp；当前 Codex 捆绑运行时的 `dependencies/node/node_modules` 已安装。它生成 WebP 副本和映射，保留原图。更新后重启 `docker compose restart jekyll-site` 并等构建完成；本机挂载目录的自动监测不可靠。

用户已于 2026-10-26 明确要求遥感方向使用其大湾区整体尺度地图，选用第三稿 Fig10 v02，来源记录在活动素材区 `04_research/gba-map/SOURCE.md`。这张已选图允许在本地网站展示；其余未发表原稿和结果不因此自动加入网站。

机构标识在lab.affiliations中，每条有稳定id、name、image/image_alt和官方url。首页只显示用户提供的原图，保留比例/颜色；2号为HKUST/Earth-HK，不能标为HKUST(GZ)。导航背景为官方HKUST Blue #003366，白字，当前页金色细线。

当前页眉只保留透明LOG logo4.png，取消白底框及右侧三行文字，原比例显示。首页标题由lab.homepage.title/subtitle维护：Land-Ocean-Groundwater / Water Science from river basin to coast.，主标题大、副标题小，各占一行，按第一栏宽度缩放字号，手机也完整显示。Platform EESRF为透明EESRF_logo2.png，最大宽420px、左栏居中，与右侧介绍高度接近；两PNG/优化副本保留透明，不flatten为白底。以上纳入v2.2，后续修改仍默认本地、获用户明确授权后再上传。导航菜单断点1140px。Platform的hide_description:true隐藏页标题下冗余说明，description仍用于meta/分享信息。

人物新闻可设置image_fit为contain、image_shape为portrait：桌面较高竖图，手机原比例完整显示。课程等参考资料可移至素材reference_only，不自动发布为News。
