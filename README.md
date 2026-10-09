# 💧 EPANET-Agentic: A Multi-Agent System for Natural Language-Controlled Simulations of Water Distribution Networks

EPANET-Agentic is a multi-agent system that uses Large Language Models to automate simulation, control, and analysis tasks for water distribution networks.
It transforms natural language instructions into executable workflows, from `.inp` file validation and disaster scenario simulation to control logic generation, result visualization, and analysis.

> 🇬🇧 **Note** — [README.zh-CN.md](README.zh-CN.md) documents this fork's *measured* install and run steps, the `.env` key setup, the Windows console encoding requirement, and how the model API has changed since the paper was written (measured: `deepseek-chat` and `deepseek-reasoner` still respond, but both are now served by the *same* model — `deepseek-flash` — in two thinking modes). It is **not** a translation of this README.
>
> 🇨🇳 **说明** — [README.zh-CN.md](README.zh-CN.md) 记录本仓库实测过的安装/运行步骤、`.env` 密钥配置、Windows 控制台编码要求，以及上游模型接口相对论文写作时已发生的变化（实测：`deepseek-chat` / `deepseek-reasoner` 仍可调用，但两者现已由**同一个**模型 `deepseek-flash` 以两种思考档位提供服务）。这不是本 README 的翻译。
>
> Engineering conventions for contributors and coding agents · 面向贡献者与编码助手的工程约定：[AGENTS.md](AGENTS.md)

---

## 🚀 Key Features

- **Orchestrator**: The Orchestrator interprets natural-language instructions and coordinates specialized agents to complete multi-step tasks.
- **TaskExecutor**: Validates `.inp` network files, adds time- or condition-based control logic, and simulates disaster scenarios (earthquakes, leaks, power outages, fires, contamination, chemical injections).
- **CodeRunner**: Writes and executes Python code to modify models, run simulations, plot results, and save outputs.
- **DataAnalyzer**: Reads images or text results to summarize findings, compare plots, and extract insights.
- **Stack**: Built with Autogen, WNTR, and related Python tools for multi-agent, multimodal, asynchronous workflows.

---

## ⚙️ Requirements

- Python ≥ 3.10. Install dependencies:

```bash
pip install -r requirements.txt
```

## 🔑 API Key (Required)

This project requires an API key for the LLMs. DeepSeek and Qwen are used via OpenAI-compatible endpoints.

Set your key before running (choose one of the following):

> **Note**: Different models (e.g., `deepseek-chat`, `deepseek-reasoner`, `qwen-vl-max`) or different model versions can change behavior (tool-calling decisions, code quality/formatting, multimodal parsing, reasoning style). Re-test critical workflows when switching models or versions.

---

## ▶️ Quick Start

1. Place a valid EPANET `.inp` file under `code_dir/`.
2. Optionally edit a task in `tasks/manuscript.json`.
3. Run:

```bash
python main.py
```
---

## 📁 Project Structure

```
├─ main.py              # Entry point, orchestrates all agents
├─ llm.py               # LLM clients (DeepSeek, Qwen)
├─ tools.py             # INP checks, control rules, disaster scenarios
├─ prompts.py           # System prompts for agents
├─ requirements.txt     # Dependencies
└─ tasks/               # Example task descriptions (JSON)
```

---

## ⚠️ Notes & Recommendations

- The `.inp` file must have valid IDs and time settings, or the simulation will fail.
- Results may vary slightly due to LLM stochasticity and model/version differences.
- For production, pin the LLM model/version and run regression tests.

---


## 📚 Reference / Citation

If you use EPANET-Agentic in academic work, please cite:

Wang, J., Fu, G., & Savic, D. (2026). *EPANET-Agentic: A Multi-Agent System for Natural Language-Controlled Simulations of Water Distribution Networks*. **Water Research**, 125433. https://doi.org/10.1016/j.watres.2026.125433

### BibTeX

```bibtex
@article{Wang2026EPANETAgentic,
  title   = {EPANET-Agentic: A Multi-Agent System for Natural Language-Controlled Simulations of Water Distribution Networks},
  author  = {Jian Wang, Guangtao Fu, Dragan Savic},
  journal = {Water Research},
  year    = {2026},
  pages   = {125433},
  issn    = {0043-1354},
  doi     = {10.1016/j.watres.2026.125433},
  url     = {https://doi.org/10.1016/j.watres.2026.125433}
}
