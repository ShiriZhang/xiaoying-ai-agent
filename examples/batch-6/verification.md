# 会话、持久化与记忆工程验证

108项离线测试通过，覆盖SQLite完整问答、重启续问、会话隔离、短事务、完整轮次历史窗口、锚点来源与失效降级。记录中的生成动作和向量为受控Mock。

真实SQLite故障测试暴露过旧锚点失效写入失败后可能重新启用的问题，通过跨仓储实例共享隔离标记与回归修复。另修正测试连接未关闭导致的Windows清理失败。模型等待不持有写事务；存储失败明确报告未保存。

## 记录中的技术明细

以下表格属于该报告对应的运行版本；不同版本及时间的数量不混用。

| 记录 | 实际工程结果 |
| --- | --- |
| [首轮](first-round.json) | 检索、读取D09、同次finish提出锚点，3模型/2工具，无额外记忆调用，保存成功 |
| [重启续问](restarted-follow-up.json) | 重开SQLite文件，历史预算冻结为1以触发跨窗；selected_message_ids为空，仍提供合法对象锚点，并重新检索/读取D10 |
| [非法锚点](invalid-anchor.json) | 未知消息来源被拒，业务out_of_scope保留，格式修正0，memory_valid=false |
| [模型故障](model-failure.json) | incomplete，旧锚点不启用，无伪造更新，故障结果本身保存成功 |
| [锚点重建](rebuilt-anchor.json) | null旧锚点、近期历史输入后同次finish重建结构合法锚点；受控动作主动提交incomplete业务状态，记忆校验独立，二者不混同 |
| [SQLite保存失败](storage-failure.json) | 真实SQLite触发器拒绝助手写入，事务回滚，已有用户消息保留，结果saved=false，memory_valid=false |
| [最终持久化状态](persisted-state.json) | 完整原始业务消息仍在，最后请求running且只有用户消息，旧锚点无效；没有伪造已保存助手 |

## 原始证据

- [offline-tests.txt](offline-tests.txt)
- [首轮](first-round.json)
- [重启续问](restarted-follow-up.json)
- [非法锚点](invalid-anchor.json)
- [模型故障](model-failure.json)
- [锚点重建](rebuilt-anchor.json)
- [SQLite保存失败](storage-failure.json)
- [最终持久化状态](persisted-state.json)
- [source-fingerprints.json](source-fingerprints.json)
