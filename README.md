# x-post-writer

把文字稿、PPT要点、个人经历和图视频素材，写成有观点、能兑现开头承诺的中文 X 短推与长推。

当前技能版本：**v1.3.0**。默认使用第一人称亲历式表达，支持完整长推、长推拆短，以及明确要求时的推文串。当前可安装分支为 `pre-release`。

## 能做什么

| 能力 | 用法 |
| --- | --- |
| 观点筛选 | 从素材提出判断，记录依据、读者收益与适用边界，再选择主线 |
| 开头与结构 | 用真实细节组织悬念、卡点、价值或反差，并检查正文的兑现位置 |
| 短长分工 | 短推交付一个完整观点或动作；长推围绕主线展开；用户明确要求时才拆串 |
| 个人文风 | 从本人样文按体裁观察语言、节奏、判断和图文关系，保留证据与反例 |
| 中文表达 | 检查段落推进，压缩换词重复，保留正常标点和必要解释 |
| 去AI味复核 | 调用随包固定版本的原版候选检测，再逐条语义判断和局部改稿 |

七宗罪用于内部选择表达动机，按素材取舍；不会把七种动机全部塞进正文，也不承诺爆款、流量或收益。资料不足时缩小承诺和篇幅，已有明确素材就直接成稿。

## 安装

技能目录是 [`skills/x-post-writer`](skills/x-post-writer/SKILL.md)。将整个目录安装到支持 Agent Skills 的环境中，保留目录内的 `references`、`scripts`、`assets` 和 `vendor`。

可以直接对支持技能安装的助手说：

```text
请从 https://github.com/zhuy3075-ui/x-post-writer 安装技能。
分支：pre-release；技能路径：skills/x-post-writer。
```

也可在 Windows PowerShell 中手动安装到 Codex 技能目录：

```powershell
git clone --branch pre-release --single-branch https://github.com/zhuy3075-ui/x-post-writer.git

$skillHome = if ($env:CODEX_HOME) {
    Join-Path $env:CODEX_HOME 'skills'
} else {
    Join-Path $env:USERPROFILE '.codex\skills'
}
$targetSkill = Join-Path $skillHome 'x-post-writer'
if (Test-Path -LiteralPath $targetSkill) {
    throw '目标技能目录已存在，请先备份并比较版本。'
}
New-Item -ItemType Directory -Path $skillHome -Force | Out-Null
Copy-Item -LiteralPath '.\x-post-writer\skills\x-post-writer' -Destination $targetSkill -Recurse
```

写作依赖支持技能的助手。运行随包检测程序需要 Python 3.10 或更新版本，只用标准库，无需 API 密钥或额外依赖包。本机验证使用 Python 3.14；其他助手客户端与运行环境未逐一测试。

## 使用

### 短推和完整长推

```text
用 $x-post-writer，把下面的文字稿和PPT要点写成2条短推、1篇完整长推。
直接用第一人称亲历口吻，先筛观点，匹配开头与正文结构。
保留自然标点，交稿前检查段落推进和去AI味。只给成稿。
```

### 参考个人文风

```text
用 $x-post-writer，参考我提供的本人短推样文，改写这段素材。
当前要求优先于旧样文，保留有依据的表达习惯，不沿用样文中的经历和成绩。
```

没有本人样文时按已知偏好写，不声称已经学会个人文风。可用的档案格式见[个人文风档案模板](skills/x-post-writer/assets/个人文风档案模板.md)；个人作品应保存在自己的资料目录。

### 拆短或只做检测

```text
用 $x-post-writer，把这篇长推拆成能独立发布的短推，每条保留完整背景和必要条件。
```

```text
用 $x-post-writer，只检查这篇稿件，不替我改写。
```

## 运行去AI味程序

在仓库根目录运行，输入文件使用 UTF-8，输出目录须为新路径：

```text
python -B -X utf8 skills/x-post-writer/scripts/run_upstream.py scan draft.md --out-dir checks/run-1
```

- 所有稿件运行原版候选提取，候选由当前会话逐条语义判断；脚本不自动决定作者来源或改写。
- 达到500汉字的稿件同时运行原版常规统计。较短稿件不拼接、不凑字，不生成虚假的常规统计报告。
- 改稿另存并复测；长稿可调用随包的原版报告程序生成 Markdown 或 HTML 对比，具体流程见[去AI味检测](skills/x-post-writer/references/去AI味检测.md)。
- `tone_check.py` 是独立的补充表达扫描，不冒称上游程序。正常标点、必要重复和作者文风结合语义判断，不按指标机械删除。

本地程序不联网、不外发文稿。使用模型或助手时的数据处理仍取决于所用服务及配置。候选、统计变化和第一人称都不证明真人来源、平台原创资格或变现资格。

## 目录

```text
skills/x-post-writer/
├── SKILL.md                 技能入口
├── agents/openai.yaml       界面元数据
├── references/              观点、结构、文风、表达与平台参考
├── assets/                  个人文风档案模板
├── scripts/                 本地检测适配与补充扫描
└── vendor/lieflat-less-ai-tone/
    ├── scripts/             未改动的原版 detect.py、report.py
    ├── references/           原版语义判据
    ├── LICENSE              原版许可证
    └── UPSTREAM.json        固定提交与SHA256
```

## 验证与边界

v1.3 已在本机完成技能结构、内部链接与锚点、原文件哈希、三短一长试写及修订复测、安装一致性与CLI冒烟检查。文案验证是实现者复核，未做独立盲测、传播效果实验或平台账号资格审核。

可以用上面的 `scan` 命令验证 Python、上游文件完整性和真实输入处理。平台规则参考含查阅日期，需要声称符合当前规则时应重新核对官方来源。

本仓库只包含可复用技能、来源与使用说明，不包含原录音、PPT照片、完整会议稿、用户私人样文、实际试写输出或本机检查日志。技能不自动采集账号、登录、发布或联系他人。

## 来源与许可

现场方法、用户新增要求和四个写作仓库的调研取舍见[方法来源](skills/x-post-writer/references/分享方法与出处.md)。README 采用定位、能力、安装、实例和验证分区，参考了 [marketingskills](https://github.com/coreyhaines31/marketingskills) 的信息组织方式，正文独立编写。

随包 `lieflat-less-ai-tone` 原文件保留作者 **shiujan** 的 **CC BY-NC 4.0** 许可及固定版本记录。自编部分尚未单独指定开源许可证；仓库公开不改变第三方许可，也不表示整仓库采用 MIT。详细归属见[第三方说明](THIRD_PARTY_NOTICES.md)。
