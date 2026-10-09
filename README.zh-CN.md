# EPANET-Agentic 中文运行与改造说明

> 这份文档**不是** [README.md](README.md) 的翻译。上游 README 描述的是论文里的系统设计；这份文档记录的是**我们把这个项目真正跑起来时踩到的坑、做过的改造、以及当前模型接口与论文写作时的差异**。
>
> 架构、功能、引用请看上级的 [README.md](README.md)。给 AI 编码助手看的工程约定见 [AGENTS.md](AGENTS.md)。

---

## 一、与原 README 的差异一览

| 原 README 的说法 | 实际情况（本文档核实过） |
|---|---|
| `Python ≥ 3.10` | 需 **3.10–3.12**。3.14 装不上：`wntr` 无对应 wheel，会退回源码编译 |
| `pip install -r requirements.txt` 即可 | 原 `requirements.txt` 装完**跑不起来**，缺 `openai` 与 `setuptools<81`。现已补齐（见下） |
| `Set your key before running (choose one of the following):` | 原文这句话后面是**空的**，没有任何配置说明。现在：`.env` 文件，见第三节 |
| 模型为 `deepseek-chat` / `deepseek-reasoner` / `qwen-vl-max` | 两个旧名**实测仍可调用**，但已指向**同一个**模型 `deepseek-flash` 的两种思考档位，见第五节 |
| —— | 中文 Windows 控制台不设 `PYTHONIOENCODING=utf-8` 会在任务中途崩溃 |
| —— | 每次运行会往仓库里写 `temp.*` 和 pickle 产物，已用 `.gitignore` 收住 |

---

## 二、环境准备

```powershell
cd code\EPANET-Agentic
& "<你的 Python 3.12>\python.exe" -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`requirements.txt` 里三行是**改造新增**的，缺任何一条都会让干净安装直接失败：

- `autogen-ext[openai]` + `openai==3.26.1` —— `llm.py` 用的 `autogen_ext.models.openai` 属于 autogen-ext 的可选 extra，漏装报 `ModuleNotFoundError: No module named 'openai'`
- `setuptools<81` —— `wntr/epanet/toolkit.py` 要 `import pkg_resources`，而 setuptools 81+ 已移除，缺它报 `No module named 'pkg_resources'`
- `python-dotenv==1.2.4` —— 供下节的 `.env` 机制使用

装 `import wntr` 时会打印一条 `pkg_resources is deprecated` 的 UserWarning，属预期，可忽略。

装完可以做一次**不需要 API key** 的自检（读最小管网 + 完整水力模拟 + 调工具函数）。注意这一步也要先设编码，否则会在打印 `✅` 时崩：

```powershell
$env:PYTHONIOENCODING = "utf-8"
python -c "import wntr, tools; wn=wntr.network.WaterNetworkModel('code_dir/data/net3.inp'); print(len(wn.junction_name_list), len(wn.pipe_name_list)); print(tools.is_runnable_inp('data/net3.inp').splitlines()[0])"
```

预期输出 `92 117` 和一行 `✅ INP file is valid...`。这一步通不过就跟密钥无关，是环境问题。它会顺手在仓库根留下 `temp.inp/bin/rpt`（已被忽略，见第六节）。

---

## 三、密钥配置（`.env`）

仓库根目录放一个 `.env`（已被 git 忽略）：

```
DEEPSEEK_API_KEY=sk-...      # Orchestrator / TaskExecutor / CodeRunner
QWEN_API_KEY=sk-...          # DataAnalyzer 看图与结果文本
```

`llm.py` 会按**文件自身位置**定位 `.env`，因此不依赖你在哪个目录启动。没有该文件、或值还是 `REPLACE_ME` 时，程序在 `import llm` 阶段就抛出点名具体变量名的错误（英文），而不是跑到一半才收到 401。

**为什么不用上游的 `OPENAI_API_KEY`**：上游让两个 DeepSeek client 和 Qwen 抢这一个变量，一旦两家都要配置就配不出来；更糟的是若该值为空，OpenAI SDK 会回退去读环境里**真实存在的** `OPENAI_API_KEY`，然后把它发往 `api.deepseek.com`，得到一个看似供应商故障、实为配置错误的 401。

---

## 四、运行

在**仓库根目录**、并先设好编码：

```powershell
$env:PYTHONIOENCODING = "utf-8"
python main.py
```

- **`PYTHONIOENCODING` 不是可选项**：`tools.py` 的返回值含 `✅`/`❌`，agent 团队会把工具结果打印出来；GBK 代码页下这会在任务执行中途抛 `UnicodeEncodeError: 'gbk' codec can't encode character '\u2705'` 并终止整个流程。
- **必须在仓库根运行**：`main.py` 打开 `tasks/manuscript.json`，`tools.py` 一律拼 `'code_dir/' + 文件名`，代码执行器的工作目录是 `code_dir`。
- **`main.py` 默认任务写死在 `tasks[8]`**，即 `System operation-03`，作用在 `L-TOWN.inp`（782 节点、约 7 天模拟）上 —— 又慢又费 token。首次运行建议改 `main.py` 里的小任务索引，拿 `net3`（92 节点）冒烟。
- 系统带**人工确认环节**（`UserProxyAgent`）：每完成一步会停下等你输入，不会自动跑完整条计划。

---

## 五、模型现状：论文用的那套分工现在是什么样

DeepSeek 官方更新日志原文：

> 旧有的 API 接口的两个模型名 `deepseek-chat` 与 `deepseek-reasoner` 将于三个月后（2026-07-24）停止使用。当前阶段内，这两个模型名分别指向 `deepseek-v4-flash` 的非思考模式与思考模式。

也就是说，论文里"V3 负责规划与工具调用、R1 负责写代码"的双模型分工，**实质是同一个模型（V4.1 Flash）的两个思考档位**。实测印证：两个旧名仍可用，且自报的 `model` 字段都是 `deepseek-flash`；`deepseek-v4-pro` 则是**真独立**的模型（自报 `deepseek-v4-pro`）。

### 实测结果（真实调用，非文档推断）

| 配置 | 多轮工具调用结果 |
|---|---|
| 旧别名 `deepseek-chat`（非思考） | ✅ 成功，走完 tool call → 执行 → 反思 → 最终答案 |
| 旧别名 `deepseek-reasoner`（思考） | ✅ 成功 |
| **`deepseek-flash`，思考默认开** | ❌ **400**：`The `reasoning_content` in the thinking mode must be passed back to the API.` |
| **`deepseek-flash` + 注入 `thinking=disabled`** | ✅ 成功 |

两个重要结论：

1. **现在的 `llm.py` 不需要改名就能跑** —— 旧别名仍有效且思考区别仍在，论文的行为层可复现叙述还没塌。代价是 autogen 会提醒一句 `Resolved model mismatch: deepseek-chat != deepseek-flash`（只影响 token/费用估算，不致错）。
2. **千万不要"顺手把模型名改成 `deepseek-flash`"** —— 思考模式默认开启且强度为 high（官方 Thinking Mode 文档），而 autogen 出站消息不带 `reasoning_content` 字段（它把 `thought` 映射进了 `content`），于是迁移本身会直接打断两个带工具的 agent。真需要迁到现役名时，**必须同时关掉思考**。

### 而"关掉思考"在 autogen 0.6.1 上没有干净通道

- 构造函数传 `extra_body` → 被参数白名单过滤掉，**静默丢弃且不报错**（实测 `_create_args` 里只剩 `model/seed/temperature`）
- 调用级 `extra_create_args={"extra_body": ...}` → 直接 `ValueError: Extra create args are invalid: {'extra_body'}`
- `reasoning_effort` 可以透传，但它的档位表（minimal/low/medium/high/xhigh/max/ultra）**没有"关闭"这一档**
- 目前**唯一实测有效**的方式：写私有属性 `client._create_args["extra_body"] = {"thinking": {"type": "disabled"}}`（已验证真的能抵达 SDK 调用）。代价是依赖 autogen 内部实现，升级可能失效；若要长期依赖，应改写成自定义 `http_client` 传输层在请求体里注入

另外两点与模型能力有关的事实：`deepseek-flash` 原生支持图像理解（`deepseek-v4-pro` 不支持），所以 `llm.py` 里 `model_info["vision"]` 应当**跟随模型名一起改**，不能写死；思考模式下 `temperature`/`presence_penalty`/`frequency_penalty` 会被接受但**不生效**，即原代码靠 `temperature=0` 追求可复现的思路在新模型上不再成立。

---

## 六、运行产物与版本控制

| 产物 | 来源 | 处理 |
|---|---|---|
| `temp.inp` / `temp.bin` / `temp.rpt` | `is_runnable_inp()` 调 `run_sim()` **没传前缀**，落在当前目录 | 已 gitignore |
| `code_dir/control_wn.pickle` | `add_multiple_controls()` 的**固定文件名** | 已 gitignore |
| `code_dir/<你传入的 save_name>.pickle` | `apply_disaster_scenario()` | 已 gitignore |
| `code_dir/*.png` 等 | CodeRunner 生成的图表与数据 | 已 gitignore |
| `conversation/**` | 论文的实验记录（含图、文本、markdown） | **保持跟踪**，不要批量忽略 |

两个固定文件名会**静默覆盖**：不要假设仓库里现存的那个 pickle 还对应你上一次的情景。

---

## 七、分支与上游同步

- `master`：跟随上游 `wangjian169/EPANET-Agentic`，不直接提交改造。
- `dev`：所有改造提交在这里。
- 远程：`origin` = 我们的 fork（可推送）；`upstream` = 原作者仓库，**push URL 已置为不可推送**，只用于取。

同步上游：

```powershell
git fetch upstream
git checkout dev
git merge upstream/master
```

若上游再次改动 `.idea/`（原作者把它提交过），这里会冲突，按"不再跟踪"这一侧解决：`git rm -r .idea`。

本仓库的 `.gitignore` 覆盖 venv、Python 缓存、IDE/OS 垃圾、上述运行产物，以及 `.env`（保留 `.env.example` 作为模板）。`.idea/` 已从版本控制中移除，磁盘文件保留。

---

## 八、常见问题

| 现象 | 原因与处理 |
|---|---|
| `ModuleNotFoundError: No module named 'pkg_resources'` | `setuptools>=81`，降到 `<81`（已 pin） |
| `ModuleNotFoundError: No module named 'openai'` | 装 `autogen-ext[openai]`（已 pin） |
| `UnicodeEncodeError: 'gbk' codec ... '\u2705'` | 没有设 `PYTHONIOENCODING=utf-8` |
| `RuntimeError: No .env found next to llm.py` | 没建 `.env`，或不在仓库根目录运行 |
| `... variable 'DEEPSEEK_API_KEY' is still the placeholder value` | `.env` 里还没替换 `REPLACE_ME` |
| 报"文件找不到"但路径看着没错 | cwd 不对，所有相对路径都以**仓库根**为基准 |
| Python 3.14 下 `wntr` 安装失败 | 换 3.10–3.12，无 wheel 可用 |

---

## 九、引用

本仓库的改造部分（依赖修复、`.env` 机制、`.gitignore`/分支约定、这份文档）不改变系统的学术归属，使用时请仍引用原论文：

> Wang, J., Fu, G., & Savic, D. (2026). *EPANET-Agentic: A Multi-Agent System for Natural Language-Controlled Simulations of Water Distribution Networks*. **Water Research**, 125433. https://doi.org/10.1016/j.watres.2026.125433

BibTeX 见上级 [README.md](README.md)。
