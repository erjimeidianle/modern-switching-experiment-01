# 电路交换与分组交换

实验一 实验规范和操作文档

现代交换原理  
基于 Vibe Coding 的仿真实验与 GitHub 自动评分

文档版本：V1.2  
文档日期：2026-10-18  
实验时长：100分钟

# 目录

1 教学目标和实验范围

2 模型和数据约定

3 功能需求和函数接口

4 基线业务场景

5 指标和输出字段

6 验收用例和完成标准

7 交付物和开发流程

8 评分和教师复核

9 课堂实施和期末项目衔接

10 依据和版本维护

> 11 GitHub实验操作指南
>
> 11 GitHub操作指南 环境与任务定位
>
> 11 GitHub操作指南 实现与验证
>
> 11 GitHub操作指南 报告与本地提交
>
> 11 GitHub操作指南 上传与创建PR
>
> 11 GitHub操作指南 评分与补交
>
> 11 GitHub操作指南 常见问题

首次实验建议按第11章逐步操作；第1至10章用于核对模型、任务、验收与评分要求。

本PRD规定实验一教学仿真程序的目标、模型、功能、验收和交付要求，供学生、教师及AI编程助手共同使用。学生在现有仓库中补全三个函数，以相同业务比较两种资源分配方式，形成可复现的代码、数据、图表和分析。验收依据是模型约定与验证证据，不预设某种交换方式始终更高效。

# 1 教学目标和实验范围

## 1.1 学习目标

- 解释固定时隙预留与共享FIFO的资源使用差异，识别统计复用收益和包头代价。

- 分别计算有效载荷利用率、线路忙碌率、完成时延、丢失率与积压，并解释指标之间的关系。

- 先给出手算预期，再用小用例和自动测试核验AI辅助生成的实现。

- 使用Fork、PR和反馈记录迭代过程，为期末数字程控交换机准备资源服务和性能观察模块。

## 1.2 实施范围和角色

实验采用Python命令行仿真。教师提供数据类型、业务生成、缓存准入、时钟、PCM辅助工具和绘图；学生实现三个TODO并完成验证与分析。学生负责可解释的实现和真实成果，教师负责模型讲解、运行审批、人工评分与结论复核。AI助手可以解释和建议实现，学生承担采纳与验证责任。

本实验不要求Web界面、数据库、真实电话接续或SIP协议，不模拟传播、误码、重传、多跳路由或建链时延。基础模型假定单链路承载已建立，不据此评价真实互联网或电信系统的总体优劣。

Python要求3.10及以上，建议3.12。依赖以requirements.txt为准。参考课堂120分钟，环境配置尽量课前完成；若课时90分钟，可把自拟反例和报告安排到课后，截止时间由教师另行通知。

# 2 模型和数据约定

| **参数或规则** | **基线要求**                                                  |
|----------------|---------------------------------------------------------------|
| 用户           | 4名，编号0至3；cfg.users＝4                                   |
| 时钟           | 256个tick，每tick 1 ms，观察窗口为\[0,256)                    |
| 链路容量       | 每tick最多128 bit，抽象链路速率128 kbit/s                     |
| 电路服务       | 当前服务用户＝tick % users，其他用户不能借用空时隙            |
| 分组服务       | 共享FIFO，每条记录初始化一次32 bit包头，可跨tick续传          |
| 缓存配额       | 两模型均为4096 bit有效载荷预留空间，包含在传记录              |
| 事件顺序       | tick开始先准入到达记录，再执行发送，完整记录在tick＋1边界交付 |
| 同刻到达       | 保持输入顺序；两模型使用同一份Arrival序列                     |
| 窗口结束       | 立即停止，不追加排空；未完成记录计积压                        |

## 2.1 数据类型和计量单位

Config保存users、ticks、slot_bits、tick_ms、header_bits和buffer_payload_bits。Arrival保存tick、user和payload_bits；Pending保存user、arrival_tick、payload_bits和remaining_wire_bits。bit表示比特，ms表示毫秒，tick表示离散时钟编号。单个tick的容量由slot_bits决定，不能与用户数量相乘。

## 2.2 缓存准入和完成规则

记录到达时，若“已预留payload＋本条payload”超过总缓存，就整条尾丢弃。已发送但尚未完整交付的记录仍占用原始payload配额，完整交付后才释放。分组包头占用线路发送容量，但不占本模型的payload缓存配额。这是为公平比较选定的课堂模型，不等同于真实设备的所有存储计量方式。

发送函数只处理已准入队列。一次tick可发送多条完整记录，也可部分发送一条；预算用完立即结束。所有完成记录都在tick结束边界计时。改变包头或缓存的附加实验应单独注明参数，不能混入基线8组结果。

# 3 功能需求和函数接口

## FR01 固定时隙电路发送

文件 src/part1_circuit.py

接口 serve_circuit(queues, tick, cfg)

返回 (wire_bits, completed_records)

queues是每用户一个deque\[Pending\]的列表，函数原地更新当前服务用户队列。发送总量不得超过cfg.slot_bits。当前用户队首完成后才能弹出并加入完成列表，剩余预算可继续发送该用户下一条记录。当前队列为空时返回(0, \[\])，其他用户等待。部分发送时只扣减remaining_wire_bits，不更改payload_bits。

验收证据：grading/test_circuit.py包含空闲、指定用户、跨tick续传和FIFO预算4项检查。禁止把空时隙自动让给其他用户，也不能把部分发送记录误报为完成。

## FR02 共享FIFO分组发送

文件 src/part2_packet.py

接口 serve_packet(queue, tick, cfg)

返回 (wire_bits, completed_records)

queue是共享deque\[Pending\]。remaining_wire_bits已由框架初始化为payload_bits＋header_bits，函数不能再加头。必须先发完队首，再服务下一条；大记录可以跨tick发送，不抢占、不交错、不因长度超过一个tick而丢弃。发完队首后有剩余预算时，应继续处理下一条。空队列返回(0, \[\])。

验收证据：grading/test_packet.py包含空闲、包头只计一次、FIFO不交错和共享预算4项检查。wire_bits是本tick实际发送的线路比特数，必须为整数且在0到slot_bits之间。

## FR03 指标统计和守恒检查

文件 src/metrics.py

接口 summarize(raw, cfg)

返回 包含第5节规定键名的字典

只使用观察窗口内原始统计量和已完成记录。完成时延为delay_ticks × tick_ms。无完成记录时，平均和最大时延返回None；无生成payload时，丢失率返回0。若生成payload不等于交付、丢弃和积压之和，必须抛出ValueError。不得用0替换无送达样本来制造低时延结果。

## FR04 业务运行和可复现实验结果

保留现有performance_test.py流程，依次运行第4节四类业务，并对同一Arrival输入运行circuit和packet两种模型，生成8行指标和8组轨迹。随机种子固定为2026，图表由本人的实现生成，重复运行相同参数应得到相同结果。

## FR05 验证证据和提交反馈

学生至少完成一组2用户手算、一个自拟反例和一项参数变化分析。提交应同时包含源代码、结果、报告和AI协作记录。教师仓库的PR触发自动评分，当前head SHA的机器人反馈写入在线跟踪表；新提交待评分时不沿用旧SHA成绩。模拟学生流程测试与真实37人记录分开。

# 4 基线业务场景

| **业务标识**       | **产生规则**                                     | **主要观察**           |
|--------------------|--------------------------------------------------|------------------------|
| continuous         | 每4 tick所有用户各生成128 bit记录                | 连续满载下的包头开销   |
| staggered_burst    | 每tick一条96 bit记录，活跃用户每64 tick轮换      | 突发热点与固定资源预留 |
| synchronized_burst | 每80 tick，各用户集中到达8条96 bit记录           | 集中排队与窗口末尾积压 |
| light_random       | 每用户每tick以0.08概率生成96 bit记录，seed＝2026 | 轻载下的利用率与时延   |

每个场景都应先预测，再运行，再解释。不同场景使用相同配置，场景内两模型必须保持业务序列、容量、缓存和时长一致。不能通过改变输入负载、给一种模型增加排空时间或漏掉包头来形成优势。

# 5 指标和输出字段

| **返回键名**         | **计算口径**                                                        |
|----------------------|---------------------------------------------------------------------|
| payload_utilization  | 完整交付payload bit ÷ (ticks × slot_bits)                           |
| wire_utilization     | 实际wire发送bit ÷ (ticks × slot_bits)，含包头和未完成记录已发送部分 |
| mean_delay_ms        | 已完成记录delay_ticks的平均值 × tick_ms，无完成记录为None           |
| max_delay_ms         | 已完成记录最大delay_ticks × tick_ms，无完成记录为None               |
| loss_ratio           | 尾丢弃payload ÷ 生成payload，无生成payload时为0                     |
| backlog_payload_bits | 窗口结束所有未完成记录的原始payload总和                             |

守恒式：generated_payload_bits＝delivered_payload_bits＋dropped_payload_bits＋backlog_payload_bits。部分发送记录的全部原始payload仍属于积压，不把已发出的部分payload重复计入交付。完成时延必须和交付量、丢失和积压一起解读，避免只因少量记录完成就宣称系统时延更好。

# 6 验收用例和完成标准

| **编号** | **输入或条件**                             | **必须满足的结果**                             |
|----------|--------------------------------------------|------------------------------------------------|
| AC01     | 当前服务用户队列为空，其他用户有数据       | 电路本tick发送0，其他用户记录保持等待          |
| AC02     | 电路当前用户一条200 bit记录，容量128       | 首tick发送128，剩余72；后续可服务tick再完成    |
| AC03     | 分组payload 96，初始化wire为128            | 一个tick发送128并完成，不能再次加32 bit        |
| AC04     | 共享FIFO中A wire 232、B wire 64            | 首tick A余104、B不变；次tick发A104和B24，B余40 |
| AC05     | 共享FIFO两条wire均48，预算128              | 本tick完成两条，实际发送96，不能固定只发一条   |
| AC06     | 分组payload 200，窗口仅1 tick，wire初值232 | wire发送128，交付0，积压200，平均时延None      |
| AC07     | 缓存100，同tick先到80后到40                | 先准入80，再整条丢弃40；准入先于当tick发送     |
| AC08     | 无生成、无完成、无丢弃、无积压             | 利用率与丢失率为0，平均与最大时延None          |
| AC09     | 生成400、交付200、丢弃100、积压99          | 守恒不成立，summarize抛ValueError              |
| AC10     | 四场景 × 两模型，默认配置和种子            | 产生8行结果、8组轨迹，重复运行可复现           |

## 6.1 两用户手算基准

设2用户、2 tick、每tick 1 ms且容量128 bit，包头32 bit，缓存足够。只有tick 0的用户1到达一条96 bit记录。电路tick 0闲置、tick 1发送并于2 ms完成；分组tick 0发送128 bit并于1 ms完成。两者有效利用率均为96/256＝37.5%，电路和分组线路忙碌率分别为37.5%和50%。该例说明相同有效利用率不代表相同时延。

## 6.2 学生自拟反例

在student_tests/test_my_case.py中给出明确输入、先手算的预期及assert断言，并说明它能揭示的错误。可选择重复加头、错误借用电路时隙、部分发送误记交付或漏算积压之一。测试应验证模型规则，不能只检查文件存在或照抄实现。

# 7 交付物和开发流程

| **交付物**                    | **要求**                                                           |
|-------------------------------|--------------------------------------------------------------------|
| 三个任务源文件                | 补全原函数，保留接口和字段，不修改教师测试、评分或工作流           |
| results/comparison.json       | config、8行rows和8组traces；数据守恒成立                           |
| results/comparison.csv        | 8组指标，单位与字段一致                                            |
| 3张PNG                        | comparison_metrics.png、queue_occupancy.png、pcm_frame_view.png    |
| REPORT.md                     | 目的、模型、手算、结果、反例、局限、AI说明及实际参考资料           |
| AI_LOG.md                     | 工具或未使用AI的说明；至少一项真实需求、建议、验证和采纳或修正理由 |
| student_tests/test_my_case.py | 至少一项独立反例，能够运行并说明断言依据                           |
| 参数变化证据                  | 改变包头或缓存等参数，结果放results/extra/并说明条件               |

先通过环境检查和4项框架测试，保留模板正常起点；再按电路、分组、指标分别实现并测试；随后运行完整仿真与集成测试，补充反例和报告。初始TODO导致核心测试失败属预期，不应通过修改测试消除失败。

python -m pytest grading/test_circuit.py grading/test_packet.py grading/test_metrics.py -q

python src/performance_test.py

python -m pytest grading/test_integration.py -q

python -m pytest student_tests -q

python grading/calculate_grade.py

以上python应为项目.venv解释器。第11章提供可直接照做的GitHub操作流程和Windows PowerShell命令；初次实验请从11.1开始，依次完成至11.16。

## 7.1 AI协作约束

提示词应包含目标函数、数据类型、模型约定和验证条件，一次只补全一个函数。学生先手算，再阅读代码差异并运行测试。首次AI建议正确也要记录边界验证，不编造错误或聊天记录。不得把完整任务委托给AI后跳过理解，也不能用教师示例图冒充自己的运行结果。

提示词示例

请先阅读README、src/models.py和serve_packet的docstring。

先说明输入输出与跨tick续传规则，再只补全该函数。

remaining_wire_bits已含一次包头，不修改教师测试或接口。

请解释AC04的预期，并说明如何验证。

## 7.2 GitHub提交和成绩记录

学生Fork教师仓库并Clone到本地，在个人Fork的main分支开发。代码和报告正常git add，默认忽略的结果需单独执行`git add -f results/*.png results/*.json results/*.csv`，再commit和push。向教师仓库main创建PR，标题为“现代交换实验01-姓名-学号”。后续补交推送原分支即可，无需重复新建PR。

教师仓库已启用Actions，首次贡献者可能需要教师点击Approve workflows。自动分可查PR机器人评论、Actions Summary及grading-report附件；最新37人记录位于Issue \#2和tracking-table附件。Excel是教师人工登记簿，不自动同步云端。未提交与未评分应保持明确区别，未评分不得填为0分。

# 8 评分和教师复核

| **评分项**       | **分值** | **验收方式**                               |
|------------------|----------|--------------------------------------------|
| 环境可运行       | 5        | 自动环境检查                               |
| 电路发送         | 20       | 4项公开测试，按通过比例给分                |
| 分组发送         | 20       | 4项公开测试，按通过比例给分                |
| 指标统计         | 15       | 3项公开测试，按通过比例给分                |
| 结果数据和3张图  | 10       | 自动检查JSON和图片，教师复核真实性与一致性 |
| 自拟反例与断言   | 5        | 教师检查输入、预期、断言及揭示的错误       |
| 实验报告         | 15       | 教师检查模型、手算、结果解释及局限         |
| AI协作与逻辑解释 | 10       | 教师检查真实协作证据和核心循环解释         |
| 基础合计         | 100      | 自动70＋人工30                             |

选做参数扫描或进一步对比最多加10分，最终成绩＝min(100, 自动分＋人工分＋选做加分)。基础内容完整即可获得100分，选做不是满分前提。自动报告中的“x/100”只表示已获自动项，不能当作最终分。

教师人工30分可按以下口径复核：反例的手算与有效断言5分；报告中模型与手算5分、结果解释7分、限制与可复现说明3分；AI协作真实性4分、核心逻辑解释6分。该细分为本PRD建议，正式评价仍按课程公布口径执行。学生未使用AI时，可用独立实现和调试记录说明验证过程，不因未使用某项付费工具扣分。

# 9 课堂实施和期末项目衔接

| **阶段**       | **建议时间** | **课堂检查点**                         |
|----------------|--------------|----------------------------------------|
| 原理与手算     | 20分钟       | 先预测两个模型，解释37.5%和时延差异    |
| 模板与参考结果 | 15分钟       | 确认环境、函数位置和公平比较条件       |
| 实现与分项验证 | 55分钟       | 逐个实现三个TODO，检查失败断言         |
| 反例与参数分析 | 20分钟       | 说明一项反例，核对图表与数据           |
| 提交与反馈     | 10分钟       | 教师仓库出现PR，能定位评分或待审批状态 |

教师开场可提问“同样链路容量，哪种交换方式一定更高效”，在四场景结果后要求学生附条件作答。遇到低平均时延，应追问“有多少数据真正完成、还有多少积压或丢弃”。课堂时间不足时先完成可验证的核心函数和阶段PR，报告及选做按课程通知课后补交。

后续实验将复用Config、Arrival、Pending、时隙索引、发送预算和事件时间，逐步加入T/S交换网络、呼叫状态机与资源释放。期末项目可复用利用率、队列和守恒观察方法，但不能直接把本实验的单链路服务函数当作完整数字程控交换机。PCM辅助示例32时隙×8 bit×8000帧/s＝2.048 Mbit/s，与本实验128 kbit/s比较模型分别说明。

# 10 依据和版本维护

本PRD以实验一仓库现有README.md、docs/model_contract.md、src/models.py、src/utils.py、三个任务文件的docstring、公开grading测试和评分脚本为依据。教学基线对应已验证提交bc9099e。若教师调整接口、业务或评分，应同步更新PRD、课件、代码和验收用例；需求与代码发生冲突时先向教师确认，不能自行篡改测试规则。

课程仓库 [https://github.com/jwentong/modern-switching-experiment-01](https://github.com/jwentong/modern-switching-experiment-01)

在线记录 [https://github.com/jwentong/modern-switching-experiment-01/issues/2](https://github.com/jwentong/modern-switching-experiment-01/issues/2)

流程验收 docs/submission_workflow_verification.md。教师参考结果来自examples/teacher_results/comparison.json及comparison.csv；参考值用于讨论和核对模型，不替代学生自己的实验产物。

# 11 GitHub实验操作指南

本章面向第一次使用GitHub的同学。按顺序完成环境准备、三个函数、结果验证、报告和PR提交；每一步达到“完成标志”后再继续。GitHub保存和协作代码，Git负责本地版本记录；本地运行正确后仍须把作业提交到教师仓库的PR。

## 11.1 准备账号和工具

在浏览器注册并登录自己的GitHub账号，完成邮箱验证。准备Git、Python 3.12及VS Code。Git官网下载地址为[https://git-scm.com/downloads](https://git-scm.com/downloads)，Python为[https://www.python.org/downloads/](https://www.python.org/downloads/)，VS Code为[https://code.visualstudio.com/](https://code.visualstudio.com/)。安装Python时勾选Add Python to PATH；安装后重新打开终端。

git --version

python --version

完成标志：终端显示Git版本和Python 3.10及以上版本，建议3.12。命令应在PowerShell输入，不是在Python的\>\>\>提示符输入。以下命令逐行执行，不复制序号或提示符。

## 11.2 在浏览器中Fork教师仓库

打开[https://github.com/jwentong/modern-switching-experiment-01](https://github.com/jwentong/modern-switching-experiment-01)。点击右上角Fork，再选择Create a new fork；Owner选择自己的账号，仓库名保留modern-switching-experiment-01，点击Create fork。已有同名Fork时直接使用已有仓库。

完成标志：浏览器地址为github.com/你的用户名/modern-switching-experiment-01，页面显示forked from jwentong/modern-switching-experiment-01。不要用Download ZIP代替Fork和Clone。

## 11.3 将个人Fork克隆到本机

在个人Fork点击Code，选择HTTPS并复制地址。在电脑创建自己的课程目录，在该目录打开PowerShell。下面YOUR-USERNAME必须替换成自己的GitHub用户名，也可直接粘贴刚复制的HTTPS地址。

```powershell
git clone https://github.com/YOUR-USERNAME/modern-switching-experiment-01.git
```

cd modern-switching-experiment-01

git remote -v

完成标志：当前目录能看到README.md、src和requirements.txt；origin指向自己的Fork。后续所有终端命令都在这个仓库根目录执行。

# 11 GitHub操作指南 环境与任务定位

## 11.4 打开项目并设置提交署名

VS Code选择File → Open Folder，打开刚克隆的modern-switching-experiment-01文件夹；选择Terminal → New Terminal。下面署名和邮箱替换为自己的信息。邮箱可使用GitHub Settings → Emails中提供的隐私邮箱。

git config user.name "YOUR-NAME"

git config user.email "YOUR-EMAIL"

git branch --show-current

完成标志：VS Code左侧能看到src、grading、student_tests等目录，当前分支是main。署名只标记提交作者，不能代替GitHub登录。

## 11.5 创建独立Python环境

在VS Code的PowerShell终端逐行运行。后续直接调用虚拟环境中的python.exe，无须先激活环境，可以避免PowerShell激活策略问题。

python -m venv .venv

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```powershell
.\.venv\Scripts\python.exe src/test_environment.py
```

```powershell
.\.venv\Scripts\python.exe -m pytest grading/test_framework.py -q
```

按Ctrl+Shift+P，选择Python: Select Interpreter，选本项目.venv中的解释器。安装依赖时等待命令完成，再执行下一条。

完成标志：环境检查无报错，框架测试显示4 passed。三个TODO尚未实现，此时核心测试失败或完整仿真提示NotImplementedError属于正常起点。

## 11.6 找到本次需要修改的文件

先阅读README.md、docs/model_contract.md、src/models.py及三个任务函数的说明。按第6.1节完成两用户手算，再依次补全src/part1_circuit.py中的serve_circuit、src/part2_packet.py中的serve_packet、src/metrics.py中的summarize。

一次只修改一个函数，保存后测试。不修改grading目录、.github/workflows、教师接口或评分脚本来提高分数。不要把参考图直接复制成自己的结果。

完成标志：能指出三个TODO的位置，并说明固定时隙、共享FIFO和包头只计一次的规则。

# 11 GitHub操作指南 实现与验证

## 11.7 完成电路交换函数

在src/part1_circuit.py实现serve_circuit。可让AI先解释输入输出和队列更新，再建议实现；自己核对tick % users、发送预算和跨tick剩余量。按Ctrl+S保存后运行：

```powershell
.\.venv\Scripts\python.exe -m pytest grading/test_circuit.py -q
```

完成标志：4项电路测试通过。失败时阅读FAILED后的用例名和assert差异，回到函数修正，再运行同一命令。不要直接删除断言。

## 11.8 完成分组交换与指标函数

先实现serve_packet，确认remaining_wire_bits已经包含包头；再实现summarize，核对None、守恒和积压口径。分别保存并运行：

```powershell
.\.venv\Scripts\python.exe -m pytest grading/test_packet.py -q
```

```powershell
.\.venv\Scripts\python.exe -m pytest grading/test_metrics.py -q
```

完成标志：分组4项、指标3项测试通过。让AI协助时附上模型约定、报错和自己手算的预期，只修改对应任务函数，并在AI_LOG中记录实际验证过程。

## 11.9 生成并检查实验结果

```powershell
.\.venv\Scripts\python.exe src/performance_test.py
```

```powershell
.\.venv\Scripts\python.exe -m pytest grading/test_integration.py -q
```

在results目录逐一打开comparison.csv、comparison.json和3张图片：comparison_metrics.png、queue_occupancy.png、pcm_frame_view.png。CSV应有四场景×两模型共8行数据，表头不计入8行；JSON应有配置、8行指标和8组轨迹。

完成标志：集成3项测试通过，5个结果文件齐全，图片可以打开。能够用数据解释“哪一种方式在什么业务和指标下更高效”，而不是只看线路忙碌率。

## 11.10 编写自己的反例测试

在VS Code的student_tests目录右键New File，创建test_my_case.py。按第6.2节选择一个错误边界，先写明确输入和手算预期，再写以test_开头的测试函数和assert；可参考AC04，但须说明断言为何成立。运行：

```powershell
.\.venv\Scripts\python.exe -m pytest student_tests -q
```

完成标志：至少有1项自己编写的有效测试通过；若显示no tests ran，检查文件名和函数名。只有文字说明或运行教师测试不算完成本项。

# 11 GitHub操作指南 报告与本地提交

## 11.11 完成报告和AI协作记录

首次创建报告时执行下面两条命令；如果REPORT.md或AI_LOG.md已经存在，直接编辑，不要重新复制覆盖已有内容。

Copy-Item REPORT_TEMPLATE.md REPORT.md

Copy-Item AI_LOG_TEMPLATE.md AI_LOG.md

在REPORT.md填入真实运行参数、两用户手算、四场景结果分析、自拟反例和模型局限。完成一项包头或缓存参数变化分析，将附加结果单独保存在results/extra/，保留默认基线的8组结果。AI_LOG.md记录真实提示、建议、测试与采纳或修正理由；未使用AI则说明独立实现和调试过程。

```powershell
.\.venv\Scripts\python.exe grading/calculate_grade.py
```

完成标志：报告没有待填写占位符，数据与图片一致；本地评分可查看grade_result.txt和grade_report.json。自动项最高70分，另有教师人工30分；本地分数和绿色运行状态都不代表最终成绩。

## 11.12 暂存并提交本地成果

保存所有文件后运行以下命令。git add把文件加入本次提交，git commit只记录到本地；下一步push才会上传。结果目录默认被忽略，必须对规定的结果文件单独使用-f。

git status --short

git add src/ REPORT.md AI_LOG.md student_tests/

`git add -f results/*.png results/*.json results/*.csv`

git diff --cached --stat

附加实验的文件另行逐个添加，例如git add -f results/extra/你实际生成的文件名。先把示例文件名替换为真实文件名。确认暂存列表包含自己的源代码、报告、反例和5个结果文件，然后执行：

git commit -m "Complete experiment 01"

完成标志：出现新的commit编号和文件变更摘要。不要上传.venv、缓存、密码、API密钥或同学名单；不要对整个仓库使用git add -f。

# 11 GitHub操作指南 上传与创建PR

## 11.13 推送到自己的GitHub仓库

git push origin main

若要求认证，按Git Credential Manager提示在浏览器登录自己的账号；网页账号密码不能直接充当Git HTTPS推送密码。不要把令牌或密码粘贴到AI聊天、代码或报告中。推送失败时先看报错，不反复使用强制推送。

完成标志：终端显示推送成功。刷新个人Fork，能看到最新commit以及REPORT.md、AI_LOG.md、student_tests/test_my_case.py和results中的5个结果文件。只有本地commit而未push，教师看不到作业。

## 11.14 向教师仓库创建Pull Request

在个人Fork点击Contribute → Open pull request；也可以进入教师仓库的Pull requests → New pull request → compare across forks。创建前逐项核对以下方向：

base repository：jwentong/modern-switching-experiment-01；base：main。

head repository：你的账号/modern-switching-experiment-01；compare：main。

先看Files changed，确认包含自己的实现、报告、测试和结果，没有私人文件。点击Create pull request，标题填写“现代交换实验01-姓名-学号”，姓名和学号使用本人信息。正文可按下列结构填写自己的实际情况：

完成情况：三个函数、报告、AI记录、自拟测试及结果文件。

验证结果：列出实际运行的测试及通过情况。

结果说明：简述观察到的效率与时延差异。

待解决问题：如有失败，写明错误与已尝试的排查。

再次点击Create pull request后，保存该PR网址。不要自行合并到教师main，教师会按课程安排审阅。

完成标志：PR网址位于github.com/jwentong/modern-switching-experiment-01/pull/编号；标题含本人姓名和学号。只推送个人Fork、只在自己仓库创建PR或只发截图都不算提交到教师仓库。

如果页面提示There isn’t anything to compare，先核查推送是否成功、选择的head仓库是否是自己的Fork，以及是否已经修改并提交任务文件。已有同分支PR时继续更新原PR。

# 11 GitHub操作指南 评分与补交

## 11.15 查看自动评分和成绩记录

在教师仓库PR页面查看Checks或机器人评论；也可打开教师仓库Actions，找到对应PR和最新提交的“自动评分系统”运行。进入该次运行查看Summary，并在Artifacts下载grading-report，解压查看grade_result.txt、grade_report.json及测试日志。

第一次向教师仓库贡献时，可能显示等待Approve workflows。此时保留PR并告知教师批准；学生无需申请仓库写权限、配置教师密钥或自行更改工作流。运行中或等待批准表示尚未得到本次成绩，不应记作0分。

核对反馈中的提交SHA与PR最新commit一致。自动评分完成后，“PR评分反馈”和“作业情况实时跟踪”还需要继续运行，评论和记录可能稍后出现。Actions显示绿色，只表示流程正常结束，仍须阅读分项得分。

37人最新提交记录入口：[https://github.com/jwentong/modern-switching-experiment-01/issues/2](https://github.com/jwentong/modern-switching-experiment-01/issues/2)。也可在“作业情况实时跟踪”运行中查看Summary或下载tracking-table附件。Excel登记簿由教师维护，不会随PR自动更新。

完成标志：能找到自己最新提交对应的自动分或明确的待评分状态，并区分自动70分和教师人工30分。没有评论时先查教师仓库本次评分的Summary和附件。

## 11.16 按反馈修正并更新同一个PR

先看失败测试和差异，回到本地修改对应函数；保存后重跑相关测试。源代码修改后重新运行完整仿真，确保结果文件与代码一致，并更新报告及AI记录。再执行11.12的暂存命令，然后：

git commit -m "Fix experiment 01 after feedback"

git push origin main

完成标志：原PR自动出现新commit，评分重新触发，无须另建PR。新提交评分完成前，旧SHA成绩不能视为本次成绩。最终截止时间以教师通知为准。

## 提交前逐项确认

① 个人Fork与教师PR方向正确，PR标题含姓名和学号。  
② 三个任务函数已实现，分项和集成测试已运行。  
③ 默认基线8组数据和3张图片已实际生成并上传。  
④ student_tests/test_my_case.py有手算依据和有效断言。  
⑤ REPORT.md与AI_LOG.md内容真实完整，附加参数结果单独保存。  
⑥ 最新commit已push，已查看教师仓库最新SHA对应的反馈。

# 11 GitHub操作指南 常见问题

## 命令找不到或依赖安装在错误环境

git或python不是可识别命令：确认工具已安装，关闭并重开VS Code终端，再运行版本检查。若python仍不可用而py --version能显示正确版本，可用py -3.12 -m venv .venv创建环境；之后仍使用本章的.venv解释器命令。缺少模块时运行`.\.venv\Scripts\python.exe` -m pip install -r requirements.txt，不要混用其他Python的pip。

## 找不到requirements或任务文件

终端通常进入了错误目录。运行Get-Location和Get-ChildItem检查当前位置；使用cd进入同时包含README.md、requirements.txt和src的项目根目录。不要进入src目录后再照抄本章命令。

## 测试失败但不知道从哪里改

先确认Ctrl+S保存。定位FAILED用例、实际值和预期值，再用第6节手算复现。NotImplementedError通常表示对应TODO未完成；包头重复计入、预算超额、部分发送误记交付和守恒不成立，应回到模型规则排查。向AI提问时提供必要报错及函数，不上传账号凭据。

## 本地有图片但GitHub没有

results默认被Git忽略。重新执行11.12中针对结果文件的git add -f命令，确认git diff --cached --stat包含它们，再commit和push。若git提示nothing to commit，检查文件是否已保存、是否在正确仓库，以及是否已经暂存。

## 推送失败或PR没有自动评分

先核对origin是自己的Fork，并按登录提示认证。若报non-fast-forward，停止强制推送，记录报错请教师协助核对远端改动。评分未出现时检查PR是否在教师仓库、是否有新commit、是否等待教师批准；不要通过修改.github/workflows来绕过问题。

## 遇到问题如何向教师求助

提供本人PR网址、最新commit编号、执行的命令、完整错误文本和已尝试的方法。描述希望得到的结果与实际结果；不要只写“不能运行”。保留原PR和错误证据，便于教师定位同一次提交。

## GitHub官方操作参考

Fork仓库：[https://docs.github.com/en/pull-requests/how-tos/work-with-forks/fork-a-repo](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/fork-a-repo)  
从Fork创建PR：[https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request-from-a-fork](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request-from-a-fork)  
批准Fork工作流：[https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks)

版本1.1修订：新增第11章学生逐步操作指南，保留原有模型、验收和评分要求；代码教学基线仍为bc9099e。GitHub界面文字可能随语言设置变化，以仓库、分支和提交方向为准。
