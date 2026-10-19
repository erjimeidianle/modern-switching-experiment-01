# AI协作记录

日期：2026-10-19。工具：Codex（本次会话）。学生：郑航宇，2024280087。
本记录由AI根据实际对话、修改和工具输出整理，不是逐字聊天转录，也不表示学生已经独立理解全部实现。

## 真实需求与授权边界

用户要求先完整阅读总览、PRD和01—08任务文件，再严格依序实施；每阶段测试通过才继续；保留真实结果、逐阶段命令和日志；不修改教师测试、评分脚本、工作流或原接口；禁止自动commit、push、PR，08只做预检。用户另外提供姓名郑航宇、学号2024280087。

AI实际完整阅读上述文件，以及README、模型合同、数据类型、三个函数docstring、公开分项和集成测试、运行和绘图源码、报告模板、评分脚本。总览引用的完整版文件名与实际文件不同，AI核对SHA256与转换审计完全相同，因此使用实际完整PRD，未修改原文。

## 先验推演与逐函数验证

1. 在修改TODO之前，AI按定义列出两用户手算：电路tick0空闲、tick1发96，于2 ms完成；分组tick0发128含头，于1 ms完成。两者有效利用率37.5%，线路忙碌率37.5%/50%。该推演写入docs/execution_log.md；不声称由学生独立作出。
2. AI建议电路只选择`queues[tick % users]`，在该队列按FIFO扣预算，不借用空时隙；用户200 bit首次发送128后剩72。只补此函数，查看diff后运行`-m pytest grading/test_circuit.py -q`，真实4 passed。
3. AI建议分组沿用共享deque和已含头部的remaining_wire_bits，不二次加头。先推演A232、B64的两tick分配，以及两条48共发96。只补此函数后运行`-m pytest grading/test_packet.py -q`，真实4 passed。
4. AI建议先核对生成=交付+丢弃+积压，再计算六指标。部分发送仍是全部原始payload积压；无完成样本时延None；无生成丢失率0。只补summarize后运行`-m pytest grading/test_metrics.py -q`，真实3 passed。

采纳依据是符合模型合同、先验小例子及对应边界测试通过。三个TODO的首次实现均通过公开测试，没有为记录“修正过程”而虚构失败。未修改任何教师grading、workflow、业务生成、数据类型或接口。

## 环境探测中的真实错误

系统Python3.14.5没有numpy、matplotlib、pytest。AI先检查系统工具和E:\workplace\codex-tools；尝试只读导入共用NumPy2.5.0失败：`No module named 'numpy._core._multiarray_umath'`。核对发现扩展为cp312，与cp314不兼容，故放弃复用该二进制，保留共用环境。

AI使用系统Python创建项目`.venv`，通过pip dry-run确认cp314兼容轮子，安装requirements范围内依赖。实际NumPy2.5.4、Matplotlib3.11.2、pytest9.1.1。环境检查输出“环境配置正确”，框架测试4 passed。下载和图形缓存放项目`.build/`，没有升级Anaconda或应用内部运行库。

PowerShell直接读取GitHub REST仓库元数据曾报`Authentication failed, see inner exception`，其null输出未用于结论。随后使用已有GitHub连接器只读核验登录账号与Fork来源成功：erjimeidianle，parent为教师jwentong仓库。未修改登录配置或索取凭据。

## 仿真、反例和参数实验

AI先写四场景条件性预测，分项复测11 passed后运行教师原始performance_test.py。实际生成8行指标、8组轨迹、3张图。集成3 passed。另用原入口的output参数输出到`.build/repro/`，5产物SHA256完全一致。AI新增核验脚本检查JSON/CSV、每tick预算、守恒、PNG解码，并逐一打开3图查看。

AI自拟的组合反例采用packet、3tick、200bit缓存：tick0到200、tick1到64、tick2再到200。先推导发送[128,104,128]、缓存[200,0,200]，生成464=交付200+丢弃64+积压200，完成样本delay2。之后写student_tests/test_my_case.py并运行，真实1 passed。它针对在传缓存过早释放、准入/发送顺序颠倒、部分发送算完成、窗口后排空，未照抄公开测试的输入断言。案例由AI提出，学生本人理解需本人复核。

附加实验只经Config接口改变包头0/32/64 bit，不改教师源码。每场景同一Arrival复用给两个模式及全部包头配置，输出results/extra/。实际24行指标、24组轨迹和一张图；header32完全复现基线，各配置电路raw一致，5个基线文件SHA256保持原样。连续满载包头变大时有效利用率下降，但轻载交付量不变，解释不能概括为所有指标都线性变化。

## 实际命令与证据

全部阶段的具体命令、修改文件、时长和输出链接见[执行记录](docs/execution_log.md)。原始输出在`results/logs/`，真实基线在`results/comparison.*`，附加数据在`results/extra/header_sweep.*`；没有复制教师examples结果作为本人仿真。

核心已运行命令（均使用项目`.venv/Scripts/python.exe`）：环境检查；框架4测试；电路4测试；分组4测试；指标3测试；performance_test；集成3测试；重复仿真和verify_baseline；student_tests 1测试；header_experiment。报告与本记录新建于以上证据产生后；评分与提交前检查结果在实际执行后追加。

## 核心逻辑与验证决策

发送循环只在预算和队列都非空时继续：取队首，发送min(预算,remaining_wire_bits)，同步扣减两个量。队首归零才popleft并加入完成列表；有剩余预算可继续下一条。循环没有额外加头，也没有切换到不属于当前时隙的电路用户。summarize只统计框架已经确认完成的payload，并保留窗口末未完成记录的完整payload。

选择组合缓存反例的理由是：只看最终守恒不一定发现错误准入；同时断言每tick发送和缓存轨迹，可区分提前释放、顺序颠倒及错误排空。选择重复输出哈希的理由是验证固定输入下真实可复现，而不是只检查文件存在。

## 本人审阅状态

首次预检时用户已提供个人信息并授权本地按阶段自动执行，尚未确认审阅，因此当时停在未暂存、未提交状态。随后用户于2026-10-19明确回复“审阅完毕直接提交吧”，授权当前成果的本地提交、推送个人Fork与创建教师仓库PR。本记录据此更新审阅状态，不代写个人独立推导或课堂反思。

## 本地评分与报告核验的真实追加

实际执行教师calculate_grade.py，自动分70/70，manual_pending=30、status=ok。首次评分没有为该进程设置MPLCONFIGDIR，触发默认用户缓存写入拒绝与临时目录警告；设置项目`.build/matplotlib`重跑后正常，临时目录自动清理。两次原始输出均保留，没有把警告写成核心测试失败。

报告手算用实际simulate再次核对，两个模型利用率和完成时延匹配。AI自写的第一次占位符检查过宽，把报告中说明实现过程的“TODO”一词也当未完成项，出现AssertionError；通过rg定位后改为核查真实模板字段残留，重跑通过。该修正只针对AI新增的检查，不涉及教师测试。详细命令与原始输出见执行记录及results/logs/07_report_validation_initial.txt和07_report_validation.txt。

阶段08运行完整`-m pytest grading student_tests -q`，真实24 passed in 0.37s；新增preflight脚本实际执行通过，确认13个受保护文件哈希、三个原函数接口、默认基线、报告数值与链接保持正确，暂存区为空，HEAD未变。提交清单已生成。依用户要求到此停止，未执行git add、commit、push或创建PR；本人理解与提交认可继续保持待审阅状态。

以上为首次预检的历史记录；后续“审阅完毕直接提交吧”授权已取代等待提交确认的状态。提交前再次运行预检通过，GitHub只读查询确认没有本人重复PR。Git默认Windows TLS后端ls-remote出现SEC_E_NO_CREDENTIALS，改用仅单次命令的`-c http.sslBackend=openssl`后正常读到远端main=bc9099e；未关闭证书校验或更改全局Git设置。后续提交与PR实际状态见Git历史、PR正文及本地results/logs/09_submission_result.json。

审阅后完整测试再次24 passed。暂存检查发现原PRD和REPORT的Markdown双空格硬换行，被Git默认空白检查提示；保留原始PRD，增加项目.gitattributes的Markdown空白规则及结果/PRD原始字节规则。该规则用于保留合法Markdown换行及真实产物哈希，没有更改任何教师测试或评分。

## 提交格式更正

用户随后明确：GitHub提交使用原来的REPORT.md；Word报告仅供本人之后通过邮件交给教师。AI此前误将Word及其制作脚本推送为68ea81f，现通过新增更正提交从最新分支及相对教师基线的PR改动中移除Word、制作脚本和Word验证摘要；本地文件与验证记录保留，使用本地.git/info/exclude避免再次误加。没有删除本地Word，也没有发送邮件；已推送历史未强制改写。

用户表示已允许GitHub访问后，AI重新尝试打开PR页面，浏览器仍返回已保存权限设置或管理策略阻止https://github.com。未绕过浏览器权限；连接器此前的403和此站点权限问题均未被记为PR创建成功。
