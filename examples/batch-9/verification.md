# 独立环境与真实权重复现

两个干净副本在不继承全局包的独立环境中完成基础依赖安装、120项离线测试、空密钥/空模型缓存Mock服务及13次HTTP请求。另显式安装CPU编码依赖、独立准备固定revision六个权重文件，验证真实召回及真实DeepSeek HTTP问答。

保留安装、网络、权限和首次请求失败及复跑，不借开发机隐式模型缓存替代准备步骤。此为当时源码的冷启动证据，未称为记忆修复后业务源码再次冷安装；依赖和检索实现未变，当前业务回归另行保存。

## 复现步骤

从干净检出开始，不复制开发环境、配置密钥、权重或运行数据库。按[README](../../README.md)先仅安装基础与test依赖，在准备真实权重之前执行：

```powershell
.venv/Scripts/python.exe -I examples/batch-9/verify_environment.py --output .cache/cold-offline-new
.venv/Scripts/python.exe -I -m enterprise_knowledge_qa --env-file .env.example
.venv/Scripts/python.exe -I examples/batch-7/exercise_http.py --output .cache/cold-http-new.json --powershell-output .cache/cold-requests-new.json
```

随后按README显式安装embedding依赖、准备固定revision权重并运行retrieval_check。最小真实HTTP验证需有效本地密钥并产生费用：

```powershell
.venv/Scripts/python.exe -I examples/batch-9/exercise_live_http.py --live --env-file C:/private/qa.env --weights models/bge-small-zh-v1.5 --output .cache/cold-live-new.json
```

将配置路径替换为实际本地文件。脚本通过内存环境向服务传递密钥，不复制或输出密钥。输出必须使用新路径，首次失败与后续结果分别保存。

## 原始证据

- [原失败](install-mock.txt)
- [成功安装](install-mock-retry.txt)
- [初次环境](offline-initial/environment.json)
- [120项测试](offline-initial/tests.txt)
- [实际HTTP记录](http-initial.json)
- [README PowerShell记录](powershell-initial.json)
- [embedding组安装](install-embedding.txt)
- [live环境记录](live-http.json)
- [下载记录](prepare-weights.txt)
- [live报告weights_manifest](live-http.json)
- [真实BGE报告](real-retrieval/f47ea46754514197aead19cdf56c331c.json)
- [真实HTTP结果](live-http.json)
- [第二环境安装](install-recheck.txt)
- [版本/源码指纹](offline-recheck/environment.json)
- [120项测试](offline-recheck/tests.txt)
- [13次HTTP](http-recheck.json)
- [PowerShell](powershell-recheck.json)
- [一致性核对](source-consistency.json)
