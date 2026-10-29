# 第一批工程验证记录

批次日期：2026-10-29（客户端日期）。本文件记录实际工程验证，不是业务验收。

## 1.1 安装与隔离导入

- Windows 11 x86-64（10.0.26300），uv 0.11.28；独立 CPython 3.12.13，非 Anaconda。
- `uv venv --python 3.12.13 --managed-python .venv` 创建成功，`include-system-site-packages = false`。
- 单一依赖声明为 `pyproject.toml`：运行时无第三方依赖，构建依赖精确固定 `setuptools==80.9.0`；后续功能依赖尚未选择，不声称 FastAPI 或 embedding 已安装。
- 首次 `uv pip install --python .venv/Scripts/python.exe .` 因受限网络下 PyPI DNS 失败；接着运行的测试报 `ModuleNotFoundError`，未算通过。
- 获准网络访问后重跑同一安装成功，构建并安装 `enterprise-knowledge-qa==0.1.0`。
- `.venv/Scripts/python.exe -I -m unittest discover -s tests -v`：1 项通过。测试验证从虚拟环境 site-packages 导入、分发版本一致和环境隔离。
- `uv pip list --python .venv/Scripts/python.exe`：环境仅有 `enterprise-knowledge-qa 0.1.0`。构建依赖由隔离构建环境使用，不是运行依赖。

## 1.2 配置与忽略规则

- 随配置实现加入唯一运行依赖 `python-dotenv==1.1.1`，仍由同一 `pyproject.toml` 声明。重新安装成功；最终运行环境共 2 包（项目 0.1.0、python-dotenv 1.1.1）。`uv pip check --python .venv/Scripts/python.exe` 无依赖冲突。1.1 中“无运行依赖”为最初骨架阶段状态。
- 配置加载显式要求 live/mock，环境变量优先于指定文件，相对路径以文件目录为基准，关闭变量插值与向父目录自动查找；不创建运行文件、不加载权重、不请求网络。
- `.env.example` 只有公共配置与空密钥/revision 占位；8/6 上限禁止改写，60/300 秒与 8000 历史预算校验为正数。预算执行本身尚未实现。
- `.venv/Scripts/python.exe -I -m enterprise_knowledge_qa --env-file .env.example` 实际返回 `mode=mock`、`configuration=valid`、`service=not_implemented` 及 8/6、60/300、8000，无密钥内容。
- 首次 8 项测试中 3 项因系统临时目录权限报错。改用仓库内 `.cache/` 临时目录后，剩 1 项 Git 输入换行测试失败；改用 NUL 分隔输入后，8 项全部通过（0.833 秒）。没有跳过测试。
- 测试实际覆盖无密钥/无权重 Mock 配置、阻断 socket、配置覆盖、相对路径、非法预算、live 缺配置明确失败、检查输出脱敏、分发安装与隔离导入。
- 忽略规则使用 Git `check-ignore --no-index --stdin -z` 实测；临时 Git 元数据在 `.cache/` 下，不初始化项目。`.env*`、本地权重、运行数据库及 sidecar、原始 Trace/缓存被忽略；`.env.example`、data、examples 可纳入版本控制。忽略规则不能阻止强制添加或清除已跟踪文件；最终提交检查属于 10.2。

## 1.3 README 入口核对

- README 安装命令对应已执行的独立环境、实际包安装和兼容性检查；测试命令对应已执行的 8 项工程测试。`uv python install 3.12.13` 首次因全局安装目录锁文件权限失败，获准访问后成功（实际复用了现有 managed Python，不声称重新下载 Python）。
- README 18 个本地导航链接逐一检查均存在。
- 实际运行模板配置检查成功；复制模板到临时 `.env` 后检查成功，没有覆盖用户 `.env`。
- 将进程模式设为 live 且密钥为空，实际退出码 2，错误明确为 `DEEPSEEK_API_KEY is required for live mode`，未产生网络调用或业务结果。
- README 四个 API 及真实/Mock 启动、请求、权重准备、三层业务验证入口均标明未实现，并指向后续任务；未给出不存在模块的启动命令或伪造成功输出。

## 1.4 工时、贡献与预算记录

- docs/04 的实际变更表区分 AI 已做工作、用户授权与尚未发生的个人审阅/验证；docs/05 提供后续计时和费用字段，未知人工工时明确为未记录，不推算或计零。
- 实际核对计划行 `[2, 4, 3, 3, 6]`，合计 18 小时，验证修复文档预留 6 小时；费用计划为真实调用 30 元。没有发起真实模型请求，本批调用费用 0 元，不据此推断账号余额。
- README 与 docs/04、05 共 27 个本地链接检查均存在。已记录失败原因与修复，未编造用户个人实践。
- `openspec validate enterprise-knowledge-qa --strict` 通过；只说明规划格式有效，不证明业务验收。

## 限制

当前目录尚非 Git 仓库；本批不初始化 Git、不提交或发布。API、语料、模型适配、业务循环、真实 embedding、真实模型验证和完整冷启动验收均属后续任务，未执行。不读取或上传真实密钥、权重或个人数据。

## 最终复核

- 将测试的权重与运行文件路径改为独立临时目录，避免开发者已有文件影响结果。最终测试 8/8 通过（0.835 秒），实际完整报告见 [unittest.txt](unittest.txt)。
- [fingerprints.json](fingerprints.json) 保存最终工程源码、配置、测试与文档的 SHA-256，供核对证据版本；不是 Git commit SHA。
- OpenSpec apply 刷新确认 1.1–1.4 均完成，整体 4/46，剩余 42 项。范围外任务均未勾选。
