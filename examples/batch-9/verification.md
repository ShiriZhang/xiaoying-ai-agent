# 第九批：全新环境实际验证

用户授权范围为9.1–9.3，实现后审查、提交及推送；第10批综合验收仍未完成。本批只新增验证脚本和证据、修正文档，未修改业务源码、依赖、基础语料或验收标准。

## 干净副本与安装

基线为`10e31980b98b816ba19f968590aa454bc494721b`，原工作区无修改。使用`git archive`获得不含开发机环境、密钥、权重、数据库的跟踪文件副本。为验证本批候选，额外复制本批验证脚本；第二副本还复制修正后的README、.env.example和docs/03。未复制src、tests或依赖的修改，因为这些文件没有变化。

实际从仓库根执行（安装阶段允许联网，运行阶段另行限制）：

```powershell
New-Item -ItemType Directory -Force .cache/batch-9-clean,examples/batch-9
git archive --format=zip --output=.cache/batch-9-source.zip HEAD
Expand-Archive .cache/batch-9-source.zip .cache/batch-9-clean
$env:UV_CACHE_DIR = Join-Path $PWD '.cache/uv-batch-9'
uv venv --python 3.12.13 --managed-python .cache/batch-9-clean/.venv
Set-Location .cache/batch-9-clean
$env:UV_CACHE_DIR = Join-Path $PWD '.cache/uv-install'
$env:UV_LINK_MODE = 'copy'
uv sync --locked --extra test --no-editable --python .venv/Scripts/python.exe
uv pip check --python .venv/Scripts/python.exe
uv pip list --python .venv/Scripts/python.exe
```

实测Windows x86-64、CPython3.12.13、uv0.11.28，venv配置`include-system-site-packages=false`。CPython解释器由uv管理，不是Anaconda；全新venv复用解释器安装并不继承其site-packages。测试从`-I`启动的已安装非editable包导入，脚本核对该包与副本src全部模块的归一化SHA-256一致。

第一次未设置UV_CACHE_DIR的探测遇到受限默认缓存目录，停止后按README设置项目内缓存成功。首次依赖安装因受限网络DNS失败，见[原失败](install-mock.txt)；联网授权后原命令成功，见[成功安装](install-mock-retry.txt)。仅安装17个声明包，无torch/transformers等真实编码依赖。包兼容检查通过，精确版本与解释器/平台/路径见[初次环境](offline-initial/environment.json)。环境本身、安装包缓存不提交。

## 9.1：无密钥、空缓存Mock

从干净副本根实际执行：

```powershell
.venv/Scripts/python.exe -I examples/batch-9/verify_environment.py --output ../../examples/batch-9/offline-initial
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa --env-file .env.example
.venv/Scripts/python.exe -I examples/batch-7/exercise_http.py --output ../../examples/batch-9/http-initial.json --powershell-output ../../examples/batch-9/powershell-initial.json
```

[120项测试](offline-initial/tests.txt)全部通过，无跳过；没有.env或models，DEEPSEEK_API_KEY清空，独立HF_HOME运行后仍为空，外部socket connect/connect_ex/解析被阻断，未记录外部尝试。测试中的受控模型传输不等于真实联网。配置检查返回mock、valid、service=not_started，没有把配置检查当服务启动。

[实际HTTP记录](http-initial.json)含13次请求：四个API、两轮产品追问、另一会话隔离、422/404、重启后同SQLite续问。子进程启动真实服务入口，阻断外部socket与BGE构造，仅允许loopback；无权重目录、无真实密钥。[README PowerShell记录](powershell-initial.json)另执行可复制请求及错误检查。以上仅证明Mock工程流程，不证明真实语义能力。

## 9.2：真实层独立准备

在同一个新环境继续执行：

```powershell
uv sync --locked --extra embedding --extra test --no-editable --python .venv/Scripts/python.exe
$env:HF_HOME = Join-Path $PWD '.cache/independent-hf'
$env:HF_HUB_DISABLE_XET = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa.prepare_weights --output models/bge-small-zh-v1.5
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa.retrieval_check --weights models/bge-small-zh-v1.5 --output ../../examples/batch-9/real-retrieval
.venv/Scripts/python.exe -I examples/batch-9/exercise_live_http.py --live --env-file ../../.env --weights models/bge-small-zh-v1.5 --output ../../examples/batch-9/live-http.json
```

安装记录见[embedding组安装](install-embedding.txt)。共39个包，torch2.9.0+cpu、transformers4.57.1、huggingface-hub0.36.0、safetensors0.6.2，其余版本保存在[live环境记录](live-http.json)。`uv pip check`通过。

[下载记录](prepare-weights.txt)实际从官方BAAI/bge-small-zh-v1.5准备revision`7999e1d3359715c523056ef9478215996d62a620`的6个文件。准备前干净副本无models，显式输出目录为`.cache/batch-9-clean/models/bge-small-zh-v1.5`，下载缓存为该副本`models/.download-cache`，另设独立HF_HOME，未复制开发机权重或全局HF缓存。文件SHA-256完整清单在[live报告weights_manifest](live-http.json)。后续真实运行只从显式本地路径加载，HF离线配置禁止下载。

[真实BGE报告](real-retrieval/f47ea46754514197aead19cdf56c331c.json)：7个输入×6/12候选共14项，无缺失；长输入拒绝、编码故障、原文替换重载、单D01/加入D02均通过。执行期间socket.connect阻断；报告耗时66.484秒。tokenizer的602>512提示来自预期长输入拒绝用例，没有静默截断或将长输入送入编码模型。

[真实HTTP结果](live-http.json)实际启动安装包服务，依次GET健康、POST会话、POST问题、GET历史。问题为“星帆剪辑支持什么导出格式？”，回答“星帆剪辑支持将视频导出为 MP4、MOV 格式。[C1]”。C1为本轮读取的D09-P01，正文明确支持MP4/MOV；出处、全文及指纹一致，没有附加未问制度。Trace为search→read→finish，3模型/2工具、无恢复或修正，实际模型deepseek-flash，持久化成功。四路由通过不代表健康检查会检查外部服务，真实生成调用只发生在问答路由。

密钥仅由脚本从原工作区本地.env读取并经子进程环境传递，干净副本不生成.env、不复制真实密钥；其余模型/权重/资料配置使用干净副本模板与显式路径，新建空SQLite，不发送私人历史。语料为synthetic=true的公开虚构资料。真实请求首次被自动审核误判为企业私有资料外发而拒绝；只读核查公开合成语料、固定官方目的地与本轮9.2授权后，补充这些事实重新审核获准，未绕过拒绝执行。

3次顶层模型usage均已知，沿用Trace记录的保守估算分别0.005440、0.009310、0.012110元，合计**0.026860元**；实际账单未核实，不推断余额，不将历史第八批费用重复相加。此处仅一个最小真实任务，不替代第八批六类两次及回归，也不代表泛化成功率。

## 9.3：修正与再次复现

修正.env.example“HTTP待实现”旧注释，README更新第九批状态和冷启动流程、显式密钥/权重路径，docs/03新增分层实际证据入口。没有更改业务代码、依赖或验收标准。

从同一Git archive另外解压`.cache/batch-9-recheck`，复制上述候选文档和本批脚本，使用新的`.venv`，仅显式复用首环境的uv安装包缓存（不是模型权重缓存），再次按README安装test组。安装日志见[第二环境安装](install-recheck.txt)。随后同样执行verify_environment、配置检查和exercise_http，改用新输出目录offline-recheck/http-recheck/powershell-recheck。第二环境没有.env、models、真实embedding包；与首个真实环境分离。

第二环境的[版本/源码指纹](offline-recheck/environment.json)、[120项测试](offline-recheck/tests.txt)、[13次HTTP](http-recheck.json)、[PowerShell](powershell-recheck.json)记录再次通过，无跳过或外部尝试。最终src与两环境及第八批最终运行指纹一致，见[一致性核对](source-consistency.json)。因此没有代码/依赖变化需要补跑第八批付费验收。

AI完成环境操作、验证脚本、证据整理和文档修正；未冒称用户手工执行。未全程计量人类或代理主动工时，不把运行耗时当个人工时。Windows为实际支持平台，其他系统未验证。OpenSpec任务勾选保留本地，公开证据不发布规划目录。9.1–9.3完成后总计43/46，第10批仍待实施。

## Standards

独立只读代理`review_standards`按code-review技能审查非空暂存候选`git diff --cached 10e31980b98b816ba19f968590aa454bc494721b`；用户要求审查后提交，故基线后commit列表为空。对照README、依赖、docs/01–03及技能smell baseline，0项可行动规范问题，未发现需要拆分或抽象的明显异味。代理独立核对两环境17包/120测试/无密钥/无外部尝试、两份13次HTTP及重启，真实39包/14项检索/3模型2工具、估算0.026860元和第八批56项指纹一致。最严重待修项：无。

## Spec

另一独立只读代理`review_spec`对照9.1–9.3及“全新环境可复现验证”规格审查同一候选，0项发现。实际环境隔离、显式权重准备、原文引用、第二环境复跑、前批源码指纹、失败保留及验证边界均符合要求。未把最小问答扩称完整验收，第10批仍未完成。最严重待修项：无。

两轴均0项发现。审查后仅补充本审查记录及最终密钥/源码一致性核对，未修改业务代码、依赖或验证脚本。
