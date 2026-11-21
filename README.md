# NLHE Poker Bot, Game-Theoretic Solver & Tournament Arena

An offline, deterministic No-Limit Texas Hold'em (NLHE) engine, multi-bot tournament arena, submission vetting pipeline, and classical algorithmic poker bot workbench.

> **Scope Note:** All bot strategies, solvers, and evaluators in this project are **100% classical algorithms and game theory** (bitmask/lookup hand evaluation, Counterfactual Regret Minimization / CFR+, range-based Monte Carlo rollouts, Bayesian frequency tracking, and exact best-response exploitability checks). **Zero ML/neural-network models, model training, or external datasets are used.**

---

## Workspace Tier & Environment Fit

- **Workspace Tier:** `Desktop Workspace` (native Linux x86-64, 4 CPU cores, 16 GB RAM, 100% offline).
- **Stack:** Python 3.10+ with `pydantic`, `pytest`, and `hypothesis` from the offline `pip` mirror, plus Python stdlib `http.server` and zero-CDN HTML/CSS/JS for the local browser viewer.
- **No external services:** Zero internet calls, zero Docker, zero GPU, zero audio, zero native GUI toolkits, and zero `[code workspace only]` services.

---

## Architecture Overview

| Module / Path | Responsibility |
|---|---|
| `card_utils.py`, `player_action.py`, `game_state.py`, `game_interface.py`, `engine.py` | Core NLHE rules engine, side-pot payout solver, hand evaluator, and read-only `GameStateView`. |
| `model.py` | Starter Monte Carlo rollout bot (`Model`) implementing `seed`, `run`, and `end_game`. |
| `arena/` | Duplicate-deal match runner (`match.py`), isolated worker (`worker.py`, `remote.py`), static submission vetter (`vet.py`), hand replay serializer (`replays.py`), tournament orchestrator (`event.py`), and static dashboard exporter (`site_export.py`). |
| `evals/` | Duplicate-deal benchmark runner with 95% confidence intervals (`bb/100`) against built-in sparring bots (`fold`, `call`, `random`, `shove`, `tight`, `equity`). |
| `submit.py` | Local pickling, AST/pickle vetting, and clean-room replay check. |
| `site/` & `scripts/serve_dashboard.py` | Zero-CDN offline browser dashboard (`http://127.0.0.1:8000`) displaying pooled standings, head-to-head matrix, pairings, and hand-by-hand showdown replays. |
| `tests/` | Unit, property-based (`hypothesis`), adversarial legality, and tournament arena tests. |

---

## Quickstart, Testing & Restarting After Session Pauses

### 1. Offline Virtual Environment Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

### 2. Run Full Offline Baseline Verification
```bash
./scripts/run_tests.sh
# Or directly:
.venv/bin/python -m pytest tests -q
```

### 3. Benchmark the Bot (`evals`) & Verify Submission (`submit`)
```bash
# Quick offline evaluation against built-in sparring bots (bb/100 ± 95% CI)
.venv/bin/python -m evals --deals 50

# Validate pickling, static vetting, and isolated replay
.venv/bin/python -m submit --team localbot --out /tmp/localbot.pkl
```

### 4. "See It" — Launch / Restart the Local Chrome Dashboard
Running servers pause between sessions; restart cleanly with one command:
```bash
.venv/bin/python scripts/serve_dashboard.py --port 8000
# Open http://127.0.0.1:8000 in Chrome
```
Pass `--regenerate --deals 20` to re-run the deterministic local demo tournament, or `--build-only` to regenerate `site_out/` without starting the HTTP server. Keep all foreground benchmark runs chunked/resumable (well under 20 minutes per command).

---

## Objective "Done When" Success Bar

All verification checks run 100% locally offline:

1. **Fast Evaluator Oracle Parity & Speed:** Custom bitmask/lookup evaluator matches `card_utils.evaluate` on 100% of 100,000+ seeded random and edge-case 5–7 card hands (all tie-breakers, wheel straights, split pots) and achieves **≥50× speedup** over `card_utils.evaluate`.
2. **Game-Theoretic Solver & Exploitability Bound:** Multi-action preflop/subgame CFR+ solver converges to **< 10 mbb/hand Nash exploitability** verified by an exact offline best-response (BR) oracle on the solved abstraction, with deterministic replay checksums.
3. **Competitive Strength & Robustness:** Combined CFR + range-tracking/exploitative bot achieves **> +60 bb/100** (95% CI strictly > 0) across an expanded adversarial field (6 built-in dummies + stress bots + solved push/fold baseline) across multiple stack depths (10 bb, 25 bb, 50 bb, 100 bb) and multi-way tables, with **0 faults**, **0 static-vetting flags**, and **max move latency < 0.5 s** under 4-core CPU load.
4. **Variance-Reduced Evaluation & Replay Integrity:** All-in equity-adjusted (AIVAT-style) evaluator reduces 95% CI width by **≥30%** on identical seeded decks vs. raw chip outcomes, and all tournament exports survive mid-run restart without duplicating or losing pairings.
5. **Interactive Desktop Dashboard & Test Suite:** Full offline `pytest` suite passes 100%, and `http://127.0.0.1:8000` displays standings, head-to-head heatmaps, exploitability convergence charts, and step-by-step hand replays in Chrome.

---

## Multi-Session Milestone Roadmap (Planned Work Ahead)

- **Milestone 1 — Fast Hand Evaluator & Verification Harness:** Implement a bitmask/lookup 5–7 card evaluator, parity test suite against `card_utils.evaluate`, micro-benchmarks, and deterministic regression fixtures.
- **Milestone 2 — Multi-Action CFR+ Solver & Exact Best-Response Oracle:** Build a resumable CFR+ solver for 25 bb heads-up preflop trees (fold / limp / min-raise / 2.5 bb open / 3-bet / jam) plus an exact best-response calculator to measure exploitability in mbb/hand.
- **Milestone 3 — Online Opponent Modeling & Exploitative Engine:** Build range-weighted equity estimation, Beta-prior opponent frequency tracking, showdown-card range calibration, bet-size-aware range narrowing, depth-aware sizing (10–100 bb), and an adaptive per-move time budget.
- **Milestone 4 — Adversarial Field & Variance-Reduced Arena:** Add plausible adversarial/stress opponent bots (min-raise spammer, check-raiser, calling station, over-bluffer, solved push/fold), AIVAT all-in equity-adjusted scoring, paired bootstrap CIs, Nash averaging, and resumable chunked tournament runners (< 20 min per batch).
- **Milestone 5 — Rich Local Chrome Analytics Dashboard & Hardening:** Upgrade `site/` with interactive head-to-head heatmaps, per-street profit attribution, CFR convergence plots, full hand-replay stepping, and complete offline E2E/regression verification.

---

## For the organiser

Local tournament orchestration runs entirely offline under `event/`:

```bash
.venv/bin/python -m arena.event import DOWNLOADS
.venv/bin/python -m arena.event status
.venv/bin/python -m arena.event run --deals 200 --concurrency 4
.venv/bin/python -m arena.event export --out site_out
```

---

## License & Attribution

Licensed under the **Apache License 2.0** (see [LICENSE](LICENSE)). Based on the GreatUniHack 2026 poker bot starter (`Manchester-AI-Society/poker_bot`), adapted for offline local evaluation and extended with the local dashboard and RC Eval verification harness.
