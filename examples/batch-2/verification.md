# 合成资料、快照与原文读取验证

验证12份合成文档的必需字段、唯一ID、日期、片段归属及正文元信息；快照不可变，内容修改改变指纹，重载前既有任务保留原快照。读取返回完整原文，未知ID、超量读取和注入故障均明确失败。

候选人已审阅基础条文，确认记录与资料指纹保留在review.json。此记录验证资料与读取契约，不证明真实模型是否正确解释冲突。

## 原始证据

- [review.json](review.json)
- [完整测试报告](unittest.txt)
- [读取实际观察](read-observations.json)
- [fingerprints.json](fingerprints.json)
