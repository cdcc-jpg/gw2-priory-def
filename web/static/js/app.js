/**
 * The Priory Grimoire — Single 3-D Book Controller
 *
 * One book. Two pages visible at a time.
 * Left page: inscription (query).
 * Right page: scrying mirror (idle) → flips to reveal results.
 */

document.addEventListener("DOMContentLoaded", () => {

  /* ── DOM handles ──────────────────────────────────────────────────────────── */
  const form          = document.getElementById("query-form");
  const input         = document.getElementById("query-input");
  const btnSubmit     = document.getElementById("btn-submit");
  const btnLabel      = document.getElementById("btn-label");
  const btnSpinner    = document.getElementById("btn-spinner");

  const turningPage   = document.getElementById("turning-page");
  const btnTurnBack   = document.getElementById("btn-turn-back");

  // Left-page account stats
  const statArmory    = document.getElementById("stat-armory");
  const statMaterials = document.getElementById("stat-materials");
  const statGold      = document.getElementById("stat-gold");
  const statShards    = document.getElementById("stat-shards");

  // Results DOM
  const heroName      = document.getElementById("hero-name");
  const heroReadiness = document.getElementById("hero-readiness");
  const chatcodeBtn   = document.getElementById("chatcode-btn");
  const resultSummary = document.getElementById("result-summary");
  const recList       = document.getElementById("rec-list");
  const roadmapList   = document.getElementById("roadmap-list");
  const checklistList = document.getElementById("checklist-list");
  const matTags       = document.getElementById("mat-tags");

  const secRecs       = document.getElementById("sec-recs");
  const secRoadmap    = document.getElementById("sec-roadmap");
  const secChecklist  = document.getElementById("sec-checklist");
  const secMaterials  = document.getElementById("sec-materials");

  /* ── Ambient particles ────────────────────────────────────────────────────── */
  initParticles();

  /* ── Load telemetry ───────────────────────────────────────────────────────── */
  fetchStatus();

  /* ── Form submit ──────────────────────────────────────────────────────────── */
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (q) runQuery(q);
  });

  /* ── Quick-spell chips ────────────────────────────────────────────────────── */
  document.querySelectorAll(".spell").forEach((btn) => {
    btn.addEventListener("click", () => {
      input.value = btn.dataset.q;
      runQuery(btn.dataset.q);
    });
  });

  /* ── Turn back ────────────────────────────────────────────────────────────── */
  btnTurnBack.addEventListener("click", () => {
    turningPage.classList.remove("flipped");
  });

  /* ── Chat-code copy ───────────────────────────────────────────────────────── */
  chatcodeBtn.addEventListener("click", () => {
    const code = chatcodeBtn.textContent.trim();
    navigator.clipboard.writeText(code);
    const orig = chatcodeBtn.textContent;
    chatcodeBtn.textContent = "Copied ✓";
    setTimeout(() => { chatcodeBtn.textContent = orig; }, 1200);
  });

  /* ── Core query flow ──────────────────────────────────────────────────────── */
  async function runQuery(query) {
    setLoading(true);

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();

      if (data.success && data.guide) {
        renderGuide(data.guide);
        // Flip the page to reveal results
        turningPage.classList.add("flipped");
      } else {
        alert(data.error || "The mirror could not resolve your query.");
      }
    } catch (err) {
      alert("Connection to the Priory lost: " + err.message);
    } finally {
      setLoading(false);
    }
  }

  /* ── Render guide onto the results page ───────────────────────────────────── */
  function renderGuide(g) {
    const qty = g.target_quantity > 1 ? g.target_quantity + "× " : "";
    heroName.textContent = qty + g.goal_name;
    heroReadiness.textContent = g.readiness_percentage + "%";
    resultSummary.textContent = g.executive_summary || "";

    if (g.chat_code) {
      chatcodeBtn.textContent = g.chat_code;
      chatcodeBtn.classList.remove("hidden");
    } else {
      chatcodeBtn.classList.add("hidden");
    }

    // Recommendations
    recList.innerHTML = "";
    if (g.strategic_recommendations?.length) {
      g.strategic_recommendations.forEach((r) => {
        const li = document.createElement("li");
        li.innerHTML = fmtWp(r);
        recList.appendChild(li);
      });
      secRecs.classList.remove("hidden");
    } else { secRecs.classList.add("hidden"); }

    // Roadmap
    roadmapList.innerHTML = "";
    if (g.master_roadmap_phases?.length) {
      g.master_roadmap_phases.forEach((p) => {
        const li = document.createElement("li");
        li.innerHTML = fmtWp(p);
        roadmapList.appendChild(li);
      });
      secRoadmap.classList.remove("hidden");
    } else { secRoadmap.classList.add("hidden"); }

    // Checklist
    checklistList.innerHTML = "";
    if (g.session_checklist?.length) {
      g.session_checklist.forEach((s) => {
        const row = document.createElement("div");
        row.className = "ck-item";
        row.innerHTML =
          `<span class="ck-step">${s.step_number}</span>` +
          `<span>${esc(s.title)}</span>` +
          `<span class="ck-time">~${s.estimated_time_minutes}m</span>`;
        checklistList.appendChild(row);
      });
      secChecklist.classList.remove("hidden");
    } else { secChecklist.classList.add("hidden"); }

    // Materials
    matTags.innerHTML = "";
    if (g.missing_materials_summary && Object.keys(g.missing_materials_summary).length) {
      Object.entries(g.missing_materials_summary).forEach(([name, count]) => {
        const tag = document.createElement("span");
        tag.className = "mat-tag";
        tag.innerHTML = `${esc(name)} <span class="mat-qty">×${count.toLocaleString()}</span>`;
        matTags.appendChild(tag);
      });
      secMaterials.classList.remove("hidden");
    } else { secMaterials.classList.add("hidden"); }
  }

  /* ── Fetch status & fill left-page stats ──────────────────────────────────── */
  async function fetchStatus() {
    try {
      const r = await fetch("/api/status");
      const d = await r.json();
      statArmory.textContent    = d.account_armory_count ?? "—";
      statMaterials.textContent = d.account_materials_count ?? "—";
      statGold.textContent      = d.wallet?.liquid_gold != null
        ? d.wallet.liquid_gold.toLocaleString(undefined, { maximumFractionDigits: 0 }) + " g"
        : "—";
      statShards.textContent    = d.wallet?.spirit_shards?.toLocaleString() ?? "—";
    } catch (_) { /* silent */ }
  }

  /* ── Helpers ──────────────────────────────────────────────────────────────── */
  function setLoading(on) {
    btnSubmit.disabled = on;
    btnLabel.classList.toggle("hidden", on);
    btnSpinner.classList.toggle("hidden", !on);
  }

  function fmtWp(text) {
    if (!text) return "";
    let s = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/`?(\[&[A-Za-z0-9+/=]+\])`?/g,
      (_, wp) => `<span class="wp" onclick="window._cpWp('${wp}',this)">${wp}</span>`);
    return s;
  }

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  /* ── Global waypoint copy ─────────────────────────────────────────────────── */
  window._cpWp = (code, el) => {
    navigator.clipboard.writeText(code);
    const orig = el.textContent;
    el.textContent = "✓";
    setTimeout(() => { el.textContent = orig; }, 1000);
  };

  /* ── Canvas particles ─────────────────────────────────────────────────────── */
  function initParticles() {
    const c = document.getElementById("particles");
    if (!c) return;
    const ctx = c.getContext("2d");
    let W, H;

    function resize() { W = c.width = window.innerWidth; H = c.height = window.innerHeight; }
    resize();
    window.addEventListener("resize", resize);

    const N = 60;
    const dots = Array.from({ length: N }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.6 + 0.4,
      dx: (Math.random() - 0.5) * 0.18,
      dy: (Math.random() - 0.5) * 0.18,
      a: Math.random() * 0.35 + 0.05,
    }));

    (function frame() {
      ctx.clearRect(0, 0, W, H);
      for (const d of dots) {
        d.x += d.dx; d.y += d.dy;
        if (d.x < 0) d.x = W; if (d.x > W) d.x = 0;
        if (d.y < 0) d.y = H; if (d.y > H) d.y = 0;
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(224,180,74,${d.a})`;
        ctx.fill();
      }
      requestAnimationFrame(frame);
    })();
  }
});
