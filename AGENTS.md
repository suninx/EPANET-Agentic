# AGENTS.md

Working notes for anyone (human or agent) changing this codebase. Every statement
below was verified against this checkout; anything unverified is marked as such.

## What this project is

EPANET-Agentic: an Autogen multi-agent system that turns natural-language requests
into WNTR/EPANET simulations of water distribution networks. Orchestrator (DeepSeek-V3)
routes work into three function-wrapped sub-agents: TaskExecutor (DeepSeek-V3 + wntr
tools), CodeRunner (DeepSeek-R1 writes code, `CodeExecutorAgent` executes it locally),
DataAnalyzer (Qwen-VL reads plots and result files).

Only three agents call an LLM. `CodeExecutorAgent` and `UserProxyAgent` do not — the
first runs Python locally, the second waits for keyboard input.

For setup steps written for humans (with the error messages you will actually see),
see [README.zh-CN.md](README.zh-CN.md); this file is the terse, verified contract for
whoever is editing the code.

## Entry points

- `main.py` — reads `tasks/manuscript.json`, **hard-coded index `tasks[8]`**
  (= `System operation-03`, which runs on `L-TOWN.inp`, 782 nodes / ~7 days simulated).
- `tools.py` — the three tools exposed to TaskExecutor.
- `llm.py` — the three model clients and the `.env` loading (see Secrets below).
- `prompts.py` — system prompts for orchestrator / task executor / coder.

## Environment

- **Use Python 3.10–3.12.** 3.14 does not work: `wntr` ships no wheel for it and
  installation falls back to compiling from source. Verified on 3.12.13.
- `pip install -r requirements.txt` is sufficient as of this checkout. Two gaps that
  used to make a fresh install fail out of the box are now pinned in requirements:
  `autogen-ext[openai]` (`autogen_ext.models.openai` fails with `ModuleNotFoundError:
  No module named 'openai'` without the extra) and `setuptools<81` (`wntr/epanet/toolkit.py`
  imports `pkg_resources`, which setuptools 81+ no longer ships).
- A `UserWarning: pkg_resources is deprecated` on `import wntr` is expected and harmless.

## Secrets

Keys come from a `.env` file **next to `llm.py`**, loaded by `python-dotenv` with an
explicit path so the lookup is independent of the current working directory.

```
DEEPSEEK_API_KEY=...    # Orchestrator, TaskExecutor, CodeRunner
QWEN_API_KEY=...        # DataAnalyzer (qwen-vl-max, served by DashScope)
```

- Copy `.env.example` to `.env`. `.env` is git-ignored — this repository is public,
  never commit a real key, and note that a key pushed once stays in git history.
- `llm.py` deliberately resolves keys itself and raises a readable error instead of
  passing `None`. If it passed `None`, the OpenAI SDK would fall back to any ambient
  `OPENAI_API_KEY` and send it to `base_url=api.deepseek.com`, producing a 401 that
  looks like the provider broke.
- The upstream code used one `OPENAI_API_KEY` variable for both providers. That cannot
  work once both are configured, since two vendors cannot share a single variable.

## Running

Run **from the repository root**:

```powershell
$env:PYTHONIOENCODING = "utf-8"   # required on Chinese Windows consoles, see below
.\.venv\Scripts\Activate.ps1
python main.py
```

- Paths are cwd-dependent: `main.py` opens `tasks/manuscript.json`, every function in
  `tools.py` prefixes `'code_dir/' + inp_file`, and `LocalCommandLineCodeExecutor`
  uses `work_dir="code_dir"`.
- `PYTHONIOENCODING=utf-8` is **not cosmetic**. `tools.py` returns strings containing
  `✅` / `❌`, and `Console(stream)` prints tool results. On a GBK codepage that raises
  `UnicodeEncodeError: 'gbk' codec can't encode character '\u2705'` in the middle of a
  task and kills the run.
- `main.py` runs `UserProxyAgent`, so it is interactive: it stops after each planned
  step and waits for you to approve the next one (human-in-the-loop by design).
- For a first smoke test, prefer a small network over the default L-TOWN task. To
  check credentials alone without running any agent team:

```powershell
python -c "from llm import deepseekV3; import asyncio; print(asyncio.run(deepseekV3.create(create_args=[{'role':'user','content':'reply OK'}])).content)"
```

## Generated artifacts

- `tools.is_runnable_inp()` calls `run_sim()` **without a file prefix**, so `temp.inp`,
  `temp.bin`, `temp.rpt` appear in the working directory on every validation.
- `add_multiple_controls()` always writes `code_dir/control_wn.pickle`; `apply_disaster_scenario()`
  writes to the `save_name` you pass. These names are fixed and **overwrite silently**
  between runs — do not assume an old pickle still describes the current scenario.
- CodeRunner saves plots and data into `code_dir/`; `DataAnalyzer` re-opens them with
  `'code_dir/' + path`. `conversation/` holds the paper's committed run records and is
  tracked; `code_dir/` scratch output is git-ignored.

## Known code-level caveats

- `deepseek-chat` and `deepseek-reasoner` are declared `"vision": False` (corrected from
  `True`; text-only models). A `True` claim disables Autogen's image-stripping guard and
  lets images reach an API that rejects them.
- `deepseekR1` declares `"function_calling": True`. That was false for the original R1 model,
  but is now true by accident: the alias is served by V4.1 Flash, and a real multi-turn
  `AssistantAgent(tools=...)` run against `deepseek-reasoner` completed successfully. The
  `coder` agent still passes no tools, so nothing changes today.
- DeepSeek's model table now lists `deepseek-flash` and `deepseek-v4-pro`. Measured with a real
  key: `deepseek-chat` and `deepseek-reasoner` still respond, and both report
  `model="deepseek-flash"` - one serving model in two thinking modes, not two models.
  `deepseek-v4-pro` is genuinely separate. **Do not switch `llm.py` to `deepseek-flash`**
  without also disabling thinking: thinking is on by default (effort high), Autogen never
  sends `reasoning_content` back, and DeepSeek rejects the multi-turn tool loop with
  `400 The reasoning_content in the thinking mode must be passed back to the API`. Injecting
  `thinking=disabled` makes flash work; the two legacy aliases work as-is.
- `extra_body` cannot reach the SDK through any Autogen 0.6.1 public surface: the constructor
  drops it silently (filtered by the `create_kwargs` whitelist, no error raised) and
  `extra_create_args` rejects it outright (`ValueError: Extra create args are invalid:
  {'extra_body'}`). `reasoning_effort` does pass through but has no "off" level. The only
  measured working injection is `client._create_args["extra_body"] = {"thinking": ...}` -
  a private attribute, so treat it as fragile across autogen-ext upgrades.
- Whether the `deepseek-chat` / `deepseek-reasoner` aliases accept image input is **unverified**,
  even though the model actually serving them (V4.1 Flash) is multimodal. Keep `vision: False`
  for these two clients until measured.
- `seed=42` / `temperature=0` on all three clients is a reproducibility choice, not
  differentiation; outputs still vary somewhat between runs.
