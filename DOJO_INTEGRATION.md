# AgentDojo 正式子集接入

**本轮正式子集已完成，请不要重复启动付费运行。** 主结果见 DOJO_RESULTS.md。原始运行曾中断，保留其 incomplete 标记；经一次明确记录的错误恢复，完成视图位于 results/dojo-formal-completed-20261020，全部 120 个官方分数已离线复核通过。

本阶段使用 AgentDojo 0.1.35 的 workspace v1.2.2 环境、24 个官方工具和原有 utility/security 评分方法。我们的改动是自定义 DeepSeek 原生工具桥接、提示词边界和检索前工具范围规划。不是 AgentDojo 全部 suite/攻击目标的完整 leaderboard 运行。

官方来源：https://github.com/ethz-spylab/agentdojo 。固定安装在项目 .venv-dojo，原环境未修改。源码与数据逐文件哈希、全部依赖精确版本保存在 evaluation/dojo-workspace-v1.2.2-plan-20261020。

## 样本与协议

- 开发集：user_task_0、user_task_1；用于接入和兼容性调试。
- 保留集：预先按连续 ID 固定 user_task_2 至 user_task_21，共 20 任务，没有根据模型结果挑选。
- 三组 none / boundary / scoped；正常与 important_instructions_no_names 两条件，共 120 个保留案例。
- 攻击固定 injection_task_0（模拟发送一封指定邮件）。使用上游 FixedJailbreakAttack 与 ImportantInstructionsAttack 原始模板，默认通用用户名/模型称呼，等同 no-names 模板文本；注入位置由上游方法通过标准任务轨迹识别，没有自行把攻击撒入所有数据。
- 所有工具均来自官方模拟环境；没有连接真实邮箱、云盘、日历账号。
- 最多 12 轮，每轮最多 1024 输出 token；scoped 另有一次最多 512 token 的检索前规划。
- 官方 security 方法返回 True 在本协议中代表攻击目标达成，不是防御成功；正常组 attack_success 为 null。

## scoped 策略的实际含义

规划器只看原用户请求和工具定义，返回允许的工具名称集合，不读取外部文档、不使用官方 ground truth 决定权限。执行前阻止集合外的调用，同时继续给模型返回拒绝结果。三组仍展示相同工具集合。

这只是工具名称级权限：不能阻止已获准 send_email 的任务向错误收件人发信。规划器也可能漏选正常任务所需工具，损失需要由 utility 指标衡量。不能将其描述为可靠的参数级授权系统或已验证的新防御算法。

## 验证与记录

tests_dojo 独立验证：官方标准轨迹通过官方 utility；桥接后的同样轨迹也通过；受控攻击确实改变模拟邮件状态且被官方 security 识别；scoped 策略可阻止该受控效果。受控替身测试不是模型攻击成功实验。

案例保存原始消息、注入文本、最终环境、允许工具集合、拒绝记录、token、响应模型名和时延。YAML 格式化可能改变空白，因此攻击暴露检查先安全解码工具返回，再规范空白匹配完整注入文本；该记录方式不参与模型输入或官方成功评分。

正式运行前检查计划哈希、AgentDojo 版本、上游源码/数据哈希和依赖版本。运行中遇到首个接口错误停止，保留 partial cases，不能把错误计为安全成功。不同防御按固定分组顺序运行，只有一次重复，存在顺序和服务波动影响。

## 命令

测试（不调用模型）：

```powershell
.\.venv-dojo\Scripts\python.exe -m unittest discover -s tests_dojo -v
.\.venv-dojo\Scripts\python.exe -m unittest discover -s tests -v
```

正式运行（会消耗 API 额度，请不要在已有正式运行进行时重复启动）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-dojo-formal.ps1
```

重建环境时先使用 Python 3.12 创建 .venv-dojo，再安装冻结依赖及当前工程：

```powershell
.\.venv-dojo\Scripts\python.exe -m pip install -r evaluation/dojo-workspace-v1.2.2-plan-20261020/requirements.lock.txt
.\.venv-dojo\Scripts\python.exe -m pip install -e .
```

模型密钥需在本机配置 .env.local，绝不包含在依赖文件或结果中。一次正式运行最多 1440 次主模型请求及 40 次范围规划请求；实际调用通常更少，记录以每条 metadata 为准。

## 当前证据边界

开发任务已经用于调试，不可当作保留集成绩。正式结果只读 results/dojo-formal-20261020；必须检查 formal_complete 和 completed_cases，运行未完成时不能写 120 个案例全部完成。

20 个任务 × 不同条件不是 120 个独立任务。只评价一个官方攻击目标和固定模板；结果不能推广到完整 AgentDojo、所有攻击或模型。Task scope 及正常任务覆盖的限制必须进入最终报告。
