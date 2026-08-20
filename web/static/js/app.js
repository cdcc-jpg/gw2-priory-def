/**
 * THE PRIORY GRIMOIRE — GUILD WARS 2 LEGENDARY TOME CONTROLLER
 * Multi-page navigation, persistent recipe journal, handwritten ink annotations,
 * and 3D page turn transitions.
 */

document.addEventListener("DOMContentLoaded", () => {

  // State
  let currentSpreadIndex = 0;
  let savedRecipes = [];
  let accountTelemetry = null;
  let isFlipping = false;
  let audioEnabled = localStorage.getItem("priory_audio_enabled") === "true";

  // DOM Handles
  const tome = document.getElementById("grimoire-tome");
  const scene = document.getElementById("scene");
  const bookAura = document.getElementById("book-aura");
  const leftPageBody = document.getElementById("left-page-body");
  const rightPageBody = document.getElementById("right-page-body");
  const flipperLeaf = document.getElementById("flipper-leaf");
  const btnPrev = document.getElementById("btn-prev-page");
  const btnNext = document.getElementById("btn-next-page");
  const pageCounterDisplay = document.getElementById("page-counter-display");
  const savedRecipesTabs = document.getElementById("saved-recipes-tabs");
  const tabInscribe = document.getElementById("tab-inscribe");
  const pageLeft = document.querySelector(".page-left");
  const pageRight = document.querySelector(".page-right");
  
  // Audio toggle button - Assume it exists or we add a listener to it
  const audioToggle = document.getElementById("audio-toggle");
  if (audioToggle) {
    audioToggle.textContent = audioEnabled ? "🔊" : "🔇";
    audioToggle.addEventListener("click", () => {
      audioEnabled = !audioEnabled;
      localStorage.setItem("priory_audio_enabled", audioEnabled);
      audioToggle.textContent = audioEnabled ? "🔊" : "🔇";
    });
  }
  
  let gw2Tooltip = document.getElementById("gw2-tooltip");

  // Initialize
  initParticles();
  initMouseParallax();
  loadSavedRecipesFromStorage();
  fetchAccountStatus();
  renderCurrentSpread();
  initTooltipDelegation();

  // Navigation Button Handlers
  btnPrev.addEventListener("click", () => {
    if (currentSpreadIndex > 0 && !isFlipping) {
      turnPageTo(currentSpreadIndex - 1, "backward");
    }
  });

  btnNext.addEventListener("click", () => {
    if (currentSpreadIndex < savedRecipes.length && !isFlipping) {
      turnPageTo(currentSpreadIndex + 1, "forward");
    }
  });

  tabInscribe.addEventListener("click", () => {
    if (currentSpreadIndex !== 0 && !isFlipping) {
      turnPageTo(0, "backward");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    if (e.key === "ArrowRight") btnNext.click();
    else if (e.key === "ArrowLeft") btnPrev.click();
  });

  function playSound(id) {
    if (!audioEnabled) return;
    const audioEl = document.getElementById(id);
    if (audioEl) {
      audioEl.currentTime = 0;
      audioEl.play().catch(() => {});
    }
  }

  // Quill debounce
  let quillTimeout = null;
  function playQuillSound() {
    if (quillTimeout) return;
    playSound('sfx-quill');
    quillTimeout = setTimeout(() => { quillTimeout = null; }, 3000);
  }

  async function fetchAccountStatus() {
    try {
      const res = await fetch("/api/status");
      accountTelemetry = await res.json();
      if (currentSpreadIndex === 0) {
        renderCurrentSpread();
      }
    } catch (err) {
      console.error("Failed to load status:", err);
    }
  }

  function loadSavedRecipesFromStorage() {
    try {
      const stored = localStorage.getItem("priory_grimoire_recipes");
      if (stored) {
        savedRecipes = JSON.parse(stored);
      }
    } catch (e) {
      savedRecipes = [];
    }
    updateRecipeTabs();
  }

  function saveRecipesToStorage() {
    try {
      localStorage.setItem("priory_grimoire_recipes", JSON.stringify(savedRecipes));
    } catch (e) {}
    updateRecipeTabs();
  }

  function updateRecipeTabs() {
    savedRecipesTabs.innerHTML = "";
    savedRecipes.forEach((recipe, idx) => {
      const tab = document.createElement("button");
      tab.className = `tome-tab recipe-tab ${currentSpreadIndex === idx + 1 ? "active" : ""}`;
      tab.innerHTML = `<span>${escapeHtml(recipe.goal_name)}</span>`;
      tab.addEventListener("click", () => {
        if (isFlipping) return;
        const targetIdx = idx + 1;
        if (targetIdx !== currentSpreadIndex) {
          turnPageTo(targetIdx, targetIdx > currentSpreadIndex ? "forward" : "backward");
        }
      });
      savedRecipesTabs.appendChild(tab);
    });

    tabInscribe.className = `tome-tab ${currentSpreadIndex === 0 ? "active" : ""}`;
  }

  function renderCurrentSpread() {
    const totalSpreads = 1 + savedRecipes.length;
    btnPrev.disabled = currentSpreadIndex === 0;
    btnNext.disabled = currentSpreadIndex >= totalSpreads - 1;

    if (currentSpreadIndex === 0) {
      pageCounterDisplay.textContent = `Chapter I • Inscription • Spread 1 of ${totalSpreads}`;
      renderInscriptionSpread();
    } else {
      const recipe = savedRecipes[currentSpreadIndex - 1];
      pageCounterDisplay.textContent = `Chapter II • ${recipe.goal_name} • Spread ${currentSpreadIndex + 1} of ${totalSpreads}`;
      renderRecipeSpread(recipe);
    }

    updateRecipeTabs();
  }

  function renderInscriptionSpread() {
    const armory = accountTelemetry?.account_armory_count ?? "—";
    const mats = accountTelemetry?.account_materials_count ?? "—";
    const gold = accountTelemetry?.wallet?.liquid_gold != null
      ? accountTelemetry.wallet.liquid_gold.toLocaleString(undefined, { maximumFractionDigits: 0 }) + " g"
      : "—";
    const shards = accountTelemetry?.wallet?.spirit_shards?.toLocaleString() ?? "—";
    const aa = accountTelemetry?.wallet?.astral_acclaim?.toLocaleString() ?? "—";
    const vm = accountTelemetry?.wallet?.volatile_magic?.toLocaleString() ?? "—";

    leftPageBody.innerHTML = `
      <div class="runic-header">ᚠ ᚢ ᚦ ᚨ ᚱ ᚲ ᚷ ᚹ ᚺ ᚾ ᛁ ᛃ</div>
      <h2 class="page-title">Chapter I: Inscription</h2>
      <div class="handwritten-subtitle">~ The Scholar's Ledger ~</div>
      <div class="ink-divider">✦</div>

      <div class="essence-journal-box">
        <div class="essence-journal-title">
          <span>Live Account Essence</span>
          <span style="font-size:0.7em;color:#c8963e;">${accountTelemetry?.api_key_masked || "Live"}</span>
        </div>
        <div class="essence-stats-grid">
          <div class="stat-item"><span class="lbl">Armory Legendaries:</span><span class="val">${armory}</span></div>
          <div class="stat-item"><span class="lbl">Tracked Materials:</span><span class="val">${mats}</span></div>
          <div class="stat-item"><span class="lbl">Liquid Gold:</span><span class="val">${gold}</span></div>
          <div class="stat-item"><span class="lbl">Spirit Shards:</span><span class="val">${shards}</span></div>
          <div class="stat-item"><span class="lbl">Astral Acclaim:</span><span class="val">${aa}</span></div>
          <div class="stat-item"><span class="lbl">Volatile Magic:</span><span class="val">${vm}</span></div>
        </div>
      </div>

      <form class="inscribe-form" id="inscribe-query-form">
        <label class="inscribe-label" for="inscribe-query-input">Inscribe thy desire upon this parchment:</label>
        <textarea id="inscribe-query-input" class="ink-textarea" rows="3" placeholder="e.g. 'Which 2 legendaries can I quickly craft?', 'How do I craft Twilight?'..."></textarea>
        <button type="submit" class="btn-forge-inscribe" id="btn-forge-submit">
          <span id="btn-forge-text">Turn the Page & Forge Truth</span>
          <span id="btn-forge-spinner" class="spinner-ink hidden"></span>
        </button>
      </form>

      <div class="quick-incantations">
        <button type="button" class="incantation-btn" data-q="Which 2 legendaries can I quickly craft?">Fastest 2 Legendaries</button>
        <button type="button" class="incantation-btn" data-q="How do I craft Twilight?">Craft Twilight</button>
        <button type="button" class="incantation-btn" data-q="How do I craft Eternity?">Forge Eternity</button>
        <button type="button" class="incantation-btn" data-q="What do I need for Aurene's Bite (Zhaitan Variant)?">Zhaitan Variant</button>
        <button type="button" class="incantation-btn" data-q="How do I craft WvW Legendary Armor?">WvW Armor</button>
      </div>
    `;

    rightPageBody.innerHTML = `
      <div class="runic-header">ᛈ ᛇ ᛉ ᛊ ᛏ ᛒ ᛖ ᛗ ᛚ ᛜ ᛟ ᛞ</div>
      <h2 class="page-title">The Scrying Matrix</h2>
      <div class="handwritten-subtitle">~ Alchemical Geometry ~</div>
      <div class="ink-divider">✦</div>

      <div class="arcane-diagram-stage">
        <div class="vitruvian-circle-wrap">
          <svg class="arcane-circle-svg" viewBox="0 0 200 200">
            <g class="spin-cw-slow" transform-origin="100 100">
              <circle cx="100" cy="100" r="95" fill="none" stroke="#c8963e" stroke-width="1.5" stroke-dasharray="4,4"/>
              <text x="100" y="15" fill="#c8963e" font-size="10" text-anchor="middle" transform="rotate(0 100 100)">ᚠ</text>
              <text x="100" y="15" fill="#c8963e" font-size="10" text-anchor="middle" transform="rotate(60 100 100)">ᚢ</text>
              <text x="100" y="15" fill="#c8963e" font-size="10" text-anchor="middle" transform="rotate(120 100 100)">ᚦ</text>
              <text x="100" y="15" fill="#c8963e" font-size="10" text-anchor="middle" transform="rotate(180 100 100)">ᚨ</text>
              <text x="100" y="15" fill="#c8963e" font-size="10" text-anchor="middle" transform="rotate(240 100 100)">ᚱ</text>
              <text x="100" y="15" fill="#c8963e" font-size="10" text-anchor="middle" transform="rotate(300 100 100)">ᚲ</text>
            </g>
            <g class="spin-ccw-medium" transform-origin="100 100">
              <circle cx="100" cy="100" r="80" fill="none" stroke="#70338a" stroke-width="1.2"/>
              <polygon points="100,20 169,140 31,140" fill="none" stroke="#c8963e" stroke-width="1"/>
              <polygon points="100,180 31,60 169,60" fill="none" stroke="#c8963e" stroke-width="1"/>
            </g>
            <g class="spin-cw-fast" transform-origin="100 100">
              <circle cx="100" cy="100" r="45" fill="none" stroke="#70338a" stroke-width="1" stroke-dasharray="2,2"/>
              <circle cx="100" cy="100" r="40" fill="none" stroke="#c8963e" stroke-width="0.5"/>
            </g>
          </svg>
          <div class="center-silhouette pulse-anim">◈</div>
        </div>

        <div class="handwritten-lore">
          "The Mystic Forge recognizes neither gold nor glory alone, but the harmonious combination of the four gifts."
          <div style="font-family:var(--font-head);font-size:0.75em;color:#c8963e;margin-top:6px;">— Archivist of the Durmand Priory</div>
        </div>
      </div>
    `;

    const form = document.getElementById("inscribe-query-form");
    const input = document.getElementById("inscribe-query-input");
    
    input.addEventListener("input", playQuillSound);

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = input.value.trim();
      if (q) executeNewQuery(q);
    });

    document.querySelectorAll(".incantation-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const q = btn.getAttribute("data-q");
        input.value = q;
        executeNewQuery(q);
      });
    });
    
    addDynamicStyles();
  }
  
  function addDynamicStyles() {
    if(document.getElementById('app-dynamic-styles')) return;
    const style = document.createElement('style');
    style.id = 'app-dynamic-styles';
    style.innerHTML = `
      @keyframes spin-cw { 100% { transform: rotate(360deg); } }
      @keyframes spin-ccw { 100% { transform: rotate(-360deg); } }
      .spin-cw-slow { animation: spin-cw 60s linear infinite; }
      .spin-ccw-medium { animation: spin-ccw 45s linear infinite; }
      .spin-cw-fast { animation: spin-cw 30s linear infinite; }
      .pulse-anim { animation: pulse 2s ease-in-out infinite; }
      @keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.1); opacity: 1; } }
      .copy-stamp-fx {
        position: fixed;
        color: #ffcc00;
        font-weight: bold;
        text-shadow: 0 0 5px #ffaa00;
        pointer-events: none;
        z-index: 9999;
        animation: float-up-fade 0.8s ease-out forwards;
      }
      @keyframes float-up-fade {
        0% { opacity: 1; transform: translateY(0) scale(1); }
        100% { opacity: 0; transform: translateY(-30px) scale(1.2); }
      }
      .no-select { user-select: none; }
      .mystic-forge-sockets-container {
        display: flex;
        justify-content: space-evenly;
        margin-bottom: 20px;
        flex-wrap: wrap;
        gap: 10px;
      }
      .mf-socket {
        background: rgba(0,0,0,0.2);
        border: 1px solid #c8963e;
        border-radius: 4px;
        padding: 8px;
        text-align: center;
        width: 40%;
        cursor: pointer;
      }
      .mf-socket-icon {
        font-size: 24px;
        margin-bottom: 4px;
      }
      .mf-socket-name {
        font-size: 0.8em;
        color: #eee;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .mf-socket-count {
        font-size: 0.85em;
        color: #c8963e;
        font-weight: bold;
      }
    `;
    document.head.appendChild(style);
  }

  function renderRecipeSpread(guide) {
    const qty = guide.target_quantity > 1 ? `${guide.target_quantity}x ` : "";
    const name = `${qty}${guide.goal_name}`;
    const chatCode = guide.chat_code || "[&AgErZgAA]";

    leftPageBody.innerHTML = `
      <div class="gw2-legendary-banner">
        <div class="gw2-banner-header">
          <div class="legendary-icon-frame">◈</div>
          <div class="legendary-title-block">
            <div class="legendary-title-text">${escapeHtml(name)}</div>
            <div class="legendary-type-subtitle">Legendary Progression Itinerary</div>
          </div>
          <button class="chatcode-stamp" onclick="copyChatCode('${chatCode}', this, event)" title="Copy Chat Code">
            ${escapeHtml(chatCode)}
          </button>
        </div>
        <div class="legendary-lore-quote">
          "${escapeHtml(guide.executive_summary || 'An artifact of tremendous power.')}"
        </div>
        <div class="readiness-meter-row">
          <span>Account Readiness:</span>
          <span class="readiness-pct">${guide.readiness_percentage}%</span>
        </div>
      </div>

      ${renderRecommendationsSection(guide.strategic_recommendations)}
      ${renderRoadmapSection(guide.master_roadmap_phases)}
    `;

    rightPageBody.innerHTML = `
      <div class="runic-header">ᚠ ᛟ ᚱ ᚷ ᛖ ✦ ᛏ ᚱ ᚢ ᛏ ᚺ</div>
      <h3 class="page-title">Actionable Itinerary</h3>
      <div class="handwritten-subtitle">~ Master Crafter's Notes ~</div>
      <div class="ink-divider">✦</div>

      ${renderMysticForgeSockets(guide.missing_materials_summary)}
      ${renderChecklistSection(guide.session_checklist)}
      ${renderMaterialsSection(guide.missing_materials_summary)}
      ${renderMarginaliaTip(guide.motivational_tip)}
    `;
  }
  
  function renderMysticForgeSockets(mats) {
    if (!mats) return "";
    const entries = Object.entries(mats).slice(0, 4);
    if (entries.length === 0) return "";
    
    let html = `<div class="mystic-forge-sockets-container">`;
    entries.forEach(([name, count]) => {
      const tooltipData = { name: name, type: "Crafting Material", rarity: "rare", description: "Used in the Mystic Forge.", source: "Gathered or crafted in Tyria." };
      const dataAttr = JSON.stringify(tooltipData).replace(/"/g, '&quot;');
      html += `
        <div class="mf-socket has-tooltip" data-tooltip="${dataAttr}">
          <div class="mf-socket-icon">◈</div>
          <div class="mf-socket-name">${escapeHtml(name)}</div>
          <div class="mf-socket-count">${count.toLocaleString()} needed</div>
        </div>
      `;
    });
    html += `</div>`;
    return html;
  }

  function renderRecommendationsSection(recs) {
    if (!recs || recs.length === 0) return "";
    const items = recs.map(r => `<li>${formatTextWithWaypoints(r)}</li>`).join("");
    return `
      <div class="journal-section">
        <h4>Currency & Strategic Conversions</h4>
        <ul>${items}</ul>
      </div>
    `;
  }

  function renderRoadmapSection(phases) {
    if (!phases || phases.length === 0) return "";
    const items = phases.map(p => `<li>${formatTextWithWaypoints(p)}</li>`).join("");
    return `
      <div class="journal-section">
        <h4>5-Phase Master Crafting Roadmap</h4>
        <ol>${items}</ol>
      </div>
    `;
  }

  function renderChecklistSection(checklist) {
    if (!checklist || checklist.length === 0) return "";
    const items = checklist.map(s => `
      <div class="journal-checklist-item">
        <span class="ck-step-num">${s.step_number}</span>
        <span><strong>${escapeHtml(s.title)}</strong> — ${formatTextWithWaypoints(s.description)}</span>
        <span class="ck-step-time">~${s.estimated_time_minutes}m</span>
      </div>
    `).join("");
    return `
      <div class="journal-section">
        <h4>Session Action Items</h4>
        <div>${items}</div>
      </div>
    `;
  }

  function renderMaterialsSection(mats) {
    if (!mats || Object.keys(mats).length === 0) return "";
    const tags = Object.entries(mats).map(([k, v]) => `
      <div class="journal-mat-tag">
        <span>${escapeHtml(k)}</span> <span class="count">${v.toLocaleString()} needed</span>
      </div>
    `).join("");
    return `
      <div class="journal-section">
        <h4>Material Shortages</h4>
        <div class="journal-mat-tags">${tags}</div>
      </div>
    `;
  }

  function renderMarginaliaTip(tip) {
    if (!tip) return "";
    return `
      <div class="handwritten-marginalia">
        Note: ${formatTextWithWaypoints(tip)}
      </div>
    `;
  }

  function turnPageTo(targetIndex, direction = "forward") {
    if (targetIndex === currentSpreadIndex) return;
    isFlipping = true;
    document.body.classList.add('no-select');
    playSound('sfx-page-turn');

    bookAura.classList.add("casting");

    if (pageLeft) pageLeft.style.boxShadow = "inset -20px 0 30px rgba(0,0,0,0.8)";
    if (pageRight) pageRight.style.boxShadow = "inset 20px 0 30px rgba(0,0,0,0.8)";

    flipperLeaf.className = `flipper-leaf ${direction === "forward" ? "flipping-forward" : "flipping-backward"}`;
    flipperLeaf.classList.remove("hidden");

    setTimeout(() => {
      currentSpreadIndex = targetIndex;
      renderCurrentSpread();
    }, 420);

    setTimeout(() => {
      flipperLeaf.className = "flipper-leaf hidden";
      bookAura.classList.remove("casting");
      isFlipping = false;
      document.body.classList.remove('no-select');
      
      if (pageLeft) pageLeft.style.boxShadow = "";
      if (pageRight) pageRight.style.boxShadow = "";
    }, 850);
  }

  async function executeNewQuery(query) {
    const btnSubmit = document.getElementById("btn-forge-submit");
    const btnText = document.getElementById("btn-forge-text");
    const btnSpinner = document.getElementById("btn-forge-spinner");

    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnText.classList.add("hidden");
      btnSpinner.classList.remove("hidden");
    }

    bookAura.classList.add("casting");

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();

      if (data.success && data.guide) {
        playSound('sfx-forge-chime');
        const existingIdx = savedRecipes.findIndex(r => r.goal_name === data.guide.goal_name);
        if (existingIdx !== -1) {
          savedRecipes[existingIdx] = data.guide;
          turnPageTo(existingIdx + 1, "forward");
        } else {
          savedRecipes.push(data.guide);
          saveRecipesToStorage();
          turnPageTo(savedRecipes.length, "forward");
        }
      } else {
        alert(data.error || "The Priory could not resolve this recipe.");
      }
    } catch (err) {
      alert("Arcane connection error: " + err.message);
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnText.classList.remove("hidden");
        btnSpinner.classList.add("hidden");
      }
      bookAura.classList.remove("casting");
    }
  }

  function formatTextWithWaypoints(text) {
    if (!text) return "";
    let s = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/`?(\[&[A-Za-z0-9+/=]+\])`?/g, (match, wp) => {
      return `<span class="wp-link" onclick="copyChatCode('${wp}', this, event)" title="Click to copy chat code">${wp}</span>`;
    });
    return s;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  window.copyChatCode = (code, el, e) => {
    navigator.clipboard.writeText(code);
    
    const clickX = e ? e.clientX : window.innerWidth / 2;
    const clickY = e ? e.clientY : window.innerHeight / 2;
    
    const stamp = document.createElement("div");
    stamp.className = "copy-stamp-fx";
    stamp.textContent = "Copied";
    stamp.style.left = `${clickX}px`;
    stamp.style.top = `${clickY}px`;
    document.body.appendChild(stamp);
    
    setTimeout(() => {
      if (stamp.parentNode) {
        stamp.parentNode.removeChild(stamp);
      }
    }, 800);
  };

  function initMouseParallax() {
    scene.addEventListener("mousemove", (e) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      const dx = (e.clientX - cx) / cx;
      const dy = (e.clientY - cy) / cy;
      const rotY = dx * 4;
      const rotX = 6 - dy * 3.5;
      tome.style.transform = `rotateX(${rotX}deg) rotateY(${rotY}deg)`;

      document.querySelectorAll('.desk-prop').forEach(prop => {
        const propDx = dx * cx * 0.3;
        const propDy = dy * cy * 0.3;
        prop.style.transform = `translate(${propDx}px, ${propDy}px)`;
      });
    });
  }

  function initParticles() {
    const c = document.getElementById("particles");
    if (!c) return;
    const ctx = c.getContext("2d");
    let W, H;
    function resize() { W = c.width = window.innerWidth; H = c.height = window.innerHeight; }
    resize();
    window.addEventListener("resize", resize);

    const L1_COUNT = 15;
    const L2_COUNT = 60;
    const L3_COUNT = 40;

    const dots = [];

    // Layer 1: Large slow ember sparks
    for(let i=0; i<L1_COUNT; i++) {
      dots.push({
        layer: 1,
        x: Math.random() * W, y: Math.random() * H,
        r: Math.random() * 2 + 2,
        dx: (Math.random() - 0.5) * 0.1, dy: -Math.random() * 0.2 - 0.1,
        a: Math.random() * 0.5 + 0.3,
        color: [255, 170, 0]
      });
    }

    // Layer 2: Medium arcane motes
    for(let i=0; i<L2_COUNT; i++) {
      const isPurple = Math.random() < 0.35;
      dots.push({
        layer: 2,
        x: Math.random() * W, y: Math.random() * H,
        r: Math.random() * 1.2 + 0.8,
        dx: (Math.random() - 0.5) * 0.18, dy: -Math.random() * 0.15 - 0.03,
        a: Math.random() * 0.4 + 0.08,
        color: isPurple ? [157, 91, 210] : [200, 150, 62]
      });
    }

    // Layer 3: Tiny dust motes
    for(let i=0; i<L3_COUNT; i++) {
      dots.push({
        layer: 3,
        x: Math.random() * W, y: Math.random() * H,
        r: Math.random() * 0.4 + 0.2,
        dx: (Math.random() - 0.5) * 0.05, dy: (Math.random() - 0.5) * 0.05,
        a: Math.random() * 0.2 + 0.05,
        color: [255, 230, 150]
      });
    }

    (function frame() {
      ctx.clearRect(0, 0, W, H);
      for (const d of dots) {
        d.x += d.dx; d.y += d.dy;
        if (d.x < 0) d.x = W; if (d.x > W) d.x = 0;
        if (d.y < -10) d.y = H + 10;
        if (d.y > H + 10) d.y = -10;
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${d.color[0]},${d.color[1]},${d.color[2]},${d.a})`;
        ctx.fill();
      }
      requestAnimationFrame(frame);
    })();
  }
  
  function initTooltipDelegation() {
    if(!gw2Tooltip) {
      const tt = document.createElement('div');
      tt.id = "gw2-tooltip";
      tt.style.position = "absolute";
      tt.style.display = "none";
      tt.style.pointerEvents = "none";
      tt.style.zIndex = "10000";
      tt.style.background = "rgba(0,0,0,0.9)";
      tt.style.border = "1px solid #c8963e";
      tt.style.padding = "10px";
      tt.style.borderRadius = "4px";
      tt.style.color = "#eee";
      tt.style.maxWidth = "250px";
      tt.style.boxShadow = "0 4px 6px rgba(0,0,0,0.5)";
      document.body.appendChild(tt);
      gw2Tooltip = tt;
    }
    
    document.addEventListener("mouseenter", (e) => {
      const el = e.target;
      if(el && el.classList && el.classList.contains("has-tooltip")) {
        const dataStr = el.getAttribute("data-tooltip");
        if(dataStr) {
          try {
            const data = JSON.parse(dataStr);
            showGw2Tooltip(el, data, e);
          } catch(err) {}
        }
      }
    }, true);
    
    document.addEventListener("mousemove", (e) => {
      const el = e.target;
      if(el && el.classList && el.classList.contains("has-tooltip")) {
        if(gw2Tooltip && gw2Tooltip.style.display !== "none") {
          let x = e.clientX + 15;
          let y = e.clientY + 10;
          const rect = gw2Tooltip.getBoundingClientRect();
          if(x + rect.width > window.innerWidth) x = window.innerWidth - rect.width - 10;
          if(y + rect.height > window.innerHeight) y = window.innerHeight - rect.height - 10;
          gw2Tooltip.style.left = x + "px";
          gw2Tooltip.style.top = y + "px";
        }
      }
    }, true);
    
    document.addEventListener("mouseleave", (e) => {
      const el = e.target;
      if(el && el.classList && el.classList.contains("has-tooltip")) {
        if(gw2Tooltip) gw2Tooltip.style.display = "none";
      }
    }, true);
  }

  function showGw2Tooltip(el, data, e) {
    if(!gw2Tooltip) return;
    
    const colorMap = {
      'legendary': '#8a2be2',
      'ascended': '#fb3e8d',
      'exotic': '#ffa500',
      'rare': '#fcd00b',
      'masterwork': '#1a9306',
      'fine': '#62a4da',
      'basic': '#000000'
    };
    const titleColor = data.rarity ? colorMap[data.rarity.toLowerCase()] || '#fff' : '#fff';

    gw2Tooltip.innerHTML = `
      <div style="color: ${titleColor}; font-weight: bold; font-size: 1.1em; border-bottom: 1px solid #444; padding-bottom: 4px; margin-bottom: 4px;">
        ${escapeHtml(data.name)}
      </div>
      <div style="font-size: 0.85em; color: #ccc; margin-bottom: 4px;">${escapeHtml(data.type || '')}</div>
      <div style="font-size: 0.9em; margin-bottom: 6px;">${escapeHtml(data.description || '')}</div>
      ${data.source ? `<div style="font-size: 0.8em; color: #aaa; font-style: italic;">Source: ${escapeHtml(data.source)}</div>` : ''}
    `;
    
    gw2Tooltip.style.display = "block";
    
    let x = e.clientX + 15;
    let y = e.clientY + 10;
    
    // Quick layout application for bounds checking
    let xStr = x + "px";
    let yStr = y + "px";
    gw2Tooltip.style.left = xStr;
    gw2Tooltip.style.top = yStr;
  }

});
