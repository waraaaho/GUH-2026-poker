#!/usr/bin/env python3
"""Generate a local offline demo tournament export (if needed) and serve the
dashboard on http://127.0.0.1:<port> for inspection in Chrome.

Usage:
    python3 scripts/serve_dashboard.py                  # generate demo + serve on :8000
    python3 scripts/serve_dashboard.py --build-only     # generate site_out/ without serving
    python3 scripts/serve_dashboard.py --deals 30 --port 8080 --regenerate
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import functools
import http.server
import itertools
import json
import os
import pickle
import shutil
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def build_demo_export(event_root: str, site_out: str, deals: int, seed: int) -> None:
    """Runs a quick, deterministic offline round-robin of 3 built-in bots
    (baseline_mc, tight, call) and exports the local static dashboard."""
    from arena.event import Event
    from arena.match import MatchConfig, play_match
    from arena.players import Player, player
    from arena.replays import save_hands, site_hand
    from arena.site_export import Options, export_site
    from model import Model

    ev = Event(event_root)
    bots_dir = ev.path("bots")
    os.makedirs(bots_dir, exist_ok=True)
    os.makedirs(ev.path("hands"), exist_ok=True)

    shutil.copy2(os.path.join(REPO_ROOT, "model.py"), os.path.join(bots_dir, "model.py"))
    pkl_path = os.path.join(bots_dir, "baseline_mc.pkl")
    with open(pkl_path, "wb") as fh:
        pickle.dump(Model(seed=seed), fh)

    roster = {
        "baseline_mc": Player("baseline_mc", pkl_path),
        "tight": player("tight"),
        "call": player("call"),
    }
    names = sorted(roster)

    run_meta = {
        "started_at": time.time(),
        "deals": deals,
        "seed": seed,
        "teams": [{"team": n, "digest": f"local-{n}"} for n in names],
        "finished_at": None,
    }
    with open(ev.path("run.json"), "w", encoding="utf-8") as fh:
        json.dump(run_meta, fh, indent=2)

    cfg = MatchConfig(deals=deals, mode="duplicate", seed=seed)
    pairing_lines: list[str] = []
    for idx, (a, b) in enumerate(itertools.combinations(names, 2)):
        recorded: list[dict] = []

        def _on_hand(record, _buf=recorded):
            _buf.append(site_hand(record, len(_buf)))

        log = play_match([roster[a], roster[b]], config=cfg, on_hand=_on_hand)
        save_hands(ev.path("hands", f"{a}__{b}.jsonl.gz"), recorded)
        pairing_lines.append(
            json.dumps({
                "a": a,
                "b": b,
                "finished_at": time.time() - 10.0 + idx * 0.01,
                "log": asdict(log),
            })
        )

    with open(ev.path("pairings.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(pairing_lines) + "\n")

    options = Options(
        title="NLHE Poker Bot Arena (Offline Local Dashboard)",
        delay=0.0,
        spacing=0.0,
        max_hands=40,
    )
    export_site(ev, site_out, options)


def serve(directory: str, host: str, port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    with http.server.ThreadingHTTPServer((host, port), handler) as httpd:
        print(f"Serving NLHE Poker Arena dashboard at http://{host}:{port}/")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and serve offline poker dashboard.")
    parser.add_argument("--event-root", default=os.path.join(REPO_ROOT, "event", "demo"))
    parser.add_argument("--out", default=os.path.join(REPO_ROOT, "site_out"))
    parser.add_argument("--deals", type=int, default=15, help="Duplicate deals per pairing")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic RNG seed")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--regenerate", action="store_true", help="Re-run demo matches")
    parser.add_argument("--build-only", action="store_true", help="Build site_out without serving")
    args = parser.parse_args(argv)

    manifest_path = os.path.join(args.out, "data", "manifest.json")
    if args.regenerate or not os.path.isfile(manifest_path):
        print(f"Generating deterministic offline demo ({args.deals} duplicate deals/pairing)...")
        build_demo_export(args.event_root, args.out, deals=args.deals, seed=args.seed)
        print(f"Exported dashboard to {args.out}")

    if not args.build_only:
        serve(args.out, args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
