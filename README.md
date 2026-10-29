# 企业知识问答 Agent（题号 3）

当前已实现 `enterprise-knowledge-qa` 第一批工程基础及第二批资料校验、快照、原文读取，资料已获用户实际审阅接受。**业务问答服务尚未实现**，工程测试通过不代表 Mock 问答、真实模型或业务验收通过。当前完成 1.1–1.4、2.1–2.4，共 8/46 项；下一项为 3.1。OpenSpec 规划与任务文件仅保留本地，不随公开仓库发布。

## 支持环境与安装

本批实测支持 Windows 11 x86-64、CPython **3.12.13**、PowerShell、uv **0.11.28**；Git 用于忽略规则测试。其他平台尚未验证。系统 PATH 中的 Anaconda Python 3.7 不用于本项目。

在项目根目录执行以下命令，不需要激活环境。若本机没有 uv，先按 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/) 准备；下列命令由 uv 获取或选择独立 Python。Python 与依赖安装可联网，工程测试和配置检查不需要网络。

```powershell
Get-Command uv, git
$env:UV_CACHE_DIR = Join-Path $PWD '.cache/uv'
uv python install 3.12.13
uv venv --python 3.12.13 --managed-python .venv
uv pip install --python .venv/Scripts/python.exe .
uv pip check --python .venv/Scripts/python.exe
uv pip list --python .venv/Scripts/python.exe
```

依赖唯一入口为 [pyproject.toml](pyproject.toml)：构建依赖 `setuptools==80.9.0`，运行依赖 `python-dotenv==1.1.1`，测试使用 Python 标准库 unittest。项目版本为 0.1.0；没有全局包继承或额外隐含 requirements 文件。每次修改源码后重新执行安装命令再测试，测试导入已安装的包，不通过 PYTHONPATH 指向源码。后续 FastAPI、模型 SDK 和 embedding 等依赖将在对应任务中固定版本并验证，目前未安装。

## 配置入口：Mock 与真实模式

[.env.example](.env.example) 可直接用于无密钥的 Mock **配置检查**：

```powershell
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa --env-file .env.example
```

这条命令只检查配置，输出 `service=not_implemented`，不会启动 HTTP 服务、调用模型、读取权重或创建 SQLite/Trace。若进程已设置同名变量，它们会覆盖文件；排查模式不符时先检查当前进程的 `QA_MODE`。

个人配置可复制模板再用本地编辑器填写，真实密钥只存本地：

```powershell
Copy-Item .env.example .env
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa --env-file .env
```

复制命令仅在 `.env` 不存在时执行，避免覆盖个人配置。真实模式将本地 `.env` 的 `QA_MODE` 改成 `live`，填写密钥、权重目录与 revision，再运行同一检查命令。缺少这些前置条件会以非零退出码 2 明确报错，不自动切成 Mock。检查仅验证密钥非空、目录存在与 revision 非空，不证明密钥有效、目录内权重完整或模型可用。真实权重的下载、版本固定及编码加载步骤待任务 4.1 实现，当前没有权重准备命令。

| 变量 | 默认/模板 | 用途 |
| --- | --- | --- |
| QA_MODE | 模板 mock，无隐式默认 | 显式 live 或 mock |
| DEEPSEEK_API_KEY | 空占位 | live 必填，不输出密钥 |
| DEEPSEEK_BASE_URL | https://api.deepseek.com | 固定官方服务入口 |
| DEEPSEEK_MODEL | deepseek-flash | 已确认模型；非思考与关闭重试的适配待 3.1 |
| EMBEDDING_MODEL_ID | BAAI/bge-small-zh-v1.5 | 已确认本地 CPU 模型 |
| EMBEDDING_MODEL_PATH | models/bge-small-zh-v1.5 | 本地权重目录，Mock 不检查或读取 |
| EMBEDDING_REVISION | 空占位 | live 必填；实际 revision 与权重准备待 4.1 |
| QA_DATA_PATH | data/knowledge.json | 已实现的合成资料路径，见 data/REVIEW.md |
| QA_SQLITE_PATH | runtime/sessions.sqlite3 | 会话库路径；持久化待第 6 组 |
| QA_TRACE_PATH | runtime/traces | 原始运行记录目录；Trace 待 3.7 |
| QA_MAX_MODEL_CALLS / QA_MAX_TOOL_CALLS | 8 / 6 | 固定上限，拒绝改值；执行计数待 3.3 |
| QA_MODEL_TIMEOUT_SECONDS / QA_TASK_TIMEOUT_SECONDS | 60 / 300 | 可配置正有限秒数；deadline 待 3.6 |
| QA_HISTORY_TOKEN_BUDGET | 8000 | 可配置正整数，估算历史预算；历史选择待 6.2 |

只读取显式指定的 env 文件，不搜索父目录；支持 dotenv 引号和注释，关闭变量插值。环境变量优先于文件。相对路径以 env 文件所在目录为基准；直接调用 `load_settings()` 不指定文件时以当前目录为基准。必须显式选择模式。检查不输出整个配置对象或环境变量。

[.gitignore](.gitignore) 排除整个 `openspec/`、本地 `.agents/` 工具配置、`.env`、本地权重、环境、缓存、运行数据库和 runtime 原始日志。精选证据放 `examples/`，提交前检查并移除密钥及隐私信息；忽略规则不能阻止强制添加。当前仓库初始化发布只保存前两批成果，不代表第 10 组最终验收完成。

## 服务启动、请求与分层测试入口

| 入口 | 当前状态与后续任务 |
| --- | --- |
| Mock HTTP 服务启动与请求 | 未完成；模型/编码适配、执行器与 API 分别在第 3、4、7 组实现，无可执行启动或问答请求命令 |
| 真实 HTTP 服务启动与请求 | 未完成；配置检查入口同上，模型连通性与真实端到端分别为 3.8、8.2 |
| POST /sessions | 计划创建会话，未实现；7.1/7.3 提供实际请求格式 |
| POST /sessions/{id}/messages | 计划提交问题并返回结果/Trace，未实现；7.1/7.3 提供实际请求格式 |
| GET /sessions/{id} | 计划查看会话，未实现；7.1/7.3 |
| GET /health | 计划无付费调用健康检查，未实现；7.1/7.3 |
| 真实 embedding 验证 | 未完成；权重准备与召回测试为 4.1/4.5 |
| 六类真实模型验收 | 未完成；8.1–8.6，条件缺失不能标通过 |
| 完整冷启动 Mock/API 与真实验证 | 未完成；9.1–9.3，不能用本批安装检查代替 |

当前实际可执行的离线工程测试：

```powershell
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
```

测试覆盖独立安装导入、配置、脱敏、Git 忽略、资料校验、快照与原文读取，不证明 Agent 决策、混合检索、API 或记忆效果。配置/读取测试阻断 socket 创建，临时文件放仓库内 `.cache/`；Git 忽略测试只创建临时仓库元数据，不初始化项目。实际执行、失败和复跑见 [第一批验证记录](examples/batch-1/verification.md) 与 [第二批验证记录](examples/batch-2/verification.md)。资料加载和重载接口见 [资料说明](data/README.md)，完整原文及单 D01、冲突、人事生效预期见 [审阅稿](data/REVIEW.md)。

## 评审导航与目录

- [需求与 A01–A06 验收预期](docs/01-requirements.md)、[方案设计](docs/02-solution.md)、[评估计划及后续证据](docs/03-evaluation.md)。这些文档的开发前状态不代表全部业务已经实现。
- [AI 使用及个人贡献记录](docs/04-ai-usage.md)、[工时、预算及阶段复盘](docs/05-retrospective.md)、[业务术语](CONTEXT.md)。
- 公开需求、设计与证据以 `docs/` 和 `examples/` 为入口；本地 OpenSpec 提案、实施设计和任务清单不发布。历史验证清单中提及的 OpenSpec 指纹仅用于本地留档。
- [src/](src/enterprise_knowledge_qa/)：包、配置、资料与读取；[tests/](tests/)：离线工程与资料测试；[data/](data/)：已审阅语料；[examples/](examples/)：实际证据，不预填业务结果。

总计划 18 小时，其中预留 6 小时用于验证、失败修复和交付文档；真实调用预算人民币 30 元。实际工时、个人操作与费用按发生记录，未知值保留未知。
