# 第七批实际验证

日期：2026-10-29（America/New_York）。范围7.1–7.3，基线`74973563b6004a82466a45822d052ec6ae0eed2f`。AI实现、运行和记录，未代称用户亲自运行/核查。无DeepSeek付费调用，本批生成费用0元；真实语义、第8批两次六类运行及第9批冷启动均未完成。

## 安装和实际命令

沿用Windows/CPython 3.12.13隔离`.venv`，从声明入口安装非editable项目。新增直接依赖FastAPI 0.115.14、Pydantic 2.11.7、Uvicorn 0.34.3；test可选组httpx 0.28.1。所有传递版本和源已锁入uv.lock，原embedding版本未升级。

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.cache/uv'
uv lock
uv sync --locked --extra embedding --extra test --no-editable --python .venv/Scripts/python.exe --reinstall-package enterprise-knowledge-qa
.venv/Scripts/python.exe -I -m unittest discover -s tests -v
.venv/Scripts/python.exe -I examples/batch-7/exercise_http.py
.venv/Scripts/python.exe -I examples/batch-7/exercise_http.py --output examples/batch-7/http-demo-final.json --powershell-output examples/batch-7/readme-requests.json
openspec validate enterprise-knowledge-qa --strict
```

上面的两次HTTP捕获已执行，输出保留于本目录；复跑须指定尚不存在的新文件，脚本拒绝覆盖旧证据。test依赖按[FastAPI官方测试入口](https://fastapi.tiangolo.com/tutorial/testing/)接入TestClient/httpx；启动器按[Uvicorn设置](https://uvicorn.dev/settings/)固定本地地址和单进程，不将其当生产部署。版本为本批实际验证的固定版本，不宣称最新版本。

## 实际结果

- 全量115项测试通过，包含新增7项API集成/启动测试，见[offline-tests.txt](offline-tests.txt)。覆盖创建、问答、完整历史/Trace、canonical引用、未知会话、非法JSON/空白/类型/额外字段、存储503、业务incomplete与HTTP状态分离、无独立问题长度上限、重启/隔离、live启动条件失败不Mock不泄露密钥。
- 健康检查在live配置和注入索引下，多次请求health/create/history均未创建模型工厂；模型调用为0。实际live模型HTTP问答未运行，这一测试不证明真实服务可达。
- [首次HTTP运行](http-demo.json)和[最终HTTP运行](http-demo-final.json)各实际执行13次loopback HTTP请求；服务子进程启动两次，使用同一临时SQLite文件重启。验证D09导出→D10分辨率重新读取、第二会话无对象时先追问、重启后再读D10、201/200/404/422以及拒绝fault字段。
- [PowerShell实际结果](readme-requests.json)执行与README相同的Invoke-RestMethod请求，中文Body转UTF-8字节；首轮/续问均answered，历史4条，非法问题422、未知会话404。完整回答、输入上下文、引用和Trace均保存，不是预填输出。
- 子进程为显式Mock，测试保护拒绝非loopback地址解析/连接及BGE构造；权重目录不存在，未创建。HTTP本身需要本地通信；“离线”指没有外部请求或下载。数据库在临时目录中，用完关闭清理，未入库。

Mock演示策略只覆盖导出格式、分辨率、报销材料；分支选择演示动作，答案逐字来自实际read，不硬编码产品数值或制度期限。它不验证真实冲突处理、改写、记忆语义或六类效果。不支持的输入明确incomplete并说明尚未执行语义判断。

## 错误与复跑

- 初次依赖锁定/安装在受限网络中无法解析PyPI/PyTorch源；获准依赖网络后锁定和安装成功，未切换模型/包源绕过。
- 首次API测试阻塞，10秒定位输出显示卡在Windows asyncio的_fallback_socketpair/accept，尚未进入路由。停止该次测试进程后，在允许本地socket环境重跑6项API测试通过；新增启动失败测试后全量115项通过。未修改业务代码掩盖该环境限制。
- PowerShell验证脚本以UTF-8 BOM保存以兼容Windows PowerShell 5读取中文；实际HTTP客户端显式UTF-8字节编码。普通API不提供测试保护或故障开关。

## 交付边界与审查

API完整结果和Trace随会话短事务保存在SQLite；GET的requests可核查完整结果，messages为原始业务消息。QA_TRACE_PATH仍供独立Agent显式保存使用。单进程、loopback，无UI、额外业务CLI或多进程承诺。HTTP路由、Mock/live请求方式和错误契约见README及docs/02新增接口章节。

本批未运行live HTTP问答、六类真实业务或全新空环境；已安装环境的测试与服务重启不能替代这些验收。个人工时不推算。规划文件按既有规则仅本地保存。

最终源码、测试、验证脚本与依赖文件的51项指纹见[source-fingerprints.json](source-fingerprints.json)，UTF-8去BOM并归一化LF后SHA-256；实际[安装包版本](environment-packages.json)共39项，uv pip check兼容检查通过。OpenSpec严格校验通过，不将其当业务语义验收。

## Standards

按code-review技能以本批基线进行独立只读审查：`git diff --cached 7497356`非空，用户要求审查后才提交，当时基线后commit列表为空。依据README、docs/01–03、依赖声明和技能smell baseline，未发现规范违反或需修改的判断性smell。四路由复用已有会话/执行器，请求不接收历史/模式/故障开关，健康检查不创建模型，依赖精确锁定，本地单进程与证据边界一致。

## Spec

另一个独立只读代理对照本地OpenSpec和公开docs/01审查7.1–7.3，未发现缺失、错误实现或范围扩张。HTTP、PowerShell、两轮追问、隔离与重启实际证据符合实现；受控Mock有限范围、真实语义与冷启动尚未运行均明确说明。仓库无issue-tracker文档，本次直接使用用户指定规格，不依赖issue跟踪。

两轴最终均0项可行动问题，无最严重待修项。115项测试、39包兼容检查、实际HTTP/PowerShell验证和OpenSpec严格校验通过；源码审查后无业务代码改动。
