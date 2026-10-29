# 第二批资料与读取验证

批次日期：2026-10-29。本记录区分实际离线验证、人工预期与尚未发生的用户审阅；没有真实模型调用、向量编码或问答结果。

## 2.1 资料与结构校验

- `data/knowledge.json`：12 个文档、每主题 4 个、12 个编号片段；公司“星帆科技”和产品“星帆剪辑”均为虚构草案名称。
- 已定数值和内容由资料测试逐项检查。D01/D02 保留无替代关系的 30/15 天；D06 的正文声明 2026-10-01 生效及替代 D05，版本日期为 2026-09-01。
- 使用标准库实现不可变资料对象、严格字段/日期/标识/片段归属/统一范围校验，以及逐字元信息声明与正文首部的匹配。此机械校验不宣称理解任意自然语言的逻辑矛盾；全文规则、替代关系的语义仍需人工审阅及后续真实测试。
- `uv pip install --offline --python .venv/Scripts/python.exe .` 成功，无新增依赖。缓存与环境跨盘使 uv 提示改用复制，安装成功。
- `.venv/Scripts/python.exe -I -m unittest discover -s tests -p test_knowledge.py -v`：6/6 通过（0.041 秒），覆盖重复文档/片段/JSON 键、缺字段/正文、错误片段归属、非法日期、元信息不一致、缺文件、坏编码、单 D01 与不可变对象。

## 2.2 指纹与任务快照

- 指纹为验证后内容的规范 JSON（字段排序、UTF-8、保留正文原样）的 SHA-256，JSON 缩进或对象键顺序不改变指纹；正文与元信息改变会改变指纹。
- `CorpusStore.acquire()` 在任务开始获取并保留不可变快照，文件变化不自动生效；`reload()` 先完整加载验证再发布，无效重载保留当前有效快照并抛错。尚无检索索引，双路重建仍属 4.4。
- 5 项快照测试首次有 1 项错误：只读 mapping 没有 clear 方法，实际抛 AttributeError，而测试期待 TypeError；改为检查真实的删除操作被拒绝后，5/5 通过（0.070 秒）。没有更改业务行为。
- 已实际验证旧任务与新任务快照隔离、格式无关指纹、内容/元信息指纹变化、失败重载、单 D01 到 D01/D02 保留双方、对象与查找表不可改写。每项测试核对基础语料文件 SHA-256 未变。

## 2.3 读取工具

- `ReadTool` 在构造时绑定任务快照，一次接受 1–3 个唯一片段 ID，成功返回逐字原文、出处与资料指纹；只有整批成功才更新本实例 read-set。
- 标准观察包含 tool/status/corpus_fingerprint/passages/error。错误分 validation_error（invalid_arguments）与 tool_error（unknown_passage/read_failed）；错误不返回部分或替代原文，不包含底层异常详情，也不自动重试。
- 内部 fault_hook 实际抛出 OSError 的测试确认：错误观察无私有异常内容，无伪原文，无隐藏重试，之前成功的 read-set 保留。未来执行器可复用 `validate_read_ids` 在预算计数前校验参数。
- `.venv/Scripts/python.exe -I -m unittest discover -s tests -p test_reading.py -v`：6/6 通过（0.039 秒）。覆盖冲突双方与 3 片段原文、空/超量/重复/非法参数、未知 ID、注入故障、返回对象修改隔离、任务 read-set 隔离，以及源文件删除/重载后仍从各自快照读取。

## 2.4 用户审阅与资料导航

- 已向用户展示 `data/REVIEW.md` 中 12 份完整正文、名称、日期、目录与变体预期。用户实际回复：“已阅读完整审阅稿，确认接受”。原话和指纹保存于 [review.json](review.json)，未将此前设计确认冒充此次资料确认。
- 本次接受的资料指纹：`sha256:47bf2f316d7b84615a1fe9807faeaace4c84e50395c767af0dfc4d84bd8d2ce1`。
- docs/01 已添加实际资料导航、12 份目录与日期、单 D01/冲突/有效替代/未来生效预期；README 与 data/README 的实现状态同步。docs/04、05 如实记录 AI 修改、用户资料审阅、未记录个人工时和本批 0 次真实调用。
- `.venv/Scripts/python.exe -I -m unittest discover -s tests -p test_corpus_review.py -v`：3/3 通过（0.006 秒），核对确认记录与当前指纹一致、审阅稿包含全部逐字原文、人事生效边界/替代证据与变体预期。该测试只核对资料和记录，不能证明模型能正确应用日期规则。
- README、docs/ 与 data/ 中 47 个本地链接实际检查均存在。

## 范围边界

本批无新增依赖、无真实模型请求、无权重下载、无业务规格变更。所有真实模型、检索索引、API、最终引用结果与完整冷启动验收属于后续批次。用户此次审阅不代表亲自完成资料修改实验或最终引用支持性核查。未初始化 Git、未提交或发布。

## 最终复核与证据

- [完整测试报告](unittest.txt)：28/28 通过（0.976 秒），包含第一批回归测试，没有跳过项。
- `uv pip check --python .venv/Scripts/python.exe`：2 个已安装包兼容，无新增运行依赖。
- `openspec validate enterprise-knowledge-qa --strict`：通过，仅为规划格式校验。
- [读取实际观察](read-observations.json)：执行本地读取组件后保存的冲突双方、未知 ID、超量和注入故障结果；明确标为离线组件验证，不是模型输出或完整 Trace。
- 已逐文件核对安装包与 src 下 Python 源码一致；[fingerprints.json](fingerprints.json) 保存本批源码/测试/资料/文档 SHA-256 与资料指纹，供后续核对。
- 每项完成后刷新 apply，最终 2.1–2.4 均 done，整体 8/46，剩余 38 项保持未完成。下一项为 3.1，不自动扩展本批范围。
