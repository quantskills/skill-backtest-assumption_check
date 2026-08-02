# skill-backtest-assumption-audit

[简体中文](./README.md) | [English](./README.en.md)

**An independent backtest assumption auditor**: audits the trading assumptions and biases behind backtest code / strategy code / research backtest reports across nine axes, producing a defect list of `finding × evidence × severity × impact × fix`.

`role: skill` `output: AuditReport` `paradigm: cross-sectional backtest` `license: GPL-3.0`

---

`skill-backtest-assumption-audit` is a backtest assumption audit skill from PandaAI Quant Skills (the QUANTSKILLS org, category 07 — Research Validation & Quality). Given a piece of backtest code, strategy code, or a research backtest report, it gathers evidence independently and issues per-item verdicts — **not a backtest engine, but a backtest assumption auditor**.

It breaks down "can I trust this backtest result?" into nine checkable axes and ships runnable detectors under `scripts/` for data-level verification (lookahead replay, price-limit reachability, survivorship reconstruction, turnover & capacity, implied costs).

## 🎯 What problem does this solve

A pretty equity curve does not mean the conclusion is trustworthy. Common systematic biases:

- **close→close lookahead**: signal and execution share the same timestamp; IC is systematically inflated
- **Zero cost**: high-turnover strategies report inflated net returns
- **Positions you cannot buy**: one-word limit-up boards are still "filled"
- **Survivorship bias**: current constituents back-filled into history hides delisting losses
- **Multiple testing**: after scanning hundreds of parameter sets, only luck survives
- **Capacity illusion**: basket notional far exceeds traded volume — impossible to fill live

This skill enforces **nine audit axes**, and every defect must carry evidence and a severity grade.

## Nine audit axes

| # | Axis | Data-level detector |
|---|---|---|
| 1 | Execution timing & lookahead | `execution_timing` |
| 2 | Trading costs | `cost_model` |
| 3 | Price limits & suspensions | `price_limits` + `suspensions` |
| 4 | Survivorship bias | `survivorship` |
| 5 | Parameter freedom & multiple testing | `parameter_freedom` |
| 6 | Data alignment & adjustment | `data_alignment` |
| 7 | Turnover & capacity | `turnover_capacity` |
| 8 | Benchmark & excess returns | — (static) |
| 9 | Reporting transparency | — (static) |

Each axis yields a **PASS / WARN / FAIL / INFO** verdict plus a severity grade (🔴 BLOCKER / 🟠 MAJOR / 🟡 MINOR / 🔵 INFO), impact, and fix. Full criteria: `references/audit-axes.md`.

## ⚡ Audit workflow (standard 7 steps)

```
1. Clarify the audit target & inputs (code / report / signal+panel)
2. Static evidence: scan the nine axes using the patterns in evidence-collection.md
3. Data verification: run scripts/ when signal + panel are available
4. Apply the severity model; write finding × evidence × severity × impact × fix
5. Aggregate per-axis verdicts and an overall confidence
6. Emit a structured audit report (Markdown)
7. Give re-audit advice: what to re-run after fixes
```

## 🚀 Quick start

```bash
# Install (platforms with a skills directory: Claude Code / OpenClaw / Codex)
cp -r skill-backtest-assumption-audit ~/.claude/skills/skill-backtest-assumption-audit

# Data-level verification (optional; needs pandas + numpy)
python -m pip install -r scripts/requirements.txt
python scripts/audit_cli.py --signal signal.csv --panel panel.csv --weights weights.csv \
    --membership members.csv --assumptions assumptions.json --out out/
```

```text
Trigger prompt 1: Audit this backtest code's assumptions — it executes at the same-day close.
Trigger prompt 2: Is the Sharpe in this report trustworthy? Check for lookahead, zero cost, survivorship.
Trigger prompt 3: Run a full backtest assumption audit on this strategy and give me a defect list.
```

## 🗃️ Inputs

- **signal** (optional): `[date × symbol]` float signal, wide or long format
- **panel** (optional): long `date, symbol, open, high, low, close, volume`; `amount`, `suspended`, `raw_close` recommended
- **weights** (optional): position weight series
- **membership** (optional): true historical constituents incl. delisted names (axis 4)
- **assumptions.json** (optional): cost / execution mode / trial count etc. (keys in `scripts/audit_cli.py`)

Missing inputs never lead to guessing: the affected axis degrades to **INFO (insufficient evidence → suggest materials)**.

## 📦 Layout

```text
skill-backtest-assumption-audit/
├── SKILL.md                        # Core protocol (9 axes + 7-step workflow + severity model)
├── references/                     # audit-axes / evidence / severity / fixes / report / source_boundary
├── scripts/
│   ├── audit_cli.py                # Audit CLI entry
│   ├── self_test.py                # Synthetic self-check with planted bugs
│   ├── report.py                   # Markdown / JSON report rendering
│   ├── detectors/                  # Nine axis detectors
│   └── requirements.txt
└── agents/                         # openai.yaml / cursor-rule.mdc / portable-loader
```

## Relationship to existing skills (complementary)

| Existing skill | Its boundary | What this adds |
|---|---|---|
| `skill-backtest` (05 protocol) | Defines the "correct backtest" protocol | Audits whether a backtest conforms |
| `skill-backtest-overfit` (05) | Only selection bias / multiple testing | Full spectrum; deep-dives that axis |
| `skill-numerical-leak-check` (07) | Only future leakage, in depth | Lookahead is one of nine axes; recommend deep-diving |
| `skill-pandaai-workflow-audit` (05) | Only PandaAI workflow JSON | Audits generic backtest code / reports |

## 📐 Core constraints

| Constraint | Note |
|---|---|
| 🔍 Evidence first | Every defect needs evidence (code line / detector output); no evidence, no verdict |
| 🌐 Independent audit | Does not rewrite code or endorse conclusions — only flags assumptions & biases |
| 🚫 Facts, not advice | Outputs research structure and factual findings; no investment advice |
| 📉 Graded severity | BLOCKER / MAJOR / MINOR / INFO, never a flat "major" label |

## ⚠️ Disclaimer

Research/education only. This repository ships no market data; signals and panels are user-provided, and the user is responsible for data legality and licensing. It does not validate any return claims and does not constitute investment advice. Audit conclusions reflect only checks over the given materials + historical data and do not represent future performance.

## 📜 License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).

## 🐼 PandaAI / QUANTSKILLS Community

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI community QR code" width="220">
  <br>
  <sub>Scan to join the PandaAI community for QUANTSKILLS skills, agent workflows, and quant research.</sub>
</div>
