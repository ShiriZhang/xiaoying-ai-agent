# 合成资料

单一基础语料为 [knowledge.json](knowledge.json)，包含三主题各 4 份虚构资料。名称、日期与完整条文已由用户实际审阅接受，见 [REVIEW.md](REVIEW.md) 和 [确认记录](../examples/batch-2/review.json)。真实效果及最终综合验收见[交付记录](../examples/batch-10/verification.md)。

格式为 schema_version=1、synthetic=true、documents 列表。文档必含 doc_id、title、topic、version_date、effective_date、scope、passages；片段必含 passage_id、doc_id、text。每片段第一行为正文中的元信息声明，第二行起为可引用条文；读取返回完整原文，不修改空格或标点。机械匹配元信息不等于自动证明所有自然语言语义一致。

`load_snapshot(path)` 加载并校验资料，`CorpusStore(path).acquire()` 取得任务快照；调用 `reload()` 才发布后续任务的新快照。指纹使用规范 JSON 内容的 SHA-256；缩进/对象键顺序不影响指纹，正文、日期与标题等变更影响指纹。读取工具按该任务快照运行，未知/超量/故障均为错误观察，不伪造原文。

单 D01、D01/D02 冲突、人事生效前后与产品正文替换均使用测试临时副本，不修改基础文件。检索两路索引、API、模型与最终引用校验均已实现；重载入口与真实权重准备见[README](../README.md)，隔离变体与真实运行见第八、九批证据。
