# 企业知识问答 Agent（题号 3）

当前已完成第一至第九批：四个REST路由及前置能力、真实模型六类两次验证、规则/记忆回归和授权的独立代理资料变更核查。最终36轮实际结果与全部104轮失败/复跑记录见[第八批证据](examples/batch-8/verification.md)、[独立逐项矩阵](examples/batch-8/delegated-audit/validated-review.md)。资料修改及支持性审阅按用户明确授权由独立AI代理代办，不冒称用户亲自完成。第九批在干净副本的独立环境完成无密钥/空缓存Mock、真实权重独立下载及真实HTTP问答，见[冷启动证据](examples/batch-9/verification.md)。**第10批综合交付尚未完成**。当前43/46项，下一项10.1。OpenSpec规划与任务文件仅保留本地，不随公开仓库发布。

## 支持环境与安装

本批实测支持 Windows 11 x86-64、CPython **3.12.13**、PowerShell、uv **0.11.28**；Git 用于忽略规则测试。其他平台尚未验证。系统 PATH 中的 Anaconda Python 3.7 不用于本项目。

在项目根目录执行以下命令，不需要激活环境。若本机没有 uv，先按 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/) 准备；下列命令由 uv 获取或选择独立 Python。Python 与依赖安装可联网，工程测试和配置检查不需要网络。

```powershell
Get-Command uv, git
$env:UV_CACHE_DIR = Join-Path $PWD '.cache/uv'
uv python install 3.12.13
uv venv --python 3.12.13 --managed-python .venv
uv sync --locked --extra test --no-editable --python .venv/Scripts/python.exe
uv pip check --python .venv/Scripts/python.exe
uv pip list --python .venv/Scripts/python.exe
```

依赖唯一声明入口为 [pyproject.toml](pyproject.toml)，[uv.lock](uv.lock)锁定传递依赖及下载来源。基础运行依赖为python-dotenv==1.1.1、FastAPI==0.115.14、Pydantic==2.11.7、Uvicorn==0.34.3；test组httpx==0.28.1供API测试，测试执行器为标准库unittest。可选embedding组固定torch==2.9.0+cpu、transformers==4.57.1、safetensors==0.6.2、huggingface-hub==0.36.0，torch只取官方CPU索引。构建使用setuptools==80.9.0。安装不继承全局包，不需要模型SDK或CUDA。

修改源码后，在对应的sync命令中追加`--reinstall-package enterprise-knowledge-qa`再测试，避免复用旧构建缓存。`--no-editable`使测试从已安装包导入，不通过PYTHONPATH引用源码。基础Mock安装不含embedding依赖；若需要保留真实编码器，请始终使用下方带`--extra embedding`的命令。

## 配置入口：Mock 与真实模式

[.env.example](.env.example) 可直接用于无密钥的 Mock **配置检查**：

```powershell
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa --env-file .env.example
```

这条命令只检查配置，输出 `service=not_started`，不会启动 HTTP 服务、调用模型、读取权重或创建 SQLite/Trace。若进程已设置同名变量，它们会覆盖文件；排查模式不符时先检查当前进程的 `QA_MODE`。

个人配置可复制模板再用本地编辑器填写，真实密钥只存本地：

```powershell
Copy-Item .env.example .env
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa --env-file .env
```

复制命令仅在 `.env` 不存在时执行，避免覆盖个人配置。真实模式将本地 `.env` 的 `QA_MODE` 改成 `live`，填写密钥、权重目录与revision，再运行同一检查命令。缺少前置条件会以退出码2报错，不切成Mock。配置检查只验证密钥非空、目录存在与revision非空；实际编码器加载会另行核对固定revision和6个文件的SHA-256，且只从本地加载。

| 变量 | 默认/模板 | 用途 |
| --- | --- | --- |
| QA_MODE | 模板 mock，无隐式默认 | 显式 live 或 mock |
| DEEPSEEK_API_KEY | 空占位 | live 必填，不输出密钥 |
| DEEPSEEK_BASE_URL | https://api.deepseek.com | 固定官方服务入口 |
| DEEPSEEK_MODEL | deepseek-flash | 官方适配已实现，显式非思考、无隐式重试 |
| EMBEDDING_MODEL_ID | BAAI/bge-small-zh-v1.5 | 已确认本地 CPU 模型 |
| EMBEDDING_MODEL_PATH | models/bge-small-zh-v1.5 | 本地权重目录，Mock 不检查或读取 |
| EMBEDDING_REVISION | 7999e1d3359715c523056ef9478215996d62a620 | 固定公开revision，与本地manifest及文件指纹匹配 |
| QA_DATA_PATH | data/knowledge.json | 已实现的合成资料路径，见 data/REVIEW.md |
| QA_SQLITE_PATH | runtime/sessions.sqlite3 | 会话库路径，API保存完整问答与结果/Trace，重启复用 |
| QA_TRACE_PATH | runtime/traces | 独立调用执行器run时通过trace_directory显式保存的目录；API的完整Trace在SQLite请求结果中 |
| QA_MAX_MODEL_CALLS / QA_MAX_TOOL_CALLS | 8 / 6 | 固定上限，拒绝改值；第6工具立即停止，第8模型请求在当前规则下不可达 |
| QA_MODEL_TIMEOUT_SECONDS / QA_TASK_TIMEOUT_SECONDS | 60 / 300 | 可配置正有限秒数；单请求与总deadline已实现 |
| QA_HISTORY_TOKEN_BUDGET | 8000 | 可配置正整数，完整轮次估算历史预算；不截断当前问题 |

只读取显式指定的 env 文件，不搜索父目录；支持 dotenv 引号和注释，关闭变量插值。环境变量优先于文件。相对路径以 env 文件所在目录为基准；直接调用 `load_settings()` 不指定文件时以当前目录为基准。必须显式选择模式。检查不输出整个配置对象或环境变量。

[.gitignore](.gitignore) 排除整个 `openspec/`、本地 `.agents/` 工具配置、`.env`、本地权重、环境、缓存、运行数据库和 runtime 原始日志。精选证据放 `examples/`，提交前检查并移除密钥及隐私信息；忽略规则不能阻止强制添加。分批提交发布只记录已实现与验证的阶段成果，不代表第10组最终验收完成。

## 服务启动与四个REST请求

在项目根目录、新PowerShell窗口运行Mock服务（无密钥、无权重）：

```powershell
$env:QA_MODE = 'mock'
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa.server --env-file .env.example
```

服务固定监听`127.0.0.1`，默认端口8000，可用`--port 8001`改变端口；单进程运行。退出用Ctrl+C，再运行相同命令和SQLite路径可续接会话。没有界面、独立业务CLI、登录或多进程协调。Mock是受控演示策略：支持“星帆剪辑支持什么导出格式？”、“那最高支持多大分辨率？”和“报销材料是什么？”，事实从实际检索、读取的原文展示，不硬编码数值。新会话只问分辨率会先确认产品对象；不支持的输入明确incomplete，不当成真实语义判断。

另开PowerShell窗口发送请求；中文Body显式转UTF-8字节：

```powershell
$base = 'http://127.0.0.1:8000'
Invoke-RestMethod "$base/health"
$session = Invoke-RestMethod -Method Post -Uri "$base/sessions" -ContentType 'application/json' -Body '{}'
$id = $session.session_id
$body = @{ question = '星帆剪辑支持什么导出格式？' } | ConvertTo-Json -Compress
$first = Invoke-RestMethod -Method Post -Uri "$base/sessions/$id/messages" -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
$first | ConvertTo-Json -Depth 100
$body = @{ question = '那最高支持多大分辨率？' } | ConvertTo-Json -Compress
$second = Invoke-RestMethod -Method Post -Uri "$base/sessions/$id/messages" -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
$second | ConvertTo-Json -Depth 100
Invoke-RestMethod "$base/sessions/$id" | ConvertTo-Json -Depth 100
```

`POST /sessions`接受无Body、null或空对象，返回201与session_id/mode；`POST /sessions/{id}/messages`只接收非空字符串question，不接收客户端历史、模式、锚点或故障开关；不设独立字符上限。正常任务返回200与业务状态、引用、缺口、单个追问、锚点校验、持久化结果、模式、计数和Trace。`GET /sessions/{id}`返回完整业务消息及requests中的完整已存结果/Trace，未完成登记无结果时为null。`GET /health`返回应用初始化状态、模式和资料指纹，不创建或调用生成模型；真实启动会预先加载本地编码器，健康检查本身不触发付费调用，不作外部模型连通性证明。

| 情况 | HTTP与响应 |
| --- | --- |
| 非法JSON、空白/非字符串question、额外字段 | 422，`error.code=invalid_request`，不回显输入内容 |
| 不存在的会话 | 404，`error.code=unknown_session` |
| 会话创建/读取存储失败 | 503，`error.code=storage_failed` |
| 本轮保存失败 | 503，error加`result`中的incomplete、已有证据、Trace及`persistence.saved=false` |
| 模型/工具/超时/上限中断 | 200任务结果，业务status=incomplete，原因在execution_issues/stop_reason；不自动Mock |

以下为预期错误请求；PowerShell会抛HTTP异常，可在异常中检查422和404，不是成功示例：

```powershell
Invoke-RestMethod -Method Post -Uri "$base/sessions/$id/messages" -ContentType 'application/json' -Body '{"question":""}'
Invoke-RestMethod "$base/sessions/not-found"
```

真实模式先按下文安装embedding依赖、准备权重，并在本地`.env`配置QA_MODE=live、密钥和权重/revision；再运行：

```powershell
$env:QA_MODE = 'live'
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa.server --env-file .env
```

真实模式与Mock使用同样四个请求格式，只有显式配置选择模式。配置、权重或存储未就绪会以退出码2停止启动；认证/服务失败返回任务incomplete，不换服务。第八批已通过同一ConversationService/Agent运行真实六类问答；第九批另在干净副本中完成了使用真实BGE与DeepSeek的HTTP问答，见[冷启动证据](examples/batch-9/verification.md)。

## 分层测试与实际证据

安装test组后执行离线工程与API测试：

```powershell
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
```

测试覆盖配置、资料、Agent预算、引用、检索流程、SQLite/历史/锚点和四个API的工程契约，不证明真实语义能力。HTTP集成测试使用TestClient，仍需操作系统允许Windows事件循环的本地socket。实际服务启动、两轮请求、隔离和重启的可复跑验证脚本如下；只允许loopback通信，阻断外部socket及BGE构造，数据库/空权重目录在临时目录中，运行后清理：

```powershell
.venv/Scripts/python.exe -I examples/batch-7/exercise_http.py --output .cache/http-demo-new.json
```

输出文件必须尚不存在；复跑时换新文件名，保留先前证据。可加`--powershell-output .cache/readme-new.json`实际执行README的PowerShell请求。实际请求/响应/Trace见[最终HTTP记录](examples/batch-7/http-demo-final.json)、[PowerShell结果](examples/batch-7/readme-requests.json)、[第七批验证](examples/batch-7/verification.md)。第九批另用独立空环境实际复跑了这些API与重启步骤，见[冷启动证据](examples/batch-9/verification.md)。真实embedding、六类真实模型效果与冷启动分别独立验收。资料加载/重载接口见[资料说明](data/README.md)，已审阅正文与变体预期见[审阅稿](data/REVIEW.md)。

第八批真实验证入口（产生实际模型费用，必须显式--live；本地.env提供密钥，权重使用已锁定revision，不改.env）：

```powershell
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group core --repeat 2 --output .cache/live-core-new
```

output目录必须尚不存在。regressions、memory组及独立代理资料组命令见[完整验证](examples/batch-8/verification.md)；原始失败与修复后结果全部保留。真实适配器显式temperature=0，不保证确定性；两次核心重复不代表统计稳定性。本批所有尝试按usage保守估算3.333384元、未知usage0，实际账单未核实；不推断剩余预算或把AI工作算作个人工时。

## 真实CPU权重、检索与重载

安装真实编码依赖（只需准备一次；若源码改动，追加上述reinstall参数）：

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.cache/uv'
$env:UV_LINK_MODE = 'copy'
uv sync --locked --extra embedding --extra test --no-editable --python .venv/Scripts/python.exe
```

显式准备固定revision权重：

```powershell
$env:HF_HUB_DISABLE_XET = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa.prepare_weights --output models/bge-small-zh-v1.5
```

只下载6个必要文件（包含safetensors，不下载pickle权重），并写入本地weights-manifest.json。权重与下载缓存位于被忽略的models目录；正常加载不下载、不使用隐式全局缓存，也不以假向量替代。模型来源与revision可核对 [BAAI官方模型](https://huggingface.co/BAAI/bge-small-zh-v1.5)。

实际真实编码/召回/重载验证入口，无需DeepSeek密钥、不调用生成模型；运行期间阻断socket.connect：

```powershell
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa.retrieval_check --weights models/bge-small-zh-v1.5 --output examples/batch-4/real-retrieval
```

每次生成独立报告，不覆盖失败。预期见 [7个检索输入](examples/batch-4/retrieval-cases.json)，实际配置、候选、缺失项及限制见 [第四批记录](examples/batch-4/verification.md)。它证明指定资料上的检索覆盖，不是六类最终问答验收。

在应用中通过`make_retrieval(settings)`建立store；任务开始只取一次`index = store.acquire()`，再用`create_agent(settings, model, index)`，保证检索、读取、引用共用该快照。资料修改后显式`new_index = store.reload()`，完整构建BM25和向量后才发布新任务使用的索引；既有任务继续用旧index。失败不发布半新索引。复现的隔离正文替换与单D01/加入D02步骤包含在上述retrieval_check中，不改基础语料。

检索参数：BM25 k1=1.5/b=0.75、正值IDF；NFKC/casefold、汉字单字/双字、拉丁/数字连续词；本地CPU BGE用CLS、单位归一化，查询加官方中文检索前缀；每路12，RRF k=60，输出6/12，按片段ID打破同分。编码最长512 token（查询前缀与特殊token也计入），过长明确报错，无静默截断。片段原文不改写，候选分数不代表规则可信度或日期优先级。

## 评审导航与目录

### 全新环境复现（第九批）

建议从一次干净检出开始，勿复制开发者的`.venv`、`.env`、`models`或运行数据库。按上方安装步骤新建环境，先仅安装test组，再执行：

```powershell
.venv/Scripts/python.exe -I examples/batch-9/verify_environment.py --output .cache/cold-offline-new
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa --env-file .env.example
.venv/Scripts/python.exe -I examples/batch-7/exercise_http.py --output .cache/cold-http-new.json --powershell-output .cache/cold-requests-new.json
```

第一条会验证未继承全局包、导入的安装包与当前源码一致、没有本地`.env`或`models`，然后在空模型缓存、空密钥、外部socket阻断下运行全部离线测试。它必须在准备真实权重之前执行；复跑需另一干净副本及新输出目录。HTTP脚本的服务子进程同样禁止外部连接，只允许本机请求。三个步骤分别验证测试、配置和实际服务，配置有效不等于服务已启动。

随后在该环境按上方真实CPU依赖与权重步骤显式下载到`models/bge-small-zh-v1.5`，并运行`retrieval_check`。最后可运行一次会产生模型费用的最小真实HTTP验证：

```powershell
.venv/Scripts/python.exe -I examples/batch-9/exercise_live_http.py --live --env-file C:/private/qa.env --weights models/bge-small-zh-v1.5 --output .cache/cold-live-new.json
```

将`C:/private/qa.env`替换为实际本地配置文件，填写`DEEPSEEK_API_KEY`；脚本只从该文件取密钥，通过内存环境交给子进程，不复制或输出密钥。服务使用干净副本的`.env.example`与资料、新建临时SQLite、指定权重和离线HF缓存配置；实际访问官方DeepSeek，执行四个路由并保存问答/Trace。它只证明一次冷启动真实问答，第八批六类重复验证另见对应证据。安装包下载缓存可以显式复用；模型权重须独立准备，不能拿开发机隐式权重缓存代替。实际命令、全部版本、原失败与复跑见[第九批记录](examples/batch-9/verification.md)。

第三批可执行的少量真实协议检查（需要本地 `.env` 中的有效密钥，会产生少量费用）：

```powershell
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa.smoke --live --env-file .env --output examples/batch-3/live-smoke
```

`--live` 明确只为这次检查选择真实模式，即使本地文件为mock也不改写它。此检查仅验证生成模型选择读取、接收实际原文后结束，不需要尚未准备的embedding权重；它不会启动HTTP服务、接入假混检或替代六类验收。每次运行按独立请求ID保存Trace和summary，失败不覆盖。使用与Mock相同的Agent执行器；`make_model`在普通应用中严格按配置选择模式，不自动降级。

调用完整Agent时可注入受控Mock策略与同快照search接口；API已接入实际混合检索、引用和记忆来源校验。来源合法性不等于业务/锚点语义正确。计数可达性修订已由用户确认，见[决定原话](examples/batch-3/budget-decision.md)；实际失败/复跑、费用与验证边界见[第三批记录](examples/batch-3/verification.md)。

- [需求与 A01–A06 验收预期](docs/01-requirements.md)、[方案设计](docs/02-solution.md)、[评估计划及后续证据](docs/03-evaluation.md)。这些文档的开发前状态不代表全部业务已经实现。
- [AI 使用及个人贡献记录](docs/04-ai-usage.md)、[工时、预算及阶段复盘](docs/05-retrospective.md)、[业务术语](CONTEXT.md)。
- 公开需求、设计与证据以 `docs/` 和 `examples/` 为入口；本地 OpenSpec 提案、实施设计和任务清单不发布。历史验证清单中提及的 OpenSpec 指纹仅用于本地留档。
- [src/](src/enterprise_knowledge_qa/)：包、配置、资料与读取；[tests/](tests/)：离线工程与资料测试；[data/](data/)：已审阅语料；[examples/](examples/)：实际证据，不预填业务结果。

总计划 18 小时，其中预留 6 小时用于验证、失败修复和交付文档；真实调用预算人民币 30 元。实际工时、个人操作与费用按发生记录，未知值保留未知。
