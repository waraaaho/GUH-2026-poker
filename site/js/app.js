(function () {
  "use strict";

  const state = {
    replay: null,
    handIndex: 0,
  };

  function fmt(num, digits) {
    if (num === null || num === undefined || Number.isNaN(num)) return "—";
    const d = digits === undefined ? 1 : digits;
    return Number(num).toFixed(d);
  }

  function signClass(num) {
    if (num === null || num === undefined) return "";
    if (num > 0) return "pos";
    if (num < 0) return "neg";
    return "";
  }

  async function fetchJson(path) {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
    return res.json();
  }

  function renderStandings(board) {
    const wrap = document.getElementById("standings-wrap");
    if (!board || !board.teams || !board.teams.length) {
      wrap.innerHTML = '<p class="muted">No completed pairings yet.</p>';
      return;
    }
    const rows = board.teams.map((t) => {
      const scoreText = t.score === null ? "—" : `${t.score >= 0 ? "+" : ""}${fmt(t.score)} ± ${fmt(t.ci95)}`;
      return `<tr>
        <td class="num">${t.rank}</td>
        <td><strong>${t.team}</strong></td>
        <td class="num ${signClass(t.score)}">${scoreText}</td>
        <td class="num">${t.wins}-${t.draws}-${t.losses}</td>
        <td class="num">${t.opponents_played}/${t.opponents_expected}</td>
        <td class="num">${t.faults}</td>
      </tr>`;
    }).join("");

    wrap.innerHTML = `<table>
      <thead>
        <tr>
          <th class="num">#</th>
          <th>Bot</th>
          <th class="num">Pooled bb/100 (95% CI)</th>
          <th class="num">W-D-L</th>
          <th class="num">Opponents</th>
          <th class="num">Faults</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  function renderMatrix(board) {
    const wrap = document.getElementById("matrix-wrap");
    if (!board || !board.matrix || !board.teams || !board.teams.length) {
      wrap.innerHTML = '<p class="muted">No matrix available.</p>';
      return;
    }
    const names = board.teams.map((t) => t.team);
    const head = `<tr><th>Row vs Col</th>${names.map((n) => `<th class="num">${n}</th>`).join("")}</tr>`;
    const body = names.map((row) => {
      const cells = names.map((col) => {
        if (row === col) return '<td class="num muted">—</td>';
        const c = board.matrix[row] && board.matrix[row][col];
        if (!c) return '<td class="num muted">…</td>';
        const val = `${c.mean_bb >= 0 ? "+" : ""}${fmt(c.mean_bb)}`;
        return `<td class="num ${signClass(c.mean_bb)}" title="±${fmt(c.ci95_bb)}">${val}</td>`;
      }).join("");
      return `<tr><td><strong>${row}</strong></td>${cells}</tr>`;
    }).join("");
    wrap.innerHTML = `<table><thead>${head}</thead><tbody>${body}</tbody></table>`;
  }

  function renderHand() {
    const wrap = document.getElementById("replay-wrap");
    const counter = document.getElementById("hand-counter");
    const prevBtn = document.getElementById("prev-hand");
    const nextBtn = document.getElementById("next-hand");

    if (!state.replay || !state.replay.hands || !state.replay.hands.length) {
      counter.textContent = "0 / 0";
      prevBtn.disabled = true;
      nextBtn.disabled = true;
      wrap.innerHTML = '<p class="muted">No hands recorded for this pairing.</p>';
      return;
    }

    const hands = state.replay.hands;
    const h = hands[state.handIndex];
    counter.textContent = `Hand ${state.handIndex + 1} / ${hands.length}`;
    prevBtn.disabled = state.handIndex <= 0;
    nextBtn.disabled = state.handIndex >= hands.length - 1;

    const boardStr = h.board && h.board.length ? h.board.join(" ") : "(preflop end)";
    const seatsSummary = h.seats.map((name, idx) => {
      const hole = h.hole ? `[${h.hole[idx].join(" ")}]` : "[hidden]";
      const net = h.net[idx];
      const cls = signClass(net);
      const label = h.res[idx][1] ? ` (${h.res[idx][1]})` : "";
      return `<span class="pill"><strong>${name}</strong> ${hole}${label}: <span class="${cls}">${net >= 0 ? "+" : ""}${net}</span></span>`;
    }).join("");

    const actionRows = h.actions.map(([seat, kind, amount, street]) => {
      const actor = h.seats[seat] || `seat ${seat}`;
      const amt = amount ? ` ${amount}` : "";
      return `<li>[${street}] <strong>${actor}</strong>: ${kind}${amt}</li>`;
    }).join("");

    wrap.innerHTML = `
      <div class="hand-meta">
        <span class="pill">Deal #${h.deal} (rot ${h.o})</span>
        <span class="pill">Blinds ${h.sb}/${h.bb}</span>
        <span class="pill">End: ${h.end}</span>
        <span class="pill">Board: <strong>${boardStr}</strong></span>
      </div>
      <div class="hand-meta">${seatsSummary}</div>
      <ol class="actions-list">${actionRows}</ol>
    `;
  }

  async function loadReplay(pairing, btnEl) {
    document.querySelectorAll(".pairing-btn").forEach((b) => b.classList.remove("active"));
    if (btnEl) btnEl.classList.add("active");
    document.getElementById("replay-title").textContent = `Replay: ${pairing.a} vs ${pairing.b}`;
    const wrap = document.getElementById("replay-wrap");
    if (!pairing.replay) {
      state.replay = null;
      wrap.innerHTML = '<p class="muted">No replay JSON saved for this pairing.</p>';
      return;
    }
    wrap.innerHTML = '<p class="muted">Loading replay…</p>';
    try {
      state.replay = await fetchJson(pairing.replay);
      state.handIndex = 0;
      renderHand();
    } catch (err) {
      wrap.innerHTML = `<p class="neg">Failed to load replay: ${err.message}</p>`;
    }
  }

  function renderPairings(pairings) {
    const wrap = document.getElementById("pairings-wrap");
    if (!pairings || !pairings.length) {
      wrap.innerHTML = '<p class="muted">No completed pairings yet.</p>';
      return;
    }
    wrap.innerHTML = "";
    pairings.forEach((p, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pairing-btn";
      const meanText = `${p.mean_bb >= 0 ? "+" : ""}${fmt(p.mean_bb)} ± ${fmt(p.ci95_bb)} bb/100`;
      btn.innerHTML = `<div><strong>${p.a}</strong> vs <strong>${p.b}</strong></div>
        <div class="muted">${p.hands} hands · ${meanText} · verdict: ${p.verdict}</div>`;
      btn.addEventListener("click", () => loadReplay(p, btn));
      wrap.appendChild(btn);
      if (idx === 0) loadReplay(p, btn);
    });
  }

  async function init() {
    document.getElementById("prev-hand").addEventListener("click", () => {
      if (state.handIndex > 0) {
        state.handIndex -= 1;
        renderHand();
      }
    });
    document.getElementById("next-hand").addEventListener("click", () => {
      if (state.replay && state.handIndex < state.replay.hands.length - 1) {
        state.handIndex += 1;
        renderHand();
      }
    });

    try {
      const manifest = await fetchJson("data/manifest.json");
      const tournament = await fetchJson("data/tournament.json");
      document.getElementById("title").textContent = manifest.title || "NLHE Poker Arena";
      document.getElementById("status-badge").textContent = manifest.phase || "ready";
      const teamsCount = manifest.teams || 0;
      const champion = tournament.champion ? ` · Leader: ${tournament.champion}` : "";
      document.getElementById("subtitle").textContent =
        `Offline local viewer · ${teamsCount} bots${champion}`;

      const board = tournament.groups && tournament.groups[0] ? tournament.groups[0].board : null;
      renderStandings(board);
      renderMatrix(board);

      if (manifest.kinds && manifest.kinds.includes("group")) {
        const pairings = await fetchJson("data/pairings-group.json");
        renderPairings(pairings);
      }
    } catch (err) {
      document.getElementById("status-badge").textContent = "no data";
      document.getElementById("subtitle").textContent =
        `Could not load data/manifest.json (${err.message}). Run scripts/serve_dashboard.py first.`;
    }
  }

  init();
})();
