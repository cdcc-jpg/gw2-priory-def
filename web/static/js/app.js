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

  // DOM Handles
  const tome = document.getElementById("grimoire-tome");
  const scene = document.getElementById("scene");
  const bookAura = document.getElementById("book-aura");
  const leftPageBody = document.getElementById("left-page-body");
  const rightPageBody = document.getElementById("right-page-body");
  const flipperLeaf = document.getElementById("flipper-leaf");
  const flipperFrontContent = document.getElementById("flipper-front-content");
  const flipperBackContent = document.getElementById("flipper-back-content");
  const btnPrev = document.getElementById("btn-prev-page");
  const btnNext = document.getElementById("btn-next-page");
  const pageCounterDisplay = document.getElementById("page-counter-display");
  const savedRecipesTabs = document.getElementById("saved-recipes-tabs");
  const tabInscribe = document.getElementById("tab-inscribe");

  // Initialize
  initParticles();
  initMouseParallax();
  loadSavedRecipesFromStorage();
  fetchAccountStatus();
  renderCurrentSpread();

  // Navigation Button Handlers
  btnPrev.addEventListener("click", () => {
    if (currentSpreadIndex > 0) {
      turnPageTo(currentSpreadIndex - 1, "backward");
    }
  });

  btnNext.addEventListener("click", () => {
    if (currentSpreadIndex < savedRecipes.length) {
      turnPageTo(currentSpreadIndex + 1, "forward");
    }
  });

  tabInscribe.addEventListener("click", () => {
    if (currentSpreadIndex !== 0) {
      turnPageTo(0, "backward");
    }
  });

  /**
   * Fetches account telemetry from backend.
   */
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

  /**
   * Loads saved recipes from localStorage.
   */
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

  /**
   * Saves recipes to localStorage.
   */
  function saveRecipesToStorage() {
    try {
      localStorage.setItem("priory_grimoire_recipes", JSON.stringify(savedRecipes));
    } catch (e) {}
    updateRecipeTabs();
  }

  /**
   * Updates top bookmark tabs.
   */
  function updateRecipeTabs() {
    savedRecipesTabs.innerHTML = "";
    savedRecipes.forEach((recipe, idx) => {
      const tab = document.createElement("button");
      tab.className = `tome-tab recipe-tab ${currentSpreadIndex === idx + 1 ? "active" : ""}`;
      tab.innerHTML = `<span>⚔️</span> <span>${escapeHtml(recipe.goal_name)}</span>`;
      tab.addEventListener("click", () => {
        const targetIdx = idx + 1;
        if (targetIdx !== currentSpreadIndex) {
          turnPageTo(targetIdx, targetIdx > currentSpreadIndex ? "forward" : "backward");
        }
      });
      savedRecipesTabs.appendChild(tab);
    });

    tabInscribe.className = `tome-tab ${currentSpreadIndex === 0 ? "active" : ""}`;
  }

  /**
   * Renders the current two-page spread.
   */
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

  /**
   * Renders Spread 0: The Inscription of Intent.
   */
  function renderInscriptionSpread() {
    const armory = accountTelemetry?.account_armory_count ?? "—";
    const mats = accountTelemetry?.account_materials_count ?? "—";
    const gold = accountTelemetry?.wallet?.liquid_gold != null
      ? accountTelemetry.wallet.liquid_gold.toLocaleString(undefined, { maximumFractionDigits: 0 }) + " g"
      : "—";
    const shards = accountTelemetry?.wallet?.spirit_shards?.toLocaleString() ?? "—";
    const aa = accountTelemetry?.wallet?.astral_acclaim?.toLocaleString() ?? "—";
    const vm = accountTelemetry?.wallet?.volatile_magic?.toLocaleString() ?? "—";

    // Left Page: Inscription & Account Journal
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
          <span id="btn-forge-text">Turn the Page & Forge Truth ✦</span>
          <span id="btn-forge-spinner" class="spinner-ink hidden"></span>
        </button>
      </form>

      <div class="quick-incantations">
        <button type="button" class="incantation-btn" data-q="Which 2 legendaries can I quickly craft?">⚡ Fastest 2 Legendaries</button>
        <button type="button" class="incantation-btn" data-q="How do I craft Twilight?">⚔️ Craft Twilight</button>
        <button type="button" class="incantation-btn" data-q="How do I craft Eternity?">✨ Forge Eternity</button>
        <button type="button" class="incantation-btn" data-q="What do I need for Aurene's Bite (Zhaitan Variant)?">🐉 Zhaitan Variant</button>
        <button type="button" class="incantation-btn" data-q="How do I craft WvW Legendary Armor?">🛡️ WvW Armor</button>
      </div>
    `;

    // Right Page: Arcane Vitruvian Transmutation Diagram (True GW2 Lore Aesthetic)
    rightPageBody.innerHTML = `
      <div class="runic-header">ᛈ ᛇ ᛉ ᛊ ᛏ ᛒ ᛖ ᛗ ᛚ ᛜ ᛟ ᛞ</div>
      <h2 class="page-title">The Scrying Matrix</h2>
      <div class="handwritten-subtitle">~ Alchemical Geometry ~</div>
      <div class="ink-divider">✦</div>

      <div class="arcane-diagram-stage">
        <div class="vitruvian-circle-wrap">
          <svg class="arcane-circle-svg" viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="95" fill="none" stroke="#c8963e" stroke-width="1.5" stroke-dasharray="4,4"/>
            <circle cx="100" cy="100" r="80" fill="none" stroke="#70338a" stroke-width="1.2"/>
            <polygon points="100,20 169,140 31,140" fill="none" stroke="#c8963e" stroke-width="1"/>
            <polygon points="100,180 31,60 169,60" fill="none" stroke="#c8963e" stroke-width="1"/>
            <circle cx="100" cy="100" r="45" fill="none" stroke="#70338a" stroke-width="1" stroke-dasharray="2,2"/>
          </svg>
          <div class="center-silhouette">🔮</div>
        </div>

        <div class="handwritten-lore">
          "The Mystic Forge recognizes neither gold nor glory alone, but the harmonious combination of the four gifts."
          <div style="font-family:var(--font-head);font-size:0.75em;color:#c8963e;margin-top:6px;">— Archivist of the Durmand Priory</div>
        </div>
      </div>
    `;

    // Attach Inscription Form Event Listeners
    const form = document.getElementById("inscribe-query-form");
    const input = document.getElementById("inscribe-query-input");
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
  }

  /**
   * Renders Spread N: Saved Legendary Progression Recipe.
   */
  function renderRecipeSpread(guide) {
    const qty = guide.target_quantity > 1 ? `${guide.target_quantity}x ` : "";
    const name = `${qty}${guide.goal_name}`;
    const chatCode = guide.chat_code || "[&AgErZgAA]";

    // Left Page: GW2 Legendary Banner + Recommendations + Roadmap
    leftPageBody.innerHTML = `
      <div class="gw2-legendary-banner">
        <div class="gw2-banner-header">
          <div class="legendary-icon-frame">⚔️</div>
          <div class="legendary-title-block">
            <div class="legendary-title-text">${escapeHtml(name)}</div>
            <div class="legendary-type-subtitle">Legendary Progression Itinerary</div>
          </div>
          <button class="chatcode-stamp" onclick="copyChatCode('${chatCode}', this)" title="Copy Chat Code">
            ${escapeHtml(chatCode)} 📋
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

    // Right Page: Session Checklist + Material Delta + Handwritten Notes
    rightPageBody.innerHTML = `
      <div class="runic-header">ᚠ ᛟ ᚱ ᚷ ᛖ ✦ ᛏ ᚱ ᚢ ᛏ ᚺ</div>
      <h3 class="page-title">Actionable Itinerary</h3>
      <div class="handwritten-subtitle">~ Master Crafter's Notes ~</div>
      <div class="ink-divider">✦</div>

      ${renderChecklistSection(guide.session_checklist)}
      ${renderMaterialsSection(guide.missing_materials_summary)}
      ${renderMarginaliaTip(guide.motivational_tip)}
    `;
  }

  function renderRecommendationsSection(recs) {
    if (!recs || recs.length === 0) return "";
    const items = recs.map(r => `<li>${formatTextWithWaypoints(r)}</li>`).join("");
    return `
      <div class="journal-section">
        <h4>💡 Currency & Strategic Conversions</h4>
        <ul>${items}</ul>
      </div>
    `;
  }

  function renderRoadmapSection(phases) {
    if (!phases || phases.length === 0) return "";
    const items = phases.map(p => `<li>${formatTextWithWaypoints(p)}</li>`).join("");
    return `
      <div class="journal-section">
        <h4>🗺️ 5-Phase Master Crafting Roadmap</h4>
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
        <h4>📋 Session Action Items</h4>
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
        <h4>📦 Material Shortages</h4>
        <div class="journal-mat-tags">${tags}</div>
      </div>
    `;
  }

  function renderMarginaliaTip(tip) {
    if (!tip) return "";
    return `
      <div class="handwritten-marginalia">
        ✒️ Note: ${formatTextWithWaypoints(tip)}
      </div>
    `;
  }

  /**
   * Page Turn Animation with 3D Leaf Flip.
   */
  function turnPageTo(targetIndex, direction = "forward") {
    if (targetIndex === currentSpreadIndex) return;

    // Trigger Aura flare
    bookAura.classList.add("casting");

    // Perform smooth 3D leaf animation
    flipperLeaf.className = `flipper-leaf ${direction === "forward" ? "flipping-forward" : "flipping-backward"}`;
    flipperLeaf.classList.remove("hidden");

    setTimeout(() => {
      currentSpreadIndex = targetIndex;
      renderCurrentSpread();
    }, 420); // Switch page content mid-flip

    setTimeout(() => {
      flipperLeaf.className = "flipper-leaf hidden";
      bookAura.classList.remove("casting");
    }, 850);
  }

  /**
   * Executes query, adds to recipe journal, and turns to the newly forged recipe spread.
   */
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
        // Append to saved recipes if not duplicate
        const existingIdx = savedRecipes.findIndex(r => r.goal_name === data.guide.goal_name);
        if (existingIdx !== -1) {
          savedRecipes[existingIdx] = data.guide; // update
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

  /**
   * Text & Waypoint formatter.
   */
  function formatTextWithWaypoints(text) {
    if (!text) return "";
    let s = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/`?(\[&[A-Za-z0-9+/=]+\])`?/g, (match, wp) => {
      return `<span class="wp-link" onclick="copyChatCode('${wp}', this)" title="Click to copy chat code">${wp}</span>`;
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

  window.copyChatCode = (code, el) => {
    navigator.clipboard.writeText(code);
    const orig = el.innerHTML;
    el.innerHTML = "Copied! ✓";
    setTimeout(() => { el.innerHTML = orig; }, 1200);
  };

  /**
   * Interactive Mouse Parallax.
   */
  function initMouseParallax() {
    scene.addEventListener("mousemove", (e) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      const dx = (e.clientX - cx) / cx;
      const dy = (e.clientY - cy) / cy;
      const rotY = dx * 4;
      const rotX = 6 - dy * 3.5;
      tome.style.transform = `rotateX(${rotX}deg) rotateY(${rotY}deg)`;
    });
  }

  /**
   * Dual-colour floating arcane motes (Gold + Arcane Purple/Blue).
   */
  function initParticles() {
    const c = document.getElementById("particles");
    if (!c) return;
    const ctx = c.getContext("2d");
    let W, H;
    function resize() { W = c.width = window.innerWidth; H = c.height = window.innerHeight; }
    resize();
    window.addEventListener("resize", resize);

    const N = 75;
    const dots = Array.from({ length: N }, () => {
      const isPurple = Math.random() < 0.35;
      return {
        x: Math.random() * W,
        y: Math.random() * H,
        r: Math.random() * 1.8 + 0.4,
        dx: (Math.random() - 0.5) * 0.18,
        dy: -Math.random() * 0.15 - 0.03, // upward draft
        a: Math.random() * 0.4 + 0.08,
        color: isPurple ? [157, 91, 210] : [200, 150, 62],
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
