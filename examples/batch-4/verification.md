# 真实CPU混合检索验证

使用固定revision的本地BGE、BM25与RRF，验证7个输入分别取6/12候选，共14项召回，以及重载和容量边界。真实编码在本地运行，不调用生成模型。

检索覆盖明确问题、自然改写、干扰和冲突双侧。单D01、加入D02、正文替换和长输入拒绝使用隔离副本；重建失败保留旧索引，任务内始终使用同一快照。历史测试78项通过，当前完整测试另见[效果验证](../../docs/03-evaluation.md)。

## 原始证据

- [embedding-smoke.json](embedding-smoke.json)
- [ef28c3a12033470a9f08258917c696a4.json](real-retrieval/ef28c3a12033470a9f08258917c696a4.json)
- [预期清单](retrieval-cases.json)
- [双轴审查](code-review.md)
- [主环境完整报告](unittest.txt)
- [独立Mock环境报告](mock-unittest.txt)
- [0eabfea5d9d749c7bcacb8eaa2e996e7.json](real-retrieval/0eabfea5d9d749c7bcacb8eaa2e996e7.json)
- [fingerprints.json](fingerprints.json)
