# 💧 EPANET-Agentic: A Multi-Agent System for Natural Language-Controlled Simulations of Water Distribution Networks

EPANET-Agentic is a multi-agent system that uses Large Language Models to automate simulation, control, and analysis tasks for water distribution networks.
It transforms natural language instructions into executable workflows, from `.inp` file validation and disaster scenario simulation to control logic generation, result visualization, and analysis.

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

## 📜 License

For research and academic use. You may use and modify the code for non-commercial purposes.
