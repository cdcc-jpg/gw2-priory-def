/**
 * The Priory Grimoire — GW2 3-D Enchanted Tome Controller
 *
 * Mouse parallax on the book, dual-colour particles (gold + arcane blue),
 * aura intensification during page turn, and page-flip logic.
 */

document.addEventListener("DOMContentLoaded", () => {

  /* ── DOM ───────────────────────────────────────────────────────────────────── */
  const scene        = document.getElementById("scene");
  const book         = document.getElementById("book");
  const aura         = document.getElementById("book-aura");
  const form         = document.getElementById("query-form");
  const input        = document.getElementById("query-input");
  const btnSubmit    = document.getElementById("btn-submit");
  const btnLabel     = document.getElementById("btn-label");
  const btnSpinner   = document.getElementById("btn-spinner");
  const turningPage  = document.getElementById("turning-page");
  const btnBack      = document.getElementById("btn-back");

  const statArmory   = document.getElementById("stat-armory");
  const statMaterials= document.getElementById("stat-materials");
  const statGold     = document.getElementById("stat-gold");
  const statShards   = document.getElementById("stat-shards");

  const rName        = document.getElementById("r-name");
  const rPct         = document.getElementById("r-pct");
  const rCc          = document.getElementById("r-cc");
  const rSum         = document.getElementById("r-sum");
  const recList      = document.getElementById("rec-list");
  const roadmapList  = document.getElementById("roadmap-list");
  const ckList       = document.getElementById("ck-list");
  const mt           = document.getElementById("mt");
  const secRecs      = document.getElementById("sec-recs");
  const secRoadmap   = document.getElementById("sec-roadmap");
  const secChecklist = document.getElementById("sec-checklist");
  const secMats      = document.getElementById("sec-mats");

  /* ── Particles ─────────────────────────────────────────────────────────────── */
  initParticles();

  /* ── Mouse Parallax ────────────────────────────────────────────────────────── */
  scene.addEventListener("mousemove", (e) => {
    const cx = window.innerWidth  / 2;
    const cy = window.innerHeight / 2;
    const dx = (e.clientX - cx) / cx;   // -1 … +1
    const dy = (e.clientY - cy) / cy;
    const rotY = dx * 4;   // max ±4 deg
    const rotX = 5 - dy * 3; // 2…8 deg range
    book.style.transform = `rotateX(${rotX}deg) rotateY(${rotY}deg)`;
  });

  /* ── Load status ───────────────────────────────────────────────────────────── */
  fetchStatus();

  /* ── Form submit ───────────────────────────────────────────────────────────── */
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (q) runQuery(q);
  });

  /* ── Quick spells ──────────────────────────────────────────────────────────── */
  document.querySelectorAll(".sp").forEach(b => {
    b.addEventListener("click", () => {
      input.value = b.dataset.q;
      runQuery(b.dataset.q);
    });
  });

  /* ── Turn back ─────────────────────────────────────────────────────────────── */
  btnBack.addEventListener("click", () => {
    turningPage.classList.remove("flipped");
    aura.classList.remove("casting");
  });

  /* ── Chat code copy ────────────────────────────────────────────────────────── */
  rCc.addEventListener("click", () => {
    const code = rCc.textContent.trim();
    navigator.clipboard.writeText(code);
    const orig = rCc.textContent;
    rCc.textContent = "Copied ✓";
    setTimeout(() => { rCc.textContent = orig; }, 1200);
  });

  /* ── Query execution ───────────────────────────────────────────────────────── */
  async function runQuery(query) {
    setLoading(true);

    // Fire aura casting effect
    aura.classList.remove("casting");
    void aura.offsetWidth;           // reflow to restart animation
    aura.classList.add("casting");

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();

      if (data.success && data.guide) {
        renderGuide(data.guide);
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

  /* ── Render guide ──────────────────────────────────────────────────────────── */
  function renderGuide(g) {
    const qty = g.target_quantity > 1 ? g.target_quantity + "× " : "";
    rName.textContent = qty + g.goal_name;
    rPct.textContent  = g.readiness_percentage + "%";
    rSum.textContent  = g.executive_summary || "";

    if (g.chat_code) { rCc.textContent = g.chat_code; rCc.classList.remove("hidden"); }
    else { rCc.classList.add("hidden"); }

    // Recommendations
    recList.innerHTML = "";
    if (g.strategic_recommendations?.length) {
      g.strategic_recommendations.forEach(r => {
        const li = document.createElement("li"); li.innerHTML = fmt(r); recList.appendChild(li);
      });
      secRecs.classList.remove("hidden");
    } else secRecs.classList.add("hidden");

    // Roadmap
    roadmapList.innerHTML = "";
    if (g.master_roadmap_phases?.length) {
      g.master_roadmap_phases.forEach(p => {
        const li = document.createElement("li"); li.innerHTML = fmt(p); roadmapList.appendChild(li);
      });
      secRoadmap.classList.remove("hidden");
    } else secRoadmap.classList.add("hidden");

    // Checklist
    ckList.innerHTML = "";
    if (g.session_checklist?.length) {
      g.session_checklist.forEach(s => {
        const row = document.createElement("div"); row.className = "ck";
        row.innerHTML =
          `<span class="ck-n">${s.step_number}</span>` +
          `<span>${esc(s.title)}</span>` +
          `<span class="ck-t">~${s.estimated_time_minutes}m</span>`;
        ckList.appendChild(row);
      });
      secChecklist.classList.remove("hidden");
    } else secChecklist.classList.add("hidden");

    // Materials
    mt.innerHTML = "";
    if (g.missing_materials_summary && Object.keys(g.missing_materials_summary).length) {
      Object.entries(g.missing_materials_summary).forEach(([name, count]) => {
        const tag = document.createElement("span"); tag.className = "m-tag";
        tag.innerHTML = `${esc(name)} <span class="m-qty">×${count.toLocaleString()}</span>`;
        mt.appendChild(tag);
      });
      secMats.classList.remove("hidden");
    } else secMats.classList.add("hidden");
  }

  /* ── Status fetch ──────────────────────────────────────────────────────────── */
  async function fetchStatus() {
    try {
      const r = await fetch("/api/status");
      const d = await r.json();
      statArmory.textContent    = d.account_armory_count ?? "—";
      statMaterials.textContent = d.account_materials_count ?? "—";
      statGold.textContent      = d.wallet?.liquid_gold != null
        ? d.wallet.liquid_gold.toLocaleString(undefined, { maximumFractionDigits: 0 }) + " g" : "—";
      statShards.textContent    = d.wallet?.spirit_shards?.toLocaleString() ?? "—";
    } catch (_) {}
  }

  /* ── Helpers ───────────────────────────────────────────────────────────────── */
  function setLoading(on) {
    btnSubmit.disabled = on;
    btnLabel.classList.toggle("hidden", on);
    btnSpinner.classList.toggle("hidden", !on);
  }

  function fmt(text) {
    if (!text) return "";
    let s = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/`?(\[&[A-Za-z0-9+/=]+\])`?/g,
      (_, wp) => `<span class="wp" onclick="window._cpWp('${wp}',this)">${wp}</span>`);
    return s;
  }

  function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

  window._cpWp = (code, el) => {
    navigator.clipboard.writeText(code);
    const orig = el.textContent;
    el.textContent = "✓";
    setTimeout(() => { el.textContent = orig; }, 1000);
  };

  /* ── Canvas particles — dual colour (gold + arcane blue) ───────────────────── */
  function initParticles() {
    const c = document.getElementById("particles");
    if (!c) return;
    const ctx = c.getContext("2d");
    let W, H;
    function resize() { W = c.width = window.innerWidth; H = c.height = window.innerHeight; }
    resize(); window.addEventListener("resize", resize);

    const N = 80;
    const dots = Array.from({ length: N }, () => {
      const isBlue = Math.random() < 0.35;
      return {
        x: Math.random() * W,
        y: Math.random() * H,
        r: Math.random() * 1.8 + 0.3,
        dx: (Math.random() - 0.5) * 0.15,
        dy: -Math.random() * 0.12 - 0.02,        // drift upward
        a: Math.random() * 0.4 + 0.05,
        color: isBlue
          ? [74, 144, 217]    // arcane blue
          : [224, 180, 74],   // priory gold
      };
    });

    (function frame() {
      ctx.clearRect(0, 0, W, H);
      for (const d of dots) {
        d.x += d.dx; d.y += d.dy;
        if (d.x < 0) d.x = W; if (d.x > W) d.x = 0;
        if (d.y < -10) d.y = H + 10;
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${d.color[0]},${d.color[1]},${d.color[2]},${d.a})`;
        ctx.fill();
      }
      requestAnimationFrame(frame);
    })();
  }
});
