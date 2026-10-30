# 企业知识问答 Agent（题号3）

面向员工的制度与产品问答服务。模型通过检索、读取和观察循环决定补查、澄清或结束，答案附本轮原文引用；面对冲突和工具失败时明确说明未解决原因。

项目采用Python原生单Agent、DeepSeek、CPU BGE与BM25/RRF、FastAPI和SQLite。提供真实与显式Mock两种模式。核心六类真实场景各运行两次，最终40轮真实回归及124项工程测试已有记录；适用范围和局限见[效果验证](docs/03-evaluation.md)。

| 评审入口 | 内容 |
| --- | --- |
| [需求](docs/01-requirements.md) | 用户、范围、六类成功标准 |
| [方案](docs/02-solution.md) | 模型循环、检索、引用和记忆取舍 |
| [评估](docs/03-evaluation.md) | 预期、实际结果、失败及限制 |
| [AI使用](docs/04-ai-usage.md) | AI辅助范围和个人贡献 |
| [复盘](docs/05-retrospective.md) | 难点、学习和改进方向 |
| [原始证据导航](examples/README.md) | 输入、输出、Trace及环境记录 |

仓库：[ShiriZhang/xiaoying-ai-agent](https://github.com/ShiriZhang/xiaoying-ai-agent)。检出版本用`git rev-parse HEAD`核对。

## 支持环境与安装

已实测 Windows 11 x86-64、CPython **3.12.13**、PowerShell、uv **0.11.28**；Git 用于忽略规则测试。其他平台尚未验证。

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

[.gitignore](.gitignore) 排除本地 `.agents/` 工具配置、`.env`、本地权重、环境、缓存、运行数据库和 runtime 原始日志。精选证据放 `examples/`，提交前检查并移除密钥及隐私信息；忽略规则不能阻止强制添加。个人学习收获及实际参与见[复盘](docs/05-retrospective.md)与[AI辅助使用记录](docs/04-ai-usage.md)。

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

真实模式与Mock使用同样四个请求格式，只有显式配置选择模式。配置、权重或存储未就绪会以退出码2停止启动；认证/服务失败返回任务incomplete，不换服务。真实六类验证与独立环境复现分别记录，见[效果验证](docs/03-evaluation.md)。

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

每次生成独立报告，不覆盖失败。预期见 [7个检索输入](examples/batch-4/retrieval-cases.json)，实际配置、候选、缺失项及限制见 [检索验证记录](examples/batch-4/verification.md)。它证明指定资料上的检索覆盖，不是六类最终问答验收。

在应用中通过`make_retrieval(settings)`建立store；任务开始只取一次`index = store.acquire()`，再用`create_agent(settings, model, index)`，保证检索、读取、引用共用该快照。资料修改后显式`new_index = store.reload()`，完整构建BM25和向量后才发布新任务使用的索引；既有任务继续用旧index。失败不发布半新索引。复现的隔离正文替换与单D01/加入D02步骤包含在上述retrieval_check中，不改基础语料。

检索参数：BM25 k1=1.5/b=0.75、正值IDF；NFKC/casefold、汉字单字/双字、拉丁/数字连续词；本地CPU BGE用CLS、单位归一化，查询加官方中文检索前缀；每路12，RRF k=60，输出6/12，按片段ID打破同分。编码最长512 token（查询前缀与特殊token也计入），过长明确报错，无静默截断。片段原文不改写，候选分数不代表规则可信度或日期优先级。

## 测试与实际证据

```powershell
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
.venv/Scripts/python.exe -I examples/batch-7/exercise_http.py --output .cache/http-new.json --powershell-output .cache/requests-new.json
.venv/Scripts/python.exe -I examples/batch-11/audit_evidence.py --output .cache/evidence-new.json
```

输出使用新路径，不覆盖已有证据。离线测试与Mock服务只证明流程；真实BGE检索与真实生成模型另行验证。六类场景、资料差分、失败和已知限制见[评估](docs/03-evaluation.md)，逐轮原始文件见[证据导航](examples/README.md)。

真实模型回归会产生费用，需本地有效配置、已准备的CPU权重和显式`--live`：

```powershell
.venv/Scripts/python.exe -I examples/batch-8/run_live.py --live --env-file .env --group core --repeat 2 --output .cache/live-core-new
.venv/Scripts/python.exe -I examples/batch-11/run_anchor_reload.py --live --env-file .env --weights models/bge-small-zh-v1.5 --revision 7999e1d3359715c523056ef9478215996d62a620 --output .cache/anchor-new
```

干净环境复现按[独立环境验证](examples/batch-9/verification.md)操作。只实测Windows/CPython3.12；运行时为本机单进程，没有登录权限和线上部署。真实模型小样本不证明统计稳定性，Mock不证明真实语义。未知usage和账单核对情况在证据中分别说明。

## 目录

| 路径 | 内容 |
| --- | --- |
| src/ | 执行器、模型/工具适配、HTTP和持久化 |
| tests/ | 可执行工程与API测试 |
| data/ | 合成制度和产品条文 |
| docs/ | 五份交付文档与能力规格 |
| examples/ | 测试输出、真实运行与失败记录 |
| pyproject.toml / uv.lock | 依赖声明及锁定来源 |
| .env.example | 无真实密钥的配置模板 |
