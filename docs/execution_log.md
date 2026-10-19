# 分阶段执行记录

日期：2026-10-19。所有命令在 `E:\现代交换原理\modern-switching-experiment-01` 执行。
本记录由 Codex 根据本次实际操作整理；不代表学生已经独立理解或教师已经评分。
用户要求依次完成 01—08，各阶段通过验收才继续；08 仅检查，不暂存、commit、push 或创建 PR。

## 开始前核查

- 已完整阅读 `codex_tasks/00_任务总览.md`、编号 01—08 的文件和实际完整 PRD `codex_tasks/实验一_PRD_电路交换与分组交换.md`（第 1—11 章）。
- 任务文档引用的 `实验一_PRD_完整版.md` 不存在，但实际 PRD 的 SHA256 为 `c96620f96b2ab41091da6a81300c600645db7ed0a1456432a445e231f1287d9b`，与 `conversion_audit.json` 一致。保留原始文档，不改名或复制。
- `README.md`、`requirements.txt`、`src/`、`grading/`、`student_tests/`、报告模板和 AI 记录模板均存在。起始 `git status --short` 仅有 `?? codex_tasks/`，三个 TODO 均未实现，无现有个人报告。
- 实际目录是工作区下的项目子目录，后续使用该目录。
- 阅读 `README.md`、`PROJECT_README.md`、`docs/model_contract.md`、数据类型、三个函数 docstring、框架及公开分项/集成测试；未发现模型和接口冲突。
- 任务文件中的逐阶段确认、完整提交步骤以本次用户指令为准：自动顺序执行本地工作，Git 提交另等确认。不会代写本人理解声明或虚构 AI 对话。

## 阶段 01：环境与手算（通过）

### 已执行的检查

```powershell
Get-Location
rg --files -g '!node_modules' -g '!.git'
git status --short
git remote -v
git branch --show-current
git log -1 --format='%h %s'
git --version
Get-Command python,py,git,uv -ErrorAction SilentlyContinue
python --version
py -0p
Get-FileHash -LiteralPath codex_tasks/实验一_PRD_电路交换与分组交换.md -Algorithm SHA256
Get-ChildItem -LiteralPath E:\workplace\codex-tools -Force
python -m pip show numpy matplotlib pytest
```

实际结果：分支 `main`，起始提交 `bc9099e`；origin 的 fetch/push 均为
`https://github.com/erjimeidianle/modern-switching-experiment-01.git`；Git 2.54.0.windows.1；系统 Python 3.14.5 位于 `C:\Python314\python.exe`，启动器仅列出此版本。系统解释器没有上述三个依赖。

通过 GitHub 连接器只读 `get_user_login`、`get_repo`：当前登录账号为 `erjimeidianle`，与 origin 所有者相同；仓库默认分支为 `main`，当前账号有 admin/push 权限。没有更改远端仓库或访问凭据。
用户本次提供姓名郑航宇、学号 2024280087，供报告使用。

进一步经 GitHub 连接器 `fetch` 读取仓库元数据，确认 `fork=true`、parent 和 source 均为 `jwentong/modern-switching-experiment-01`，摘要保存到 `results/logs/01_repository_verified.json`。此前 PowerShell `Invoke-RestMethod` 的尝试报 `Authentication failed, see inner exception`，产生的 `01_repository.json` 全空字段不作证据，保留该失败事实，没有修改认证设置。

修改代码前用 Python 标准库与 `git ls-files grading .github/workflows` 保存 13 个受保护文件的 SHA256 到 `results/logs/00_protected_sha256.json`，供阶段 08 再核验。

### 复用检查与真实失败

共用目录 `E:\workplace\codex-tools\python-packages` 存在 NumPy 2.5.0。执行：

```powershell
python -B -c "import sys; sys.path.insert(0, r'E:\workplace\codex-tools\python-packages'); import numpy, PIL; print('Python:', sys.version); print('NumPy:', numpy.__version__, numpy.__file__); print('Pillow:', PIL.__version__, PIL.__file__)"
```

退出码 1。真实错误摘要：`ModuleNotFoundError: No module named 'numpy._core._multiarray_umath'`，随后 NumPy 抛 `ImportError`。现有扩展是 `_multiarray_umath.cp312-win_amd64.pyd`，WHEEL 标记 `cp312-cp312-win_amd64`，与 cp314 不兼容，因此没有复用、覆盖或升级该共用环境。此错误是复用探测失败，不是阶段测试失败。

已执行 `python -m venv .venv`，退出码 0。依赖将安装到项目级 `.venv`，下载缓存放 `.build/cache/pip`，图形缓存使用 `.build/matplotlib`。

```powershell
& .\.venv\Scripts\python.exe -m pip install --dry-run --only-binary=:all: --cache-dir .build/cache/pip -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install --only-binary=:all: --disable-pip-version-check --cache-dir .build/cache/pip -r requirements.txt
```

dry-run 退出码 0，发现兼容的 cp314 预编译包，输出保存到 `results/logs/01_dependency_check.txt`。实际安装输出保存到 `results/logs/01_dependency_install.txt`。后续命令设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`，避免 Windows 中文路径输出乱码。

### 数据类型与事件规则

- `Config` 保存用户数、观察 tick 数、每 tick 的 wire bit 预算、tick 毫秒长度、包头 bit 数和 payload 缓存上限。
- `Arrival` 是不可变的到达记录：到达 tick、用户编号、原始 payload bit。
- `Pending` 保存用户、到达 tick、原始 payload 与可变的 `remaining_wire_bits`；只扣最后一项。
- 每 tick 先按到达输入顺序准入，再服务。缓存预留包含在传记录的完整原始 payload，整条完成才释放。空间不足整条尾丢弃。
- 电路只服务 `tick % users` 的队列，空时隙不可借；分组共享 FIFO，包头在框架中只加一次，可跨 tick 续传。
- 完成边界为 `tick + 1`，窗口结束不排空。未完成 payload 计积压，不能按已发出的部分减少。
- 模型忽略建链、传播、误码、重传与多跳。抽象比较链路 128 kbit/s，与 32×8×8000＝2.048 Mbit/s 的 PCM 辅助示例分开理解。

### 两用户先验手算

配置：users=2、ticks=2、slot_bits=128、tick_ms=1、header_bits=32、缓存足够。仅 tick 0 用户 1 到达 payload=96。

| tick | 电路服务用户 | 电路发送 wire bit | 分组发送 wire bit | 完成边界 |
|---|---|---:|---:|---|
| 0 | 0（空） | 0 | 96+32=128 | 分组在 1 ms 完成 |
| 1 | 1 | 96 | 0 | 电路在 2 ms 完成 |

总容量为 2×128=256 bit。两模型完整交付 payload 均为 96 bit，有效利用率均 96/256=37.5%；电路线路忙碌率 96/256=37.5%，分组线路忙碌率 128/256=50%。均无丢失和积压。这里的“用户 1”指零起始索引 1。

本阶段不修改 TODO。下一阶段仅修改 `src/part1_circuit.py` 的 `serve_circuit`。

### 验收

依赖安装退出码 0，实际版本：NumPy 2.5.4、Matplotlib 3.11.2、pytest 9.1.1。

```powershell
& .\.venv\Scripts\python.exe src/test_environment.py
& .\.venv\Scripts\python.exe -m pytest grading/test_framework.py -q
```

实际输出：`环境配置正确`；`4 passed in 0.27s`，两命令退出码均为 0。
原始输出保存到 `results/logs/01_environment.txt`、`01_framework.txt`。
新增 `.vscode/settings.json` 配置项目默认 Python 解释器为 `.venv/Scripts/python.exe`；未操控或声称已验证 VS Code UI 中的当前选择。
变更：项目级 `.venv/`、`.build/`、`.vscode/settings.json`、本记录和 `results/logs/`。无用户级安装、无 TODO 变更。阶段 01 无未解决的测试问题。

## 阶段 02：电路函数（通过）

AC01：当前用户为空则发送 0，其他用户不借用；AC02：200 bit 在首次服务时发送 128、剩余 72，原始 payload 仍为 200。实现只确定当前队列，再用 `min(剩余预算, 队首剩余)` 逐条扣减；完成才出队。

修改：仅 `src/part1_circuit.py` 的 TODO，以及本记录。接口、docstring、教师文件不变。

```powershell
git diff -- src/part1_circuit.py
& .\.venv\Scripts\python.exe -m pytest grading/test_circuit.py -q
```

真实结果：退出码 0，`4 passed in 0.04s`，详见 `results/logs/02_circuit.txt`。未修改其他 TODO，无未解决问题。

## 阶段 03：分组函数（通过）

AC03：payload=96、初始化 wire=128，一次发送完成；AC04：A=232、B=64，首 tick A 剩 104，次 tick 发 A104+B24，B 剩 40；AC05：两条各 48，一 tick 发 96、完成两条。只扣已初始化的 wire 剩余量，共享 FIFO 连续使用预算，不重复加头。

修改：仅 `src/part2_packet.py` 的 TODO，以及本记录。

```powershell
git diff -- src/part2_packet.py
& .\.venv\Scripts\python.exe -m pytest grading/test_packet.py -q
```

真实结果：退出码 0，`4 passed in 0.05s`，详见 `results/logs/03_packet.txt`。无未解决问题。

## 阶段 04：指标与守恒（通过）

AC06：仅一个 tick 发出 wire128，但 payload200 记录未完整交付，故有效利用率 0、积压200、平均时延 None。AC08：完全无业务则利用率和丢失率为 0，两个时延均 None。AC09：400≠200+100+99，必须抛 ValueError。部分发送不能和完整交付重复计量；无完成样本时的 None 表示无法估计时延，不能解释为零时延。

修改：仅 `src/metrics.py` 的 TODO，以及本记录。

```powershell
git diff -- src/metrics.py
& .\.venv\Scripts\python.exe -m pytest grading/test_metrics.py -q
```

真实结果：退出码 0，`3 passed in 0.05s`，详见 `results/logs/04_metrics.txt`。先检查守恒再计算六项指标，没有修改 raw、接口或其他源码。无未解决问题。

## 阶段 05：基线仿真与集成（通过）

运行前预测：continuous 电路预计充分利用，分组包头降低有效交付；staggered_burst 的热点用户不能借用电路空时隙，分组预计降低积压和丢失；synchronized_burst 两者会排队，包头可能加长分组时延；light_random 分组预计减少等待轮到用户时隙的时间，但须结合有限窗口内的实际交付量判断。以上是先验推测，不是实验结果。

新增项目脚本 `scripts/verify_baseline.py`，核查默认配置、场景/模型配对、原始生成/完成/丢弃/积压、每 tick 预算与缓存、JSON/CSV 一致性、PNG 解码，以及重复输出 SHA256。未改教师运行或绘图代码。

```powershell
& .\.venv\Scripts\python.exe -m pytest grading/test_circuit.py grading/test_packet.py grading/test_metrics.py -q
$env:MPLCONFIGDIR=(Join-Path (Get-Location) '.build/matplotlib')
& .\.venv\Scripts\python.exe src/performance_test.py
& .\.venv\Scripts\python.exe -m pytest grading/test_integration.py -q
& .\.venv\Scripts\python.exe -c "from src.performance_test import run; run('.build/repro')"
& .\.venv\Scripts\python.exe scripts/verify_baseline.py --repeat .build/repro
```

实际结果：分项 `11 passed in 0.07s`；集成 `3 passed in 0.05s`；两次仿真与核验退出码均 0。
`results/comparison.json` 有 config、8 rows、8 traces，每组 256 tick；CSV 有 8 条数据。
3 PNG 可实际解码，Codex 已逐一打开查看：指标图 2100×690、队列图 1350×600、PCM 图 1650×450，标注可读。
5 个基线文件的 SHA256 与 `.build/repro` 重复输出完全一致，详情见 `results/logs/05_artifact_verification.json`。
原始输出为 `results/logs/05_components.txt`、`05_simulation.txt`、`05_integration.txt`、`05_repeat.txt`、`05_verification.txt`。

初步结果：continuous 电路有效利用率 1.0、平均时延 2.5 ms，分组 0.796875、26.1471 ms；staggered_burst 电路 0.4921875、45.0952 ms、丢失率 0.18359375，分组 0.75、1 ms、无丢失。两者不是全场景固定优劣。完整数值见实际 CSV。
变更：本记录、项目核验脚本、`results/` 内 5 个基线产物和日志、`.build/repro/`。原始基线配置和教师业务均未变。无未解决问题。

## 阶段 06：自拟反例与参数实验（通过）

自拟输入（不是照抄公开测试）：packet，users=2、ticks=3、slot_bits=128、tick_ms=1、header_bits=32、buffer_payload_bits=200；到达依次为 (tick0,user1,payload200)、(tick1,user0,payload64)、(tick2,user0,payload200)。

先验手算：tick0 第一条 wire232 发128、剩104，仍占原始 payload200；tick1 先准入64，因200+64>200整条丢弃，随后发104并完成旧记录，释放缓存；tick2 新200被准入，发128后窗口截止，不排空。预期 wire 轨迹 [128,104,128]、缓存 [200,0,200]、生成464=交付200+丢弃64+积压200；平均和最大完成时延均2 ms，有效利用率200/384、线路忙碌率360/384、丢失率64/464。该组合能发现按剩余 wire 提前释放缓存、先发后准入、部分发送算交付或窗口排空错误。

按照本次用户“每阶段无需等待确认”的授权继续设计和验证；这不代表学生已确认理解该反例。报告和 AI 记录将标明由 AI 提出并执行验证，供本人复核。

参数实验利用既有 `Config(header_bits=...)` 和 `simulate` 接口，无须侵入框架；扫描 0/32/64 bit 包头，其他参数、种子和 Arrival 输入固定，保存到 `results/extra/`。

```powershell
& .\.venv\Scripts\python.exe -m pytest student_tests -q
& .\.venv\Scripts\python.exe scripts/header_experiment.py
& .\.venv\Scripts\python.exe -m pytest grading/test_integration.py -q
& .\.venv\Scripts\python.exe -m pip freeze
```

真实结果：自拟测试 `1 passed in 0.04s`，集成 `3 passed in 0.05s`；附加实验退出码 0，生成 3 个完整配置、24 行指标和24组轨迹。
原始输出：`results/logs/06_student_tests.txt`、`06_header_experiment.txt`、`06_integration.txt`。
输出 `results/extra/header_sweep.json`、`header_sweep.csv`、`header_sweep.png`；PNG 已实际打开查看，标注可读。
脚本验证同场景 Arrival 在全部参数与模型间完全相同，header32 的 rows/traces 与基线完全一致，三种配置的全部电路 raw 均一致，基线 5 文件 SHA256 未变，CSV24行和 PNG 解码有效。

连续负载的分组有效利用率随 header0/32/64 为 1/0.796875/0.6640625，平均时延 2.5/26.1470588/35.3705882 ms。错峰业务 header64 的有效利用率降为0.59765625、平均时延27 ms、丢失率0.0390625、积压4032 bit。轻载三种配置均交付6912 bit，但 header64 的平均时延由1.0972222增至2.125 ms，说明包头影响依赖负载及tick离散边界；不推断任意真实网络。
变更：`student_tests/test_my_case.py`、`scripts/header_experiment.py`、`requirements-lock.txt`（保存实际依赖版本）、本记录、附加产物及日志。无教师框架变更，无未解决测试问题。

## 阶段 07：报告与本地评分（本地验收通过）

已核对两份模板及报告检查/评分脚本。起始没有 REPORT.md、AI_LOG.md；新建报告，使用真实运行数据和用户提供的姓名学号，不复制覆盖个人既有文件。个人理解与反思没有由 AI 代为声明。

```powershell
& .\.venv\Scripts\python.exe grading/calculate_grade.py
$env:MPLCONFIGDIR=(Join-Path (Get-Location) '.build/matplotlib')
& .\.venv\Scripts\python.exe grading/calculate_grade.py
rg -n '填写|TODO|待补充|占位符' REPORT.md AI_LOG.md
```

首次评分退出码0，自动70分，但忘记给该进程设置MPLCONFIGDIR，Matplotlib尝试默认用户缓存被拒绝后自动使用临时目录`C:\Users\lenovo\AppData\Local\Temp\matplotlib-lymtq5gp`。随后明确设置项目`.build/matplotlib`重跑，退出码0、无该警告。已检查临时目录不存在（自动清理），没有迁移或修改用户级工具。两次输出分别保留`results/logs/07_grade_initial.txt`、`07_grade.txt`。

实际自动分：环境5/5、电路20/20、分组20/20、指标15/15、结果10/10，合计70/70；`grade_report.json`状态`ok`，manual_pending=30。脚本显示70.0/100，不是最终成绩。原始文件位于项目根目录`grade_report.json`、`grade_result.txt`。

另执行项目Python内联核验：以users=2/ticks=2仿真原先手算，断言利用率、线路量、两个时延及无丢失积压均匹配；结果保存`results/logs/07_handcalc_validation.json`。
首次自写占位符检查把所有“TODO”文本一概视作占位符，退出码1（`AssertionError`）。`rg`定位表明命中的是“修改三个TODO前”等真实过程描述，不是模板待填项。修正检查为模板的具体空白字段（如“姓名：填写”“需求与输入：填写”“待补充”），并重新运行全部内联核验，退出码0，手算匹配、两份文档无这些模板残留、自动分70且状态ok。保留`07_report_validation_initial.txt`和最终`07_report_validation.txt`，没有删除教师断言或掩盖实施错误。

变更：`REPORT.md`、`AI_LOG.md`、本记录，以及真实评分/手算核验日志。个人信息完整；没有编造个人反思、外部文献或人工成绩。本人理解与最终认可仍需本人提交前审阅，不据此声称学生已经掌握内容。

## 阶段 08：仅提交前检查（通过，停在授权节点）

按本次授权仅进行只读Git检查、运行测试和生成本地检查记录，不暂存、commit、push或创建PR。

新增`docs/submission_checklist.md`与项目脚本`scripts/preflight.py`，列明14个必需交付文件、配套脚本/报告/PRD、忽略规则和本人后续确认节点。

```powershell
$env:MPLCONFIGDIR=(Join-Path (Get-Location) '.build/matplotlib')
& .\.venv\Scripts\python.exe -m pytest grading student_tests -q
& .\.venv\Scripts\python.exe scripts/preflight.py
git status --short
git remote -v
git branch --show-current
git diff --stat
git diff --check
git diff --cached --stat
```

真实结果：完整公开grading（含作业跟踪测试）加student_tests，`24 passed in 0.37s`，退出码0；预检退出码0、status=passed。输出为`results/logs/08_full_tests.txt`、`08_preflight.json`和`08_preflight.txt`。

- 原13个grading/workflow文件SHA256与修改前一致，受保护目录没有新增未跟踪文件。
- 教师src中只有3个目标文件变化，原接口、docstring和TODO外模块结构不变。
- main与origin正确，HEAD仍为`bc9099e3f932168af640ce0d03abc2c3f283e10f`，暂存区为空。
- 基线文件哈希与阶段05一致，报告全部8行基线指标和12行分组参数指标与实际JSON一致，本文档和AI记录的文件链接存在，模板个人字段完整。
- 拟提交文件中常见GitHub/API令牌及私钥模式没有命中；此检查限于清单中的文件与具体模式，不声称能够排除一切敏感信息。
- 必需结果和附加实验均齐全。`.venv`与`.build`为项目级环境/缓存，未纳入清单；同学名单和无关材料未纳入本次变更。

阶段08仅检查的授权范围已完成。待本人审阅REPORT、AI_LOG与清单，确认理解和最终认可，并明确授权后才允许后续暂存、commit；push/PR另按本人授权进行。当前没有新提交SHA或PR网址，不报告任何GitHub评分结果。

## 审阅后的提交授权（2026-10-19）

用户随后明确回复“审阅完毕直接提交吧”，授权当前成果暂存、本地commit、推送本人Fork并在教师仓库建立PR。上述等待状态保留为首次检查时的历史记录，已由本次授权取代。
再次执行项目preflight检查通过；通过GitHub连接器确认登录账号erjimeidianle，教师仓库没有本人现有open PR。Git默认schannel访问远端出现SEC_E_NO_CREDENTIALS，单次命令使用`git -c http.sslBackend=openssl ls-remote origin refs/heads/main`后成功，远端main仍为起始bc9099e。没有关闭证书检查或更改全局设置。
Git未配置提交署名；本次commit仅通过`git -c user.name=郑航宇 -c user.email=299534429+erjimeidianle@users.noreply.github.com`使用本人提供的姓名及与已核验GitHub账号ID对应的隐私邮箱，不永久修改其他项目的身份配置。

本次提交将逐文件添加三个源文件、报告、AI记录、自拟测试、3个项目复现脚本、依赖锁定文件、项目解释器配置、执行记录和清单、报告所引PRD及其转换审计；基线5文件、附加实验3文件和本地原始日志按确切文件列表强制添加。其余原始阶段任务说明继续保留在本地，不把缓存或同学名单加入本次变更。实际提交SHA、PR网址和最新评分状态由后续Git/PR及本地`results/logs/09_submission_result.json`记录。

审阅后再次执行完整测试，`24 passed in 0.37s`，输出`results/logs/09_full_tests.txt`。暂存后默认`git diff --cached --check`发现REPORT和原始PRD中Markdown用于硬换行的双空格（退出码2）。未改动经审计的PRD，而新增项目`.gitattributes`声明Markdown允许行尾空格、`results/**`与原始任务Markdown按原始字节存储，避免Git自动换行转换破坏数据或PRD的SHA256。随后重新暂存，检查索引中的原始证据与工作区字节一致，并复核变更范围及凭据模式，再创建commit。

## 提交格式更正 2026-10-19

用户澄清：GitHub只提交原Markdown报告，Word为本地留存、之后由本人发邮件给老师。此前AI将Word版本作为68ea81f推送；本次不改写远端历史，新增更正提交，从最新Git文件列表移除`reports/实验一报告_郑航宇_2024280087.docx`、3个Word制作渲染脚本及Word验证摘要，并恢复Word改动前的项目属性和提交清单。通过`git rm --cached -- <确切文件>`保留所有本地副本；本地.git/info/exclude增加确切Word及脚本规则，不上传这些本地规则。

REPORT.md、3个仿真函数、原基线产物、教师文件均保持原样；更正说明保留在AI_LOG和本记录，未掩盖已发生的Word制作及误推送。用户未委托AI发邮件，本次没有邮件操作。拟通过普通commit和push更新main，无强制推送。

浏览器重试仍被已保存的权限设置或管理策略拒绝：https://github.com。未通过其他浏览器或隐蔽网络调用绕过；教师仓库PR尚未创建。
