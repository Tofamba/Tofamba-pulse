# Tofamba Pulse

**The supervision layer for autonomous agents.**

When your agents loop, overspend, or get stuck — Pulse pings your WhatsApp and nothing continues without your say-so.

---

```python
from pulse import supervise

with supervise("reconciliation-bot") as session:
    result = run_bank_reconciliation(ledger)   # your agent logic here
    
    if result.needs_human_input:
        answer = session.ask(
            "Found a $5,000 discrepancy on Invoice #502. Suspected cause: currency conversion.",
            options=["Use 1.2 rate", "Flag for manual review", "Skip and continue"]
        )
        result.apply(answer)
```

Your WhatsApp receives:
> 🤔 **reconciliation-bot** needs your input
> Found a $5,000 discrepancy on Invoice #502. Suspected cause: currency conversion.
> A) Use 1.2 rate  B) Flag for manual review  C) Skip and continue

You reply **A**. The agent continues.

---

## Why Pulse

Monitoring tools are for servers. **Pulse is for digital workers.**

You wouldn't leave a junior clerk alone with the company checkbook. Why leave an AI agent alone with your API keys, your data, and your money?

| Without Pulse | With Pulse |
|---|---|
| Agent loops for 3 hours, burns $800 in tokens | Cost circuit breaker fires at $50, you approve or kill |
| Agent hallucinated a bank entry at 2am | You got a WhatsApp at 2am and said no |
| "The system did something" | Immutable audit trail: who told it what, when, at what cost |
| Agent fails silently | You know within 30 seconds |

---

## Features

### 🔍 Agent Supervision
Wrap any agent loop — LangChain, CrewAI, AutoGen, raw OpenAI — with one context manager. Pulse watches for stalls, loops, errors, and cost spikes.

### 💬 Bi-Directional WhatsApp / Telegram
When your agent needs a human decision, Pulse pauses execution and sends you a message. Your reply resumes the agent with the context it needs.

### 💰 Cost Circuit Breaker
Set a token spend threshold. When an agent approaches it, Pulse asks for approval before it continues. No more $2,000 overnight surprises.

### 📋 Audit Trail of Intent
Not just what the agent did — but who told it to do it. Every human decision is logged immutably with timestamp, actor, and the exact context that was presented.

### 🌑 Shadow Mode
Run Pulse in observation-only mode for 30 days. See what it would have flagged — zero production impact, full governance report at the end.

---

## Installation

```bash
pip install tofamba-pulse
```

Set your credentials:

```bash
export PULSE_API_KEY=your_key_here
```

---

## Quick Start

### Basic supervision

```python
from pulse import supervise

with supervise("my-agent") as session:
    # your agent runs here
    # if it stalls or errors, Pulse notifies you automatically
    result = my_agent.run(task)
```

### Ask for human input mid-task

```python
with supervise("data-entry-bot") as session:
    for record in records:
        if record.ambiguous:
            decision = session.ask(
                f"Record #{record.id} is ambiguous: {record.description}",
                options=["Accept", "Reject", "Flag for review"]
            )
            record.apply(decision)
```

### Cost circuit breaker

```python
with supervise("research-agent", cost_limit_usd=25.0) as session:
    # agent will pause and ask for approval if spend approaches $25
    result = agent.deep_research(topic)
```

### Loop detection

```python
with supervise("scraping-bot", max_retries=5) as session:
    # if the agent retries the same action 5 times, Pulse fires
    data = scraper.run(url)
```

---

## How It Works

```
Your Agent                    Pulse SDK               Tofamba Orchestrator
─────────────────────────────────────────────────────────────────────────
run_task()           ──▶   supervise() wraps it   ──▶  monitors heartbeat
                                                         every 5s
agent stalls         ──▶   detects no progress    ──▶  AI diagnoses cause
                                                         in plain English
                           session.ask() called   ──▶  WhatsApp message sent
                                                         to you
you reply "A"        ◀──   answer delivered        ◀──  your response routed back
agent continues      ──▶   with your context       ──▶  logged immutably
```

Every step is logged to an append-only audit ledger. Every human decision is attributed. The SHA-256 hash of the full session is included in the Governance Report.

---

## The Governance Report

At the end of a Shadow Mode evaluation — or on demand — Pulse generates a **Certified Agent Supervision Report**:

- Sessions observed
- Interventions suppressed (Shadow Mode) or actioned (Live)
- Cost circuit breaker events
- Human decisions made and their outcomes
- SHA-256 integrity hash of the complete audit ledger

> *"I spent 30 years as a bookkeeper. I know you don't leave a junior clerk alone with the checkbook. Why are you leaving an AI agent alone with your API keys? Pulse is the Supervisory Ledger for your AI agents."*
> — Lenard Francis, Founder, Tofamba

---



---

## 🚀 The 7-Day Shadow Challenge

Worried about your AI agents going rogue but not ready to add supervision yet?

**Step 1** — Install Pulse:
```bash
pip install tofamba-pulse
```

**Step 2** — Add one decorator to your agent function:
```python
from pulse.decorators import shadow_supervise

@shadow_supervise("my-agent", cost_limit=10.0)
def run_my_agent(data):
    # your existing agent logic — unchanged
    ...
```

**Step 3** — Run normally for 7 days. Zero production impact. No WhatsApp alerts. No pauses.

**Step 4** — At the end of the week, get your **Certified Governance Report** showing:
- Every point where your agent hit an uncertainty boundary
- Every loop or retry that Pulse would have caught
- Every cost spike that would have triggered a circuit breaker
- The SHA-256 integrity hash of the complete observation ledger

> *"I'm not asking you to trust my AI. I'm asking you to let my Audit Ledger observe your AI for a week. The data will speak for itself."*

**[Start your Shadow Challenge →](mailto:tofambatech@outlook.com)**

---
## Pricing

| Plan | Price | Agents | Sessions/mo |
|---|---|---|---|
| **Shadow Mode** | Free | 1 | 30-day evaluation |
| **Starter** | $19/mo | 1 | 50 sessions |
| **Growth** | $99/mo | 3 | 200 sessions + cost tracking |
| **Team** | $299/mo | 10 | 1,000 sessions + Diagnostic Council |
| **Compliance** | $799/mo | Unlimited | Unlimited + audit export |

All plans include WhatsApp or Telegram notifications and the immutable audit trail.

---

## Built in Zimbabwe. Built for the world.

In Africa, WhatsApp is the operational control plane — not a Slack integration or a dashboard you open on a laptop. Pulse was built for operators who need to supervise agents from a phone, in any timezone, without opening a terminal.

The same governance discipline works everywhere.

---

## Powered by Tofamba

Pulse shares infrastructure with **[AlertEngine](https://github.com/Tofamba/fastapi-alertengine)** — Tofamba's human-authorized incident governance platform for FastAPI APIs.

**[tofamba.com](https://tofamba.com)** · **[app.tofamba.com](https://app.tofamba.com)**

---

## Status

Tofamba Pulse is in active development. AlertEngine (the infrastructure governance layer) is production-ready and available now.

[Join the early access list →](mailto:tofambatech@outlook.com)
