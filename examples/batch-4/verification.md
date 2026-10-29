# 第四批本地检索验证

批次日期：2026-10-29。基线为第三批提交93528e8。本批真实层是CPU embedding与混检，不默认调用DeepSeek，不代替最终六类生成模型验收。

## 4.1 编码器与显式准备

- 在独立CPython 3.12.13/Windows x86-64环境安装固定torch 2.9.0+cpu、transformers 4.57.1、safetensors 0.6.2、huggingface-hub 0.36.0。`uv.lock`锁定全部传递依赖；基础Mock安装仍不需要embedding extra。
- 实际执行 `uv lock --python .venv/Scripts/python.exe`、`uv sync --locked --extra embedding --no-editable --python .venv/Scripts/python.exe` 成功；torch报告CUDA不可用，按CPU运行。
- 实际显式运行 `python -I -m enterprise_knowledge_qa.prepare_weights --output models/bge-small-zh-v1.5`，下载6个必要文件，revision固定为7999e1d3359715c523056ef9478215996d62a620。models目录被忽略；manifest逐文件SHA-256校验。正常加载local_files_only=true、trust_remote_code=false、只用safetensors，无隐式下载或回退。
- 真实离线加载/段落与查询编码成功，socket.connect被阻断；[embedding-smoke.json](embedding-smoke.json)记录版本、revision、512维CLS归一化、1个CPU线程、512-token限制及查询前缀。tokenizer给出先编码再padding的性能提示，无失败/截断。
- `test_embeddings.py` 4/4通过（0.603秒）：Mock稳定、单位向量、独立子进程不导入torch/transformers、缺权重/坏manifest先失败、无隐式网络、非法向量/输入拒绝。

## 4.2 两路与RRF

纯Python BM25使用k1=1.5、b=0.75、正IDF log1p((N-df+0.5)/(df+0.5))，避免单文档IDF归零。分词为NFKC/casefold、汉字单字/相邻双字、拉丁字母/数字连续词；不引入外部分词词典。每路最多12，RRF k=60，输出默认6/可扩大12，同分按片段ID升序。

`test_retrieval.py`中6项RetrievalTests通过：两路排名/融合分数/去重与数量、单D01正分且不补齐、确定性同分、成功空集合、非法参数/编码错误、跨快照拒绝、元数据与词项表不可变、原文不改写。同文件另外3项重载测试通过，完整结果9/9（0.100秒）。

候选分数是排序依据，不是事实可信度。检索输入为标题+条文主体；完整canonical原文含出处声明，读取时逐字返回。检索失败不返回BM25单路成功，Mock向量不证明语义召回。

## 4.3 同一Agent执行器集成

`create_agent(settings, model, index)`将同一已取得的index.snapshot同时交给search、read与引用校验，禁止混用真实/Mock编码模式。Agent的embedding Trace取实际索引元信息，不再写“尚未加载”。

`test_retrieval_agent.py` 4/4通过（0.060秒）：实际执行两次不同query（默认6/扩大12），由同一Agent循环读取并结束；模型可据真实混检观察选择后续；注入编码故障产生retrieval_failed和空候选，进入模型上下文，无单路/Mock回退；模式不匹配明确拒绝。

## 4.4 原子重载与容量边界

`RetrievalStore`先加载新资料、完整构建BM25和向量，再一次发布不可变索引/快照对。旧任务只保留旧index，读/引用仍绑定旧snapshot。无效JSON或编码失败不会发布半新索引。

重载单元测试3/3通过；真实模型边界也在下方真实报告中全部通过：1080p→1440p的隔离副本重载改变资料/向量指纹与BM25词项，旧任务仍读1080p；单D01可召回，加入D02保留双方；基础文件字节未变。真实BGE检查超过512 token的段落和含前缀查询并拒绝，未运行截断后的输入。tokenizer报告602>512警告，随后编码器按契约抛错；这不是业务测试失败。

实际真实BgeEncoder注入一次编码错误，返回retrieval_failed、候选为空，未返回仅BM25结果。

## 4.5 真实召回

实际运行 `python -I -m enterprise_knowledge_qa.retrieval_check --weights models/bge-small-zh-v1.5 --output examples/batch-4/real-retrieval`；权重准备以外运行socket.connect阻断，无DeepSeek请求。初次真实检索运行 [ef28c3a12033470a9f08258917c696a4.json](real-retrieval/ef28c3a12033470a9f08258917c696a4.json) 全部通过，耗时16.359秒。

[预期清单](retrieval-cases.json)包含7个输入：明确报销材料、口语改写、人事咨询与其他主题干扰、报销冲突双方、导出格式、分辨率改写、新旧请假双方；分别返回6/12候选共14条结果，所需片段均实际召回，无missing。报告逐条保存两路排名、融合参数、实际候选、资料/权重指纹和包版本；不只保存“通过”布尔值。

当前结果只说明这份小语料上的指定输入覆盖，不宣称通用最优、统计稳定或模型最终回答正确。没有为了过测试隐藏旧文档/按日期裁决；首次无缺失不捏造失败或调参经历，后续复跑保留独立文件。

## 4.6 复现文档与安装边界

README已补充锁定依赖的基础/embedding安装、显式prepare_weights、retrieval_check与库接口重载步骤；docs/02记录精确分词/输入/编码/BM25/RRF参数，docs/03链接预期与实际证据。公开.env.example记录固定revision，无真实密钥。

安装与准备/重载命令已实际执行。额外按README基础路径在独立`.cache/batch4-mock-env`执行不含extra的锁定安装：仅安装项目和python-dotenv两个包，无torch/transformers；该环境运行78/78离线测试通过（2.677秒）。它只证明本批Mock依赖独立，不冒称未完成的API冷启动第9批通过。

README/docs/本批记录61个本地链接初次检查无缺失；OpenSpec严格校验通过。用户要求的双轴代码审查已完成，过程与最终结论见下节。

## 代码审查与最终回归

- [双轴审查](code-review.md)：Standards与Spec初审均无阻塞问题，各提出1项非阻塞建议（共用RRF分数计算、修正文档旧状态），已修复并由各轴复核确认；最终未解决项均0。
- [主环境完整报告](unittest.txt)：最终78/78通过（2.135秒）；[独立Mock环境报告](mock-unittest.txt)：最终78/78通过（2.799秒），仅项目和python-dotenv两个包，没有torch/transformers。
- 最终RRF源码已重新运行 [0eabfea5d9d749c7bcacb8eaa2e996e7.json](real-retrieval/0eabfea5d9d749c7bcacb8eaa2e996e7.json)：14条召回及8项边界均通过（18.921秒），没有missing，初次报告保留未覆盖。两次小样本不宣称统计稳定性。
- `uv pip check`核对27个安装包兼容。没有本批测试失败、真实召回失败或业务规格修改；tokenizer长度警告为预期拒绝边界，保留说明，不伪造失败修复故事。
- [fingerprints.json](fingerprints.json)记录最终源码/依赖锁/测试/公开文档/资料SHA-256和最终真实运行ID，安装源码与主工作区及Mock环境源码逐文件一致。未提交权重、真实.env或隐私数据。本批未调用DeepSeek，生成调用费用0元。
- OpenSpec刷新确认4.1–4.6全部完成，整体22/46，剩余24项；本地规划继续按既定忽略规则留在本地，公开代码与证据提交推送不包含openspec/或.agents/。
