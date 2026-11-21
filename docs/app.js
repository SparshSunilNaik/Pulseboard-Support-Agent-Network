(() => {
  "use strict";

  const REPO = "https://github.com/SparshSunilNaik/Pulseboard-Support-Agent-Network/blob/main/";
  const SVGNS = "http://www.w3.org/2000/svg";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const portraitMQ = window.matchMedia("(max-width: 640px)");

  /* ---------- scenarios ---------- */
  const tests = [
    {
      id: "test-retry-pass",
      question: "Why did my exports stop?",
      origin: "test",
      group: "First draft fails, the retry passes",
      file: "tests/test_end_to_end.py",
      output: {
        classification: "answerable",
        answer: "Check the export log and the workspace timezone. [Source: <top retrieved document>]",
        sources: [],
        confidence: null,
        requires_human: false,
        reason: "all checks passed",
        node_trace: ["triage:answerable", "retrieval:top_k", "generate:attempt_1", "verify:failed", "generate:attempt_2", "verify:passed", "finalize:answerable"],
      },
    },
    {
      id: "test-retry-fail",
      question: "Why did my exports stop?",
      origin: "test",
      group: "Both drafts fail, so a person takes over",
      file: "tests/test_end_to_end.py",
      output: {
        classification: "answerable",
        answer: "I could not produce a response that passes automatic verification after a retry, so I am deliberately not answering rather than risking misinformation. This case has been flagged for a human support agent with the full diagnostic context.",
        sources: [],
        confidence: 0.0,
        requires_human: true,
        reason: "verification failed after one retry",
        node_trace: ["triage:answerable", "retrieval:top_k", "generate:attempt_1", "verify:failed", "generate:attempt_2", "verify:failed", "safe_response:answerable"],
      },
    },
  ];
  const groupFor = {
    answerable: "Answered from the docs",
    requires_escalation: "Escalation",
    out_of_scope: "Out of scope",
    requires_clarification: "Needs clarification",
  };
  const scenarios = (window.SAMPLES || []).map((s) => ({ ...s, group: groupFor[s.output.classification] || s.output.classification })).concat(tests);

  /* ---------- map geometry (landscape coords; portrait = transposed) ---------- */
  const ST = {
    triage: [130, 210], retrieval: [330, 110], generate: [510, 110],
    verify: [700, 110], finalize: [900, 110], safe_response: [900, 320],
  };
  const TRACKS = {
    trunk: { d: "M40,210 H130", c: "--line-trunk", w: 10 },
    answer: { d: "M130,210 L230,110 H900", c: "--line-answer", w: 10 },
    handoff: { d: "M130,210 L240,320 H900", c: "--line-handoff", w: 10 },
    retry: { d: "M700,110 V62 Q700,40 678,40 H532 Q510,40 510,62 V110", c: "--line-retry", w: 7 },
    fail: { d: "M700,110 V250 L770,320", c: "--line-retry", w: 7, dash: "2 12" },
  };
  const LOOP = "H700 V62 Q700,40 678,40 H532 Q510,40 510,62 V110";
  const ROUTES = {
    answer: { d: "M40,210 H130 L230,110 H900", tracks: ["trunk", "answer"] },
    handoff: { d: "M40,210 H130 L240,320 H900", tracks: ["trunk", "handoff"] },
    retryPass: { d: `M40,210 H130 L230,110 ${LOOP} H900`, tracks: ["trunk", "answer", "retry"] },
    retryFail: { d: `M40,210 H130 L230,110 ${LOOP} H700 V250 L770,320 H900`, tracks: ["trunk", "answer", "retry", "fail", "handoff"] },
  };
  const LABELS = [
    { id: "triage", t: "Triage", s: "sorts into 4 classes", L: [130, 262, "middle"], P: [236, 137, "start"] },
    { id: "retrieval", t: "Retrieval", s: "top 6 passages", L: [330, 152, "middle"], P: [136, 337, "start"] },
    { id: "generate", t: "Generate", s: "Qwen2.5 0.5B", L: [510, 152, "middle"], P: [136, 517, "start"] },
    { id: "verify", t: "Verify", s: "rule checks", L: [718, 152, "start"], P: [136, 684, "start"] },
    { id: "finalize", t: "Finalize", s: "answer goes out", L: [900, 152, "middle"], P: [84, 907, "end"] },
    { id: "safe_response", t: "Safe response", s: "flagged for a person", L: [915, 362, "end"], P: [296, 907, "end"] },
  ];
  const BRANCHES = [
    { t: ["answerable"], L: [244, 92, "start"], P: [92, 252, "end"] },
    { t: ["clarify, escalate,", "out of scope"], L: [256, 350, "start"], P: [304, 282, "end"], oneLine: true },
    { t: ["fails once, retry"], L: [605, 26, "middle"], P: [26, 610, "end"] },
    { t: ["fails twice"], L: [714, 236, "start"], P: [150, 728, "start"] },
  ];

  function transposePath(d) {
    const toks = d.match(/[MLHVQ]|-?\d+(?:\.\d+)?/g);
    const out = [];
    let cmd = "", nums = [];
    const flush = () => {
      if (!cmd) return;
      if (cmd === "H") out.push("V" + nums.join(" "));
      else if (cmd === "V") out.push("H" + nums.join(" "));
      else {
        const sw = [];
        for (let i = 0; i < nums.length; i += 2) sw.push(nums[i + 1] + "," + nums[i]);
        out.push(cmd + sw.join(" "));
      }
    };
    for (const t of toks) {
      if (/[A-Z]/.test(t)) { flush(); cmd = t; nums = []; } else nums.push(t);
    }
    flush();
    return out.join(" ");
  }

  const mapEl = document.getElementById("map");
  let svg, rider, ring, routePaths = {}, stationEls = {}, trackEls = {}, portrait = false;

  function el(name, attrs, parent) {
    const n = document.createElementNS(SVGNS, name);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function buildMap() {
    portrait = portraitMQ.matches;
    const P = (d) => (portrait ? transposePath(d) : d);
    const pt = ([x, y]) => (portrait ? [y, x] : [x, y]);
    mapEl.textContent = "";
    svg = el("svg", { viewBox: portrait ? "-80 0 540 960" : "0 0 960 400", "aria-hidden": "true", focusable: "false" }, mapEl);

    trackEls = {};
    for (const [k, t] of Object.entries(TRACKS)) {
      const p = el("path", { d: P(t.d), class: "track", "stroke-width": t.w, style: `stroke: var(${t.c})` }, svg);
      if (t.dash) p.setAttribute("stroke-dasharray", t.dash);
      trackEls[k] = p;
    }
    // start terminus
    const [sx, sy] = pt([40, 210]);
    el("line", portrait ? { x1: sx - 16, y1: sy, x2: sx + 16, y2: sy, class: "terminus" } : { x1: sx, y1: sy - 16, x2: sx, y2: sy + 16, class: "terminus" }, svg);

    stationEls = {};
    for (const [id, c] of Object.entries(ST)) {
      const [x, y] = pt(c);
      const g = el("g", { class: "station" + (id === "triage" ? " big" : "") }, svg);
      if (id === "triage") {
        el("circle", { cx: x, cy: y, r: 20 }, g);
        el("circle", { cx: x, cy: y, r: 7, style: "stroke-width:0" }, g);
      } else {
        el("circle", { cx: x, cy: y, r: 13 }, g);
      }
      stationEls[id] = g;
    }

    for (const l of LABELS) {
      const [x, y, a] = portrait ? l.P : l.L;
      const t = el("text", { x, y, class: "label", "text-anchor": a }, svg);
      t.textContent = l.t;
      if (!portrait) {
        const s = el("text", { x, y: y + 20, class: "sub", "text-anchor": a }, svg);
        s.textContent = l.s;
      }
    }
    for (const b of BRANCHES) {
      const [x, y, a] = portrait ? b.P : b.L;
      const t = el("text", { x, y, class: "branch", "text-anchor": a }, svg);
      const lines = !portrait && b.oneLine ? [b.t.join(" ")] : b.t;
      lines.forEach((line, i) => {
        const ts = el("tspan", { x, dy: i === 0 ? 0 : 20 }, t);
        ts.textContent = line;
      });
    }

    routePaths = {};
    for (const [k, r] of Object.entries(ROUTES)) {
      routePaths[k] = el("path", { d: P(r.d), fill: "none", stroke: "none" }, svg);
    }
    ring = el("circle", { r: 17, class: "rider-ring", cx: -100, cy: -100 }, svg);
    rider = el("circle", { r: 9, class: "rider", cx: -100, cy: -100 }, svg);
    hitCache = {};
  }

  /* Distances along a route at which it reaches each station, in order. */
  let hitCache = {};
  function hitsFor(routeKey) {
    if (hitCache[routeKey]) return hitCache[routeKey];
    const path = routePaths[routeKey];
    const len = path.getTotalLength();
    const pts = Object.entries(ST).map(([id, c]) => [id, portrait ? [c[1], c[0]] : c]);
    const hits = [];
    let near = null;
    for (let s = 0; s <= len; s += 1) {
      const p = path.getPointAtLength(s);
      let found = null;
      for (const [id, [x, y]] of pts) if (Math.hypot(p.x - x, p.y - y) < 3) { found = id; break; }
      if (found && found !== near) hits.push({ id: found, at: s });
      near = found;
    }
    hitCache[routeKey] = { len, hits };
    return hitCache[routeKey];
  }

  function routeKeyFor(trace) {
    const nodes = trace.map((t) => t.split(":")[0]);
    const gens = nodes.filter((n) => n === "generate").length;
    if (nodes.includes("safe_response") && gens > 0) return "retryFail";
    if (gens > 1) return "retryPass";
    if (nodes.includes("safe_response")) return "handoff";
    return "answer";
  }

  /* ---------- stub rendering ---------- */
  const $ = (id) => document.getElementById(id);
  const colorForStep = (step) => {
    const [node, branch] = step.split(":");
    if (node === "triage") return "var(--line-trunk)";
    if (node === "safe_response") return "var(--line-handoff)";
    if (node === "verify" && branch === "failed") return "var(--line-retry)";
    return "var(--line-answer)";
  };
  const prettyStep = (step) => {
    const [node, branch] = step.split(":");
    const names = { triage: "Triage", retrieval: "Retrieval", generate: "Generate", verify: "Verify", finalize: "Finalize", safe_response: "Safe response" };
    const b = (branch || "").replace(/_/g, " ").replace("top k", "top 6");
    return `${names[node] || node} <span class="b">${b}</span>`;
  };
  const escapeHTML = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const humanClass = (c) => ({ answerable: "Answerable", requires_clarification: "Needs clarification", requires_escalation: "Needs escalation", out_of_scope: "Out of scope" }[c] || c);

  function renderStub(sc) {
    const o = sc.output;
    const handed = o.requires_human;
    $("stub").style.setProperty("--stub-c", handed ? "var(--line-handoff)" : "var(--line-answer)");
    $("stub-q").textContent = `“${sc.question}”`;
    $("stub-class").textContent = humanClass(o.classification);
    $("stub-human").textContent = handed ? "Yes" : "No";
    $("stub-conf").textContent = o.confidence == null ? "n/a" : o.confidence.toFixed(2);
    $("stub-trace").innerHTML = o.node_trace.map((s) => `<li style="--c:${colorForStep(s)}${s === "verify:failed" ? ";--chip-ink:#14213D" : ""}">${prettyStep(s)}</li>`).join("");
    const firstPara = String(o.answer).split("\n")[0].trim();
    const clipped = firstPara.length < String(o.answer).trim().length;
    $("stub-answer").textContent = firstPara + (clipped ? " …" : "");
    if (o.sources && o.sources.length) {
      $("stub-sources").innerHTML = `<b>Sources it pulled</b><ul>${o.sources.map((s) => `<li>${escapeHTML(s.document)}, ${escapeHTML(s.passage)}</li>`).join("")}</ul>`;
    } else {
      $("stub-sources").innerHTML = "";
    }
    $("stub-reason").textContent = `Why: ${o.reason}`;
    $("stub-json").textContent = JSON.stringify(o, null, 2);
    $("stub-origin").innerHTML = sc.origin === "test"
      ? `From the test suite, with the language model swapped for a stub so the failure is predictable. See <a href="${REPO}${sc.file}">${sc.file}</a>.`
      : `Real output, unedited${clipped ? ", first paragraph shown" : ""}. Full file: <a href="${REPO}${sc.file}">${sc.file}</a>.`;
  }

  /* ---------- animation ---------- */
  let raf = 0;
  function play(sc) {
    cancelAnimationFrame(raf);
    const key = routeKeyFor(sc.output.node_trace);
    const route = ROUTES[key];
    for (const [k, p] of Object.entries(trackEls)) p.classList.toggle("dimmed", !route.tracks.includes(k));
    for (const g of Object.values(stationEls)) g.classList.remove("hit");
    const chips = [...$("stub-trace").children];
    chips.forEach((c) => c.classList.remove("on"));

    const { len, hits } = hitsFor(key);
    const path = routePaths[key];
    const place = (s) => {
      const p = path.getPointAtLength(s);
      rider.setAttribute("cx", p.x); rider.setAttribute("cy", p.y);
      ring.setAttribute("cx", p.x); ring.setAttribute("cy", p.y);
    };
    const reach = (i) => {
      const h = hits[i];
      if (stationEls[h.id]) stationEls[h.id].classList.add("hit");
      if (chips[i]) chips[i].classList.add("on");
    };

    if (reduceMotion.matches) {
      hits.forEach((_, i) => reach(i));
      place(len);
      return;
    }

    const speed = 0.62; // px per ms
    const dwell = 320;
    let s = 0, next = 0, pauseUntil = 0, last = performance.now();
    place(0);
    const tick = (now) => {
      const dt = Math.min(now - last, 50);
      last = now;
      if (now >= pauseUntil) {
        s = Math.min(len, s + dt * speed);
        while (next < hits.length && s >= hits[next].at) {
          s = hits[next].at;
          reach(next);
          next++;
          pauseUntil = now + dwell;
          break;
        }
      }
      place(s);
      if (s < len || next < hits.length) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  }

  /* ---------- ticket list ---------- */
  const list = $("ticket-list");
  let current = scenarios[0];
  function select(sc, btn) {
    current = sc;
    list.querySelectorAll(".ticket").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
    renderStub(sc);
    play(sc);
  }
  scenarios.forEach((sc, i) => {
    if (sc.origin === "test" && (i === 0 || scenarios[i - 1].origin !== "test")) {
      const p = document.createElement("p");
      p.className = "ticket-sep";
      p.textContent = "Two runs from the test suite that show the retry loop:";
      list.appendChild(p);
    }
    const b = document.createElement("button");
    b.type = "button";
    b.className = "ticket";
    b.setAttribute("aria-pressed", "false");
    const c = sc.output.requires_human ? "var(--line-handoff)" : "var(--line-answer)";
    b.innerHTML = `<span class="dot" style="--c:${c}" aria-hidden="true"></span><span>${escapeHTML(sc.question)}<span class="group">${escapeHTML(sc.group)}</span></span>`;
    b.addEventListener("click", () => {
      select(sc, b);
      // In the stacked layout the map sits below the list; bring it into view.
      const r = mapEl.getBoundingClientRect();
      if (r.bottom < 0 || r.top > window.innerHeight * 0.6) {
        mapEl.scrollIntoView({ behavior: reduceMotion.matches ? "auto" : "smooth", block: "start" });
      }
    });
    list.appendChild(b);
  });

  buildMap();
  portraitMQ.addEventListener("change", () => { buildMap(); play(current); });
  if (scenarios.length) select(scenarios[0], list.querySelector(".ticket"));

  /* ---------- latency bars ---------- */
  const lat = [
    ["Timezone and exports", 15.39, "answer"],
    ["Read-only API access", 15.78, "answer"],
    ["Escalation checklist", 0.15, "handoff"],
    ["Refund request", 0.14, "handoff"],
    ["Which plan am I on", 0.15, "handoff"],
  ];
  const max = 16;
  $("bars").innerHTML = lat.map(([n, v, line]) =>
    `<li class="bar"><span class="bar-name">${n}</span><span class="bar-track"><span class="bar-fill" style="width:${(v / max) * 82}%;--c:var(--line-${line})"></span><span class="bar-val">${v.toFixed(2)}&nbsp;s</span></span></li>`
  ).join("");

  /* ---------- copy buttons ---------- */
  document.querySelectorAll(".copy").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const text = btn.parentElement.querySelector("code").textContent;
      try {
        await navigator.clipboard.writeText(text);
        btn.textContent = "Copied";
      } catch {
        btn.textContent = "Press Ctrl+C";
        const r = document.createRange();
        r.selectNodeContents(btn.parentElement.querySelector("code"));
        const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
      }
      setTimeout(() => (btn.textContent = "Copy"), 1800);
    });
  });
})();
