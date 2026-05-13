# 第 17 章 远程抓取：学习笔记

当本地爬虫遇到 **IP 限制、带宽或算力瓶颈**，或需要 **7×24 调度** 时，通常会考虑 **远程主机、代理/IP 轮换、容器与云上编排**。本章从**技术部署**角度收口；**法律与条款边界**仍以第 18 章为准。

---

## 1. 核心知识点与原理

### 1.1 为什么要用远程服务器

- **降低单点封禁影响**：出口 IP 与家庭宽带不同；在合规前提下可配合**限速、重试、退避**与**代理池策略**（代理本身也需合法来源与合同）。
- **可移植与扩展**：云主机、容器镜像、CI/CD 便于复制环境；可按任务选配 CPU/内存/磁盘与出站带宽。

### 1.2 Tor 与匿名代理（概念 + 局限）

- **原理（简述）**：Tor 通过多层中继加密转发流量，**隐藏客户端到中间节点的直接关联**（洋葱路由）。
- **局限**：延迟与抖动较大；**登录个人账号**、浏览器指纹、Cookie 等都可能削弱匿名性；许多站点会**拦截 Tor 出口**或对自动化额外限制。
- **合规**：Tor 可用于合法隐私保护，但**不得**将其作为违反目标站条款、绕过授权或从事违法活动的工具。

**端口提示**：**Tor Browser** 本地 SOCKS 常见为 **9150**；独立 **`tor` 守护进程** 常见为 **9050**（以你的安装配置为准）。

### 1.3 远程主机形态（书中脉络 + 现代等价）

- **共享虚拟主机 / cPanel**：历史上可用 CGI 跑脚本；如今更常见 **SSH + venv + systemd/cron** 或 **Docker**。
- **云主机（AWS、GCP、Azure 等）**：按量计费、弹性扩缩容；注意 **IAM、密钥轮换、安全组出站规则** 与日志留存。
- **Serverless / 容器编排**：注意 **冷启动、超时、无状态、出站 IP 变化** 对目标站与白名单的影响。

### 1.4 运维要点（与前几章衔接）

- **调度**：`cron`、`systemd timer`、Windows 任务计划程序；见 `chapter-17/run_once.py` 作为最小入口示例。
- **配置与密钥**：环境变量、密钥管理服务，**勿**把密码写进镜像或公开仓库。
- **可观测性**：结构化日志、退出码、失败告警（第 6 章邮件可作通知渠道之一）。

---

## 2. 示例代码：通过 SOCKS（Tor）查看出口 IP

**前置**：本机已运行 Tor（或 Tor Browser 保持运行）。Python 侧常用 **`requests` + SOCKS**（底层依赖 **PySocks**），比全局 `socket` 猴子补丁更安全、易维护。

可运行脚本：

- **`chapter-17/tor_requests_ip.py`**：`requests` + `socks5h`（依次尝试 **9150 / 9050**）。  
- **`chapter-17/selenium_tor_chrome.py`**：Chrome `--proxy-server=socks5://...`（需与本机 Tor 端口一致）。

书中曾给 **`socket` 全局替换** + **PhantomJS 走代理**；此处改为：

1. **`requests` + `socks5h://`**（分别尝试 **9150 / 9050**）；  
2. 可选：**Selenium 4 + Chrome** 的代理参数（见同目录脚本内注释或 `selenium_tor_chrome.py`）。

```bash
pip install "requests[socks]"  # 内含 PySocks
```

```python
import requests

ports = (9150, 9050)
for port in ports:
    proxies = {
        "http": f"socks5h://127.0.0.1:{port}",
        "https": f"socks5h://127.0.0.1:{port}",
    }
    try:
        r = requests.get("https://icanhazip.com", proxies=proxies, timeout=15)
        print("port", port, "->", r.text.strip())
        break
    except OSError as e:
        print("port", port, "failed:", e)
```

---

## 3. 学习贴士

- **先本地后远程**：与第 14–16 章一致，先在可控环境跑通，再上代理与并行。  
- **代理采购**：商用代理、Tor、自建出口各有利弊；务必保留**合同与用途说明**备查。

---

## 4. 与本仓库其他示例

`chapter-17/run_once.py`：供调度器调用的最小「单次任务」壳。

## 练习建议

1. 用 **Dockerfile** 把爬虫与 `cron` 打进同一镜像（草图即可）。  
2. 为云主机编写 **systemd unit**：`ExecStart=/path/venv/bin/python job.py`。  
3. 记录一次「代理失败 → 直连回退」的策略伪代码，并标注合规前提。
