# 第 17 章 远程抓取：学习笔记

前面 16 章解决的是「怎么在本地把数据抓下来」，本章解决的是「怎么让抓取在本地之外的机器上长期、稳定地跑」。当本地爬虫遇到 **IP 限制、带宽或算力瓶颈**，或需要 **7×24 调度** 时，思路就是把任务搬到 **远程主机** 上，配合 **代理 / IP 轮换**（本章用 Tor 演示 SOCKS 代理的接法）与 **定时调度**（cron / systemd timer / 任务计划程序）构成完整闭环。核心机制一句话：**代理只改出口，调度只改触发时机，爬虫逻辑本身完全不变** —— 第 1–16 章写好的解析代码可以原样搬上去。本章从**技术部署**角度收口；**法律与条款边界**仍以第 18 章为准，Tor 与代理绝不能用来绕过授权或违反目标站条款。读完本章，你应当能把任意一个前面章节写好的爬虫，打包成一个「可调度、可换出口、可观测」的远程任务。

**本章目标**

1. 说清楚「为什么本地不够用」，能从**封禁、资源、调度**三个维度判断何时该上远程
2. 理解 **HTTP 代理与 SOCKS 代理**的差异，以及 `socks5` 与 `socks5h` 中「谁负责 DNS 解析」的区别
3. 理解 **Tor 洋葱路由**的基本原理与工程局限（延迟、出口封锁、匿名性削弱）
4. 会用 **`requests` + PySocks** 走本地 Tor SOCKS 端口查看出口 IP
5. 会用 **Selenium 4 + Chrome** 的 `--proxy-server` 参数让浏览器流量走代理
6. 能把一个 Python 入口脚本包装成可被 **cron / systemd / 任务计划程序** 调用的「单次任务」

---

## 1. 核心知识点与原理

### 1.1 为什么要用远程服务器

本地跑爬虫有三类绕不开的短板，远程主机分别对症下药：

| 本地短板 | 表现 | 远程方案 |
|---|---|---|
| **出口 IP 单一** | 家庭宽带一个 IP，触发限流/封禁后全网任务停摆 | 云主机出口 IP 独立，配合代理池分散风险 |
| **资源受限** | 笔记本要关机、要休眠，带宽和算力都不稳定 | 云主机按任务选配 CPU/内存/磁盘与出站带宽 |
| **无法 7×24 调度** | 人肉守着跑不现实 | cron / systemd timer 常驻触发，机器不睡 |

两点补充：

- **降低单点封禁影响**：远程出口 IP 与家庭宽带不同；在合规前提下可配合**限速、重试、退避**与**代理池策略**（代理本身也需合法来源与合同）。但注意换 IP 只是降低**误伤面**，不是豁免权 —— 行为过激照样被封。
- **可移植与扩展**：云主机、容器镜像、CI/CD 便于复制环境；一次配好 `venv` + 依赖清单，换机器等于 `git clone && pip install`。

一个常见的误判是「本地能跑 = 远程能跑」。实际迁移时经常踩到三类差异：**时区**（服务器默认 UTC，日志时间与本地对不上，本章 `run_once.py` 特意用 `timezone.utc` 就是示范）、**字符编码**（cron 环境下 `LANG` 可能不是 UTF-8，打印中文直接 `UnicodeEncodeError`）、**网络出口**（云厂商的 IP 段本身就在很多站点的风控名单里，直连质量未必比家庭宽带好）。所以搬远程的第一步不是部署，而是先跑一个最小探针脚本确认出口、时区、编码三件事。

### 1.2 代理协议：HTTP 代理与 SOCKS 代理

「代理」的共同点是在客户端与目标站之间插入一跳中转，差异在**工作层次**：

| 维度 | HTTP 代理 | SOCKS5 代理 |
|---|---|---|
| 工作层 | 应用层，只懂 HTTP(S) | 传输层，可转发任意 TCP（HTTP、FTP、SSH 皆可） |
| 常见形态 | `http://proxy:8080`，支持 `CONNECT` 隧道 | `socks5://proxy:1080` |
| Python 接入 | `requests` 原生支持 | `requests` 需 **PySocks** 提供底层支持 |
| 典型代表 | 商用代理网关、Squid | **Tor 本地端口**、SSH 动态转发（`ssh -D`） |
| 认证方式 | 常见于 URL 内嵌 `user:pass@` | SOCKS5 协议自带用户名/密码认证字段 |

`requests` 对两种代理的接法是同一个 `proxies` 参数，区别只在 scheme 字符串：`http://` / `https://` 走 HTTP 代理，`socks5://` / `socks5h://` 走 SOCKS（后者要求已装 PySocks，否则请求时会抛 `InvalidSchema` 一类的错误提示缺依赖 —— 本章 `tor_requests_ip.py` 在发请求前先 `import socks` 试导入，就是为了把「缺依赖」从「网络不通」里区分出来，报错信息更准确）。

**`socks5` 与 `socks5h` 的区别**是很多教程不讲但实战必问的：

- `socks5://`：域名在**本地解析**，再把 IP 交给代理转发 —— DNS 查询会泄露给本地网络（且若本地 DNS 被污染，拿到的就是错的 IP）。
- `socks5h://`：`h` 表示 hostname，域名连原文一起交给 **SOCKS 服务器解析** —— 走 Tor 时这意味着 DNS 请求在 Tor 网络内部完成，不会从本地泄出。本章脚本统一用 `socks5h`。

### 1.3 Tor 与洋葱路由（概念 + 局限）

- **原理（简述）**：Tor 客户端先拿一份中继节点目录，随机挑「入口 → 中继 → 出口」三跳建链；数据包像洋葱一样**层层加密**，每一跳只能解开自己那一层，只知道上一跳和下一跳是谁，从而**隐藏客户端到中间节点的直接关联**。目标站看到的是**出口节点**的 IP。
- **局限**：
  - **延迟与抖动大**：三跳加密转发，单请求动辄数百毫秒到数秒，不适合高并发抓取。
  - **匿名性可被削弱**：**登录个人账号**、浏览器指纹、Cookie、页面内指纹脚本，任何一项都可能把流量重新关联回你。
  - **出口常被拦截**：Tor 出口节点列表是公开的，许多站点直接**整段封锁**或对自动化额外校验 —— 所以 Tor 适合演示「代理怎么接」，不适合当作生产爬虫的主力出口。
- **合规**：Tor 可用于合法隐私保护，但**不得**将其作为违反目标站条款、绕过授权或从事违法活动的工具。

与商用代理对比着理解更清楚：商用代理卖的是「干净、稳定、可换的 IP 池」，Tor 给的是「匿名性强但慢且常被封锁的链路」。学习目标用 Tor 足够（免费、本地可起）；生产需求应走有合同的商用代理或自建出口。

**端口提示**：**Tor Browser** 启动后本地 SOCKS 常见监听 **9150**；独立 **`tor` 守护进程**（Linux 包安装的 `tor` 服务）常见为 **9050**（以你的安装配置为准）。本章两个脚本覆盖了这两个端口。

补充一个工程上有用的细节：Tor 的**链路（circuit）默认约十分钟轮换一次**，也就是说同一进程连续抓十分钟，出口 IP 就可能悄悄换掉。想主动换链路，可以向 Tor 的 **ControlPort**（默认 9051，需配置认证）发 `SIGNAL NEWNYM` 指令；但频繁换链路会加重 Tor 网络负担，且对「目标站看到的你」帮助有限 —— 行为指纹没变。学习阶段知道这个机制存在即可，不建议在练习里刷它。

### 1.4 远程主机形态（书中脉络 + 现代等价）

| 形态 | 当年书中的样子 | 现代等价做法 | 注意点 |
|---|---|---|---|
| **共享虚拟主机 / cPanel** | CGI 目录放脚本，Web 触发 | **SSH + venv + systemd/cron** 或 **Docker** | 共享主机权限受限，长任务易被杀 |
| **云主机（AWS、GCP、Azure 等）** | 租 VPS 手动部署 | 按量计费、弹性扩缩容，镜像一键复制 | **IAM、密钥轮换、安全组出站规则**、日志留存 |
| **Serverless / 容器编排** | 尚未普及 | 定时触发的云函数、K8s CronJob | **冷启动、超时上限、无状态、出站 IP 变化** 对目标站与白名单的影响 |

选型的判断逻辑很简单：任务能拆成「几分钟跑完一次」→ Serverless 省钱；要常驻、要状态、要长连接 → 云主机；只是学习 → 本机 Docker 就够。

迁移 checklist（按顺序过一遍能省掉大半部署事故）：

1. **依赖固化**：本地 `pip freeze > requirements.txt`，远程 `pip install -r` 后先跑一遍冒烟脚本。
2. **时区与编码**：确认 `TZ`、`LANG` / `LC_ALL`，脚本内时间一律显式带时区（UTC 最稳）。
3. **出站规则**：安全组 / 防火墙是否放行目标端口；服务器所在网段是否被目标站整段风控。
4. **凭据就位**：环境变量或密钥管理服务配好，确认镜像与仓库里没有明文密码。
5. **日志落盘**：调度器的 stdout/stderr 重定向到带轮转的日志文件，别让磁盘悄悄写满。

### 1.5 调度：把脚本变成「可被定时触发的单次任务」

远程抓取的调度侧约定俗成一个模式：**脚本本身只做一次完整工作、跑完即退**，把「什么时候跑」完全交给外部调度器。这样的好处是失败可重试、日志好收集、进程不会越攒越多。

| 调度器 | 平台 | 触发配置示例 |
|---|---|---|
| **cron** | Linux / macOS | `*/30 * * * * /path/venv/bin/python /path/run_once.py >> job.log 2>&1` |
| **systemd timer** | 现代 Linux | `.timer` 单元配 `OnCalendar=*-*-* *:00/30:00` 拉起对应 `.service` |
| **任务计划程序** | Windows | 图形界面或 `schtasks` 命令，触发器选「按计划」 |

三者的共同点是「到点拉起一个进程、跑完即走」，区别在生态：cron 最老最简但没有依赖管理与失败重试；systemd timer 能配依赖、日志走 journald、失败自动重启；任务计划程序是 Windows 上的等价物，图形界面为主。

被调度的脚本要遵守两条工程纪律：**用退出码说话**（0 成功、非 0 失败，调度器和监控系统靠它判断成败），**所有输出带时间戳**（否则日志无法对时）。`chapter-17/run_once.py` 就是这个模式的最小骨架。

反面模式是「脚本自己常驻 + 内部 `while True: sleep(3600)`」：进程挂了没人知道、重启服务器后不会自动拉起、多个实例并发跑会互相踩踏，而这些问题外部调度器早就解决过了。把调度外包出去，脚本只关心「做一次、做对、报结果」。

### 1.6 运维要点（与前几章衔接）

远程任务一旦离开你的视线，所有「本地随手看一眼」的检查都必须变成机制：

- **配置与密钥**：数据库密码、API key 走**环境变量**或密钥管理服务，**勿**写进镜像或公开仓库 —— 第 6 章 `mysql_pages_demo.py` 的 `os.environ` 读法就是模板。
- **可观测性**：结构化日志（带时间戳、任务名、结果计数）、明确的退出码、失败告警。第 6 章的 SMTP 邮件就是现成的通知渠道之一 —— 任务抛异常时给 `main()` 外层包一个 `try / except`，在兜底分支里发一封告警邮件再返回非零退出码，就是最小可用的监控。
- **依赖固化**：每章一个 `requirements.txt`，远程机器上 `pip install -r requirements.txt` 即可复现环境；本章清单见第 4 节。生产环境建议进一步锁定到具体版本（`pip freeze`），避免某天依赖发新版引入行为变化。
- **幂等与断点**：定时任务一定会重复跑、一定会在半路挂掉。入库用业务键做幂等（第 6 章的 `INSERT OR REPLACE` / `ON DUPLICATE KEY UPDATE`），抓取进度落盘，重跑时从断点继续而不是从头再来 —— 远程环境出故障的概率远高于本地，这些设计不是锦上添花而是必需品。

---

## 2. 示例代码：通过 SOCKS（Tor）查看出口 IP

**前置**：这些脚本假设本机已运行 Tor（Tor Browser 保持运行，或独立 `tor` 守护进程已启动）。Python 侧用 **`requests` + SOCKS**（底层依赖 **PySocks**），比书中旧例的 `socket` 全局猴子补丁更安全、易维护 —— 补丁会改全进程的 TCP 行为，副作用难排查；`proxies` 参数则只影响当前请求。

**实测状态说明**：本机**未运行 Tor 服务**，`tor_requests_ip.py` 与 `selenium_tor_chrome.py` **未实测跑通** —— 预期行为是连接 `127.0.0.1:9150/9050` 被拒，脚本按各自兜底逻辑打印提示并返回退出码 1；以下逐层讲清代码逻辑，行为描述均以源码为准。`run_once.py` 为纯本地调度演示，**已实测**。

三个脚本按「requests 直连代理 → 浏览器走代理 → 调度入口」分成两类：前两个演示**同一件事的两种接入姿势**（库级 `proxies` 参数 vs 进程级启动参数），第三个演示远程抓取的另一半 —— **调度**。验证思路统一是访问 `icanhazip.com`：这个服务只回一行纯文本的「来访者出口 IP」，直连时看到的是本机 IP，走通 Tor 后看到的是某个出口节点的 IP，对比即知代理是否生效。

### 2.1 `tor_requests_ip.py`：requests + socks5h 探测两个候选端口

脚本思路：先检查 `requests` 与 `socks`（PySocks）是否可导入，缺哪个就在 stderr 提示对应的 `pip install` 命令并以 1 退出；随后对候选端口元组 `(9150, 9050)` 逐个构造 `http` / `https` 双协议的 `socks5h://127.0.0.1:<port>` 代理字典，请求 `https://icanhazip.com` 并 `raise_for_status()` 校验状态码，成功即打印出口 IP 并返回 0。异常分两类捕获：`OSError` 对应「端口根本连不上」（Tor 没启动），`requests.RequestException` 对应「连上了但请求失败」；两个端口都失败后打印「请先启动 Tor Browser 或 tor 服务」的指引，返回 1。

```python
ports = (9150, 9050)  # Tor Browser 默认 9150；tor 守护进程常见 9050
url = "https://icanhazip.com"
for port in ports:
    proxies = {
        "http": f"socks5h://127.0.0.1:{port}",
        "https": f"socks5h://127.0.0.1:{port}",
    }
    try:
        r = requests.get(url, proxies=proxies, timeout=12)
        r.raise_for_status()
        print(f"SOCKS5 127.0.0.1:{port} ->", r.text.strip())
        return 0
    except OSError as e:
        print(f"端口 {port} 不可用:", e)
    except requests.RequestException as e:
        print(f"端口 {port} 请求失败:", e)
```

```bash
cd chapter-17
pip install -r requirements.txt   # requests + PySocks
python tor_requests_ip.py
```

**未实测**：预期输出形如 `端口 9150 不可用: SOCKSHTTPSConnectionPool(...)` 的连接拒绝错误（被 `OSError` 分支捕获），随后尝试 9050 同样失败，最终打印启动 Tor 的指引并以退出码 1 结束。逐层逻辑已核对源码。

值得注意的设计细节：`socks5h` 方案把「端口探测」做成了**遍历候选端口元组**而不是写死一个端口 —— Tor Browser 与独立 `tor` 守护进程端口不同，脚本不关心你装的是哪种，逐个试即可；命中即 `return 0` 短路返回，不再打扰第二个端口。超时设为 12 秒：Tor 链路本身延迟高，超时太短会把「慢」误判成「不通」。

依赖检查也值得抄：脚本顶部先 `try: import requests`，失败则提示 `pip install requests` 并以退出码 1 结束；`main()` 内再单独试导入 `socks`（PySocks 的导入名是 `socks`，与包名不同，这正是容易踩的坑），缺了提示 `pip install pysocks`。把「环境问题」挡在网络请求之前，报错信息才不会被一长串连接异常淹没。

### 2.2 `selenium_tor_chrome.py`：让 Chrome 浏览器流量走 SOCKS

脚本思路：用 Selenium 4 的 `Options` 给 Chrome 传两个参数 —— `--headless=new` 启用新版无头模式（不弹窗），`--proxy-server=socks5://127.0.0.1:9150` 把浏览器全部流量指到本地 Tor SOCKS（脚本常量注释里提醒：tor 守护进程对应 9050，需与实际端口一致）。`webdriver.Chrome(options=options)` 启动失败（如缺 Chrome/驱动）被 `WebDriverException` 捕获，打印原因返回 1；启动成功后 `driver.get("https://icanhazip.com")`，用 `find_element(By.TAG_NAME, "body")` 取页面正文打印（icanhazip 的正文就是纯文本出口 IP），返回 0；`finally` 保证 `driver.quit()` 一定执行，不留僵尸浏览器进程。

```python
TOR_SOCKS = "socks5://127.0.0.1:9150"  # tor 守护进程常见 9050

options = Options()
options.add_argument("--headless=new")
options.add_argument("--proxy-server=" + TOR_SOCKS)

driver = webdriver.Chrome(options=options)
try:
    driver.get(URL)
    print(driver.find_element(By.TAG_NAME, "body").text.strip())
    return 0
finally:
    driver.quit()
```

```bash
cd chapter-17
pip install -r requirements.txt   # selenium>=4.15.0，另需本机装有 Chrome
python selenium_tor_chrome.py
```

**未实测**：预期在 `driver.get(URL)` 处抛超时/代理不可达异常，被兜底 `except Exception` 捕获，stderr 打印「请求失败（Tor 未启动或代理不可达？）」并返回 1。与 `requests` 版相比，浏览器代理在**进程启动参数**层面生效，覆盖页面内所有子请求（图片、JS、XHR 全部走代理），适合需要渲染 JS 的场景。

与 2.1 的另一个差异是**端口策略**：本脚本只写死 9150（Tor Browser），不像 `tor_requests_ip.py` 那样遍历候选端口。实战照搬时先确认本机 Tor 形态，必要时把常量改成 9050。另外注意 Chrome 的 SOCKS 代理参数**不支持 `socks5h` 写法**，浏览器侧的远程 DNS 由 Chrome 自身机制处理，与 `requests` 的语义略有差别。

错误处理分两层：`webdriver.Chrome(...)` 启动阶段的失败（没装 Chrome、驱动不匹配）走 `WebDriverException` 分支，提示「无法启动 Chrome」；启动成功后的页面加载失败走后面的通用 `except Exception` 分支，提示 Tor 未启动或代理不可达。这种「启动错误」与「运行错误」分开报的做法，能让远程日志一眼定位故障层。

### 2.3 `run_once.py`：供调度器调用的最小单次任务壳

脚本思路：只有 14 行，但把「可调度脚本」的两条纪律都演示了 —— `main()` 打印带 UTC 时间戳的一行日志（`datetime.now(timezone.utc).isoformat()`），然后 `return 0`；模块底部用 `raise SystemExit(main())` 把返回值变成**进程退出码**。真实项目里把 `print` 换成一次完整抓取即可，cron 行照抄第 1.5 节表格。

```python
def main() -> int:
    print("run_once:", datetime.now(timezone.utc).isoformat())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

```bash
cd chapter-17
python run_once.py
```

**已实测**：输出 `run_once: 2026-11-02T06:19:02.546607+00:00`，退出码 0。

把它接到 cron 的完整一行示例（每 30 分钟跑一次，日志追加并带轮转）：

```bash
*/30 * * * * /path/venv/bin/python /path/chapter-17/run_once.py >> /var/log/run_once.log 2>&1
```

cron 环境极简：没有交互终端的 `PATH`、`LANG` 等变量，所以**解释器与脚本都用绝对路径**；脚本内部也不要依赖「当前工作目录」，写文件一律用 `Path(__file__).resolve().parent` 定位（第 6 章的下载脚本就是这么做的）。

---

## 3. 学习贴士

- **先本地后远程**。与第 14–16 章一致，先在可控环境把解析逻辑跑通，再上代理、上远程、上并行。远程机器的排错成本是本地的好几倍，把 bug 留在本地修。
- **代理采购要留痕**。商用代理、Tor、自建出口各有利弊；商用代理务必保留**合同与用途说明**备查，Tor 只作演示与隐私保护用途，自建出口注意机房条款。
- **代理只放在「会话」层，不要全局补丁**。书中旧例用 `socket` 猴子补丁让整个进程走 Tor，一旦忘记还原，后续所有请求（包括不该走代理的）都被改道。`requests` 的 `proxies` 参数或 Selenium 的启动参数，作用域清晰、好测试、好回退。
- **出口 IP 变了不等于「隐身」**。换 IP 解决的是限流误伤，浏览器指纹、行为节奏、登录态照样能把你认出来；把匿名当目标之前，先想清楚自己真正要解决的问题是不是限速与调度。
- **排错路径与成本意识要预先铺好**。本地调试用 `print` + 断点，远程只能靠日志 —— 每个关键分支（重试、回退、降级）都打带上下文的一行日志，出问题时「读日志 → 定位分支 → 复现」三分钟走完，而不是登服务器手动猜。同时记住云主机按小时与流量计费：预算告警、任务的 `timeout` 兜底、最大重试次数，都是远程抓取的必修课。

---

## 4. 与本仓库其他示例

| 文件 | 说明 |
|---|---|
| `chapter-17/tor_requests_ip.py` | `requests` + `socks5h` 依次探测 9150/9050，打印 Tor 出口 IP（需本机运行 Tor，未实测） |
| `chapter-17/selenium_tor_chrome.py` | Chrome `--headless=new` + `--proxy-server` 走 SOCKS 访问 icanhazip（需 Tor 与 Chrome，未实测） |
| `chapter-17/run_once.py` | 可被 cron / systemd / 任务计划程序调用的最小单次任务壳：UTC 时间戳 + 退出码（已实测） |
| `chapter-17/requirements.txt` | 本章依赖：`requests>=2.31.0`、`PySocks>=1.7.1`、`selenium>=4.15.0`；注释内注明未启动 Tor 时连接被拒属预期 |

与前面章节的衔接：调度入口的形态复用第 6 章「脚本用退出码与 stderr 汇报」的约定；代理替换的只是第 1–3 章 `requests.get` 的出口，解析代码（第 2–5 章）一行不用改；远程入库则直接拼接第 6 章的 `mysql_pages_demo.py` 模式 —— 环境变量读凭据、参数化插入。

把三个脚本串起来就是一个最小远程抓取闭环：`run_once.py` 的壳负责「被调度」，`tor_requests_ip.py` 的代理接法负责「换出口」，第 6 章的落库代码负责「存结果」。本章没有引入任何新的解析技术 —— 这也印证了导语那句话：远程抓取的难点从来不在「抓」，而在部署、调度与合规边界的把控。

---

## 练习建议

1. 给 `tor_requests_ip.py` 增加第三个候选端口（如自定义的 1080），并把端口列表改成从环境变量 `TOR_PORTS` 读取，练习「配置不进代码」。
2. 写一条真实可用的 **cron** 配置：每分钟跑一次 `run_once.py`，stdout 与 stderr 都追加到 `run_once.log`，跑几分钟后检查日志时间戳是否连续。
3. 用 **Dockerfile** 把爬虫与 `cron` 打进同一镜像（草图即可）：基础镜像装好依赖，`CMD` 启动 cron 前台进程。
4. 为云主机编写 **systemd unit**：`ExecStart=/path/venv/bin/python job.py`，配 `Restart=on-failure` 与对应 `.timer` 单元。
5. 记录一次「代理失败 → 直连回退」的策略伪代码：哪些错误允许回退、回退前等多久、直连要不要限速，并逐条标注合规前提。
6. 对比实验：分别用 `socks5://` 与 `socks5h://` 连一个本地 SOCKS 代理，用抓包工具观察 DNS 查询是否从本机发出，验证第 1.2 节的结论。
