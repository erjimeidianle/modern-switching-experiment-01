# 提交前检查与后续人工节点

本文件保留首次预检清单；2026-10-19用户随后回复“审阅完毕直接提交吧”，授权提交、推送个人Fork及创建教师仓库PR。下列待确认事项的授权节点已满足，实际完成状态以Git历史和PR为准。

## 本地交付清单

必需：`src/part1_circuit.py`、`src/part2_packet.py`、`src/metrics.py`、`REPORT.md`、`AI_LOG.md`、`student_tests/test_my_case.py`；
`results/comparison.json`、`comparison.csv`、`comparison_metrics.png`、`queue_occupancy.png`、`pcm_frame_view.png`；
`results/extra/header_sweep.json`、`header_sweep.csv`、`header_sweep.png`。

配套复现材料：`scripts/verify_baseline.py`、`scripts/header_experiment.py`、`scripts/preflight.py`、`requirements-lock.txt`、`docs/execution_log.md`、本清单及`results/logs/`原始证据。
报告引用的`codex_tasks/实验一_PRD_电路交换与分组交换.md`也应随报告保留，或由本人提交时决定如何提供该引用。
`.vscode/settings.json`只含项目相对解释器路径，可按需要提交。
其他原有`codex_tasks/`文件保持原样，初始即由用户放入，未擅自加入暂存区。

结果目录和评分输出受.gitignore忽略，本地存在不代表已上传；将来获准提交时，须对上述实际产物逐文件使用git add -f，不对整个仓库强制添加。
不要把`.venv/`、`.build/`、缓存、密钥或`course_management/`同学名单纳入本次变更。
评分根文件`grade_report.json`、`grade_result.txt`保留在本地，另有结果日志供复核。

## 本次已核查内容

运行`python scripts/preflight.py`（使用项目.venv解释器）会只读检查main、origin、起始HEAD、空暂存区、受保护文件SHA256、原函数接口、其他教师src未变、默认基线哈希、报告数值/图片链接、模板字段与常见凭据模式，输出`results/logs/08_preflight.json`。
完整测试使用`python -m pytest grading student_tests -q`；这还包含教师作业跟踪功能测试，不更改其规则。
测试和评分日志中的时间、版本及结果以原始文件为准。自动70分不等于最终成绩。

## 等待本人完成的事项

1. 阅读REPORT中的两用户手算、在传缓存反例、四场景结论和局限，确认理解与认可；AI没有替本人声明完成理解。
2. 核对姓名郑航宇、学号2024280087和账号erjimeidianle，审阅变更与结果，明确授权后再暂存和创建本地commit。
3. 推送需另获明确授权。origin为个人Fork，目标教师仓库为jwentong/modern-switching-experiment-01，base/head分支均main，禁止强制推送。
4. PR标题预期为“现代交换实验01-郑航宇-2024280087”。正文只列真实完成情况与验证结果。当前尚无PR网址或本次新提交SHA。
5. 以后创建PR时检查最新head SHA对应的Checks、Summary、grading-report；等待Approve workflows由教师处理，不能记为0分。自动70分、人工30分及最终成绩须区分。补交更新同一个PR。

首次预检曾在此节点停止。本人随后已表示审阅完毕并授权直接提交，继续执行本清单所列提交流程。项目级依赖、缓存及同学名单不纳入本次新增提交文件。
