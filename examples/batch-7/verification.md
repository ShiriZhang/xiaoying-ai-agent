# HTTP服务、中文请求与重启验证

115项离线测试通过；实际启动本机服务，完成13次HTTP及README PowerShell请求，覆盖四个接口、中文UTF-8、两轮追问、会话隔离和进程重启。

运行时阻断外部连接和真实BGE构造，使用空权重目录及临时SQLite；证明服务与受控离线流程，不证明真实模型语义。安装及本机通信首次遇环境限制，获准运行后复跑结果另存。

## 原始证据

- [offline-tests.txt](offline-tests.txt)
- [首次HTTP运行](http-demo.json)
- [最终HTTP运行](http-demo-final.json)
- [PowerShell实际结果](readme-requests.json)
- [source-fingerprints.json](source-fingerprints.json)
- [安装包版本](environment-packages.json)
