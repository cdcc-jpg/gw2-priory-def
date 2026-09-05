/**
 * THE PRIORY GRIMOIRE — GUILD WARS 2 LEGENDARY TOME CONTROLLER
 * Multi-page navigation, persistent recipe journal, handwritten ink annotations,
 * smooth 2D page turn transitions, and neuro-symbolic solver suite.
 */

document.addEventListener("DOMContentLoaded", () => {

  // ── State Management ────────────────────────────────────────────────────────
  let currentSpreadIndex = 0;
  let savedRecipes = [];
  let accountTelemetry = null;
  let isFlipping = false;
  let audioEnabled = localStorage.getItem("priory_audio_enabled") === "true";

  // Solver Suite State
  let plannerBudgetMinutes = 60;
  let plannerGoalId = 30704;
  let plannerItineraryData = null;
  let plannerLoading = false;

  let arbitrageGoalId = 30704;
  let arbitrageData = null;
  let arbitrageLoading = false;
  let oppCurrencyId = 63;
  let oppQuantity = 100;
  let oppData = null;
  let oppLoading = false;

  let prereqGoalId = 30704;
  let prereqData = null;
  let prereqLoading = false;

  // ── Global Quick Jump Handlers ──────────────────────────────────────────────
  window.jumpToPlanner = (goalId) => {
    plannerGoalId = Number(goalId) || 30704;
    plannerItineraryData = null;
    turnPageTo(1, 1 > currentSpreadIndex ? "forward" : "backward");
  };
  window.jumpToArbitrage = (goalId) => {
    arbitrageGoalId = Number(goalId) || 30704;
    arbitrageData = null;
    turnPageTo(2, 2 > currentSpreadIndex ? "forward" : "backward");
  };
  window.jumpToPrereqs = (goalId) => {
    prereqGoalId = Number(goalId) || 30704;
    prereqData = null;
    turnPageTo(3, 3 > currentSpreadIndex ? "forward" : "backward");
  };

  // ── DOM Handles (Coordinated with web/templates/index.html) ──────────────────
  const tome = document.getElementById("grimoire-tome");
  const scene = document.getElementById("scene");
  const bookAura = document.getElementById("book-aura");
  const pagesSpread = document.getElementById("pages-spread");
  const pageLeft = document.getElementById("page-left-content") || document.querySelector(".page-left");
  const pageRight = document.getElementById("page-right-content") || document.querySelector(".page-right");
  const leftPageBody = document.getElementById("left-page-body");
  const rightPageBody = document.getElementById("right-page-body");
  const flipperLeaf = document.getElementById("flipper-leaf");
  const btnPrev = document.getElementById("btn-prev-page");
  const btnNext = document.getElementById("btn-next-page");
  const pageCounterDisplay = document.getElementById("page-counter-display");
  const savedRecipesTabs = document.getElementById("saved-recipes-tabs");
  const tabInscribe = document.getElementById("tab-inscribe");
  const tabPlanner = document.getElementById("tab-planner");
  const tabArbitrage = document.getElementById("tab-arbitrage");
  const tabPrereqs = document.getElementById("tab-prereqs");
  const audioToggle = document.getElementById("audio-toggle");

  // Audio toggle button with active state indicators
  if (audioToggle) {
    const updateAudioButton = () => {
      audioToggle.classList.toggle("active", audioEnabled);
      audioToggle.setAttribute("aria-pressed", audioEnabled ? "true" : "false");
      audioToggle.innerHTML = audioEnabled 
        ? `<span class="audio-icon">🔊</span><span class="audio-label">Sound On</span>` 
        : `<span class="audio-icon">🔇</span><span class="audio-label">Sound Off</span>`;
      audioToggle.title = audioEnabled ? "Ambient sound enabled (Click to mute)" : "Ambient sound muted (Click to enable)";
    };
    updateAudioButton();
    audioToggle.addEventListener("click", () => {
      audioEnabled = !audioEnabled;
      localStorage.setItem("priory_audio_enabled", audioEnabled);
      updateAudioButton();
      if (audioEnabled) {
        getAudioContext();
        playForgeChimeSound();
      }
    });
  }

  let gw2Tooltip = document.getElementById("gw2-tooltip");

  // ── Initialization ──────────────────────────────────────────────────────────
  initParticles();
  loadSavedRecipesFromStorage();
  fetchAccountStatus();
  renderCurrentSpread();
  initTooltipDelegation();
  addDynamicStyles();

  // ── Navigation Button Handlers ──────────────────────────────────────────────
  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      if (currentSpreadIndex > 0 && !isFlipping) {
        turnPageTo(currentSpreadIndex - 1, "backward");
      }
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      const totalSpreads = 4 + savedRecipes.length;
      if (currentSpreadIndex < totalSpreads - 1 && !isFlipping) {
        turnPageTo(currentSpreadIndex + 1, "forward");
      }
    });
  }

  if (tabInscribe) {
    tabInscribe.addEventListener("click", () => {
      if (currentSpreadIndex !== 0 && !isFlipping) {
        turnPageTo(0, "backward");
      }
    });
  }

  if (tabPlanner) {
    tabPlanner.addEventListener("click", () => {
      if (currentSpreadIndex !== 1 && !isFlipping) {
        turnPageTo(1, 1 > currentSpreadIndex ? "forward" : "backward");
      }
    });
  }

  if (tabArbitrage) {
    tabArbitrage.addEventListener("click", () => {
      if (currentSpreadIndex !== 2 && !isFlipping) {
        turnPageTo(2, 2 > currentSpreadIndex ? "forward" : "backward");
      }
    });
  }

  if (tabPrereqs) {
    tabPrereqs.addEventListener("click", () => {
      if (currentSpreadIndex !== 3 && !isFlipping) {
        turnPageTo(3, 3 > currentSpreadIndex ? "forward" : "backward");
      }
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
    if (e.key === "ArrowRight") {
      if (btnNext && !btnNext.disabled && !isFlipping) btnNext.click();
    } else if (e.key === "ArrowLeft") {
      if (btnPrev && !btnPrev.disabled && !isFlipping) btnPrev.click();
    }
  });

  // ── Procedural Web Audio API Synthesizer (Zero 404s, 100% Offline) ──────────
  let audioCtx = null;
  function getAudioContext() {
    if (!audioEnabled) return null;
    try {
      if (!audioCtx && (window.AudioContext || window.webkitAudioContext)) {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        audioCtx = new AudioContextClass();
      }
      if (audioCtx && audioCtx.state === "suspended") {
        audioCtx.resume().catch(() => {});
      }
      return audioCtx;
    } catch (e) {
      return null;
    }
  }

  function playPaperTurnSound() {
    if (!audioEnabled) return;
    const ctx = getAudioContext();
    if (!ctx) return;

    try {
      const duration = 0.38;
      const bufferSize = Math.floor(ctx.sampleRate * duration);
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
      }

      const noise = ctx.createBufferSource();
      noise.buffer = buffer;

      // Filtered white noise simulating parchment flutter
      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.setValueAtTime(800, ctx.currentTime);
      filter.frequency.exponentialRampToValueAtTime(420, ctx.currentTime + duration);
      filter.Q.setValueAtTime(1.3, ctx.currentTime);

      const gain = ctx.createGain();
      const now = ctx.currentTime;
      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.28, now + 0.04);
      gain.gain.setValueAtTime(0.22, now + 0.12);
      gain.gain.linearRampToValueAtTime(0.26, now + 0.18);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      noise.start(now);
      noise.stop(now + duration);
    } catch (err) {
      // Audio fallback safe
    }
  }

  function playForgeChimeSound() {
    if (!audioEnabled) return;
    const ctx = getAudioContext();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      const duration = 2.2;

      // Master gain
      const masterGain = ctx.createGain();
      masterGain.gain.setValueAtTime(0.35, now);
      masterGain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      masterGain.connect(ctx.destination);

      // Reverb-like decay simulation via low-pass feedback delay
      const delay = ctx.createDelay();
      delay.delayTime.setValueAtTime(0.075, now);
      const delayGain = ctx.createGain();
      delayGain.gain.setValueAtTime(0.32, now);
      const delayFilter = ctx.createBiquadFilter();
      delayFilter.type = "lowpass";
      delayFilter.frequency.setValueAtTime(1500, now);

      masterGain.connect(delay);
      delay.connect(delayFilter);
      delayFilter.connect(delayGain);
      delayGain.connect(delay);
      delayGain.connect(ctx.destination);

      // Bell harmonic chime with dual sine oscillators (880Hz + 1320Hz)
      const osc1 = ctx.createOscillator();
      osc1.type = "sine";
      osc1.frequency.setValueAtTime(880, now);

      const osc2 = ctx.createOscillator();
      osc2.type = "sine";
      osc2.frequency.setValueAtTime(1320, now);

      const osc1Gain = ctx.createGain();
      osc1Gain.gain.setValueAtTime(0.001, now);
      osc1Gain.gain.linearRampToValueAtTime(0.7, now + 0.006);
      osc1Gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

      const osc2Gain = ctx.createGain();
      osc2Gain.gain.setValueAtTime(0.001, now);
      osc2Gain.gain.linearRampToValueAtTime(0.45, now + 0.006);
      osc2Gain.gain.exponentialRampToValueAtTime(0.0001, now + duration * 0.85);

      osc1.connect(osc1Gain);
      osc1Gain.connect(masterGain);

      osc2.connect(osc2Gain);
      osc2Gain.connect(masterGain);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + duration);
      osc2.stop(now + duration);
    } catch (err) {
      // Audio fallback safe
    }
  }

  // Quill debounce
  let quillTimeout = null;
  function playQuillSound() {
    if (!audioEnabled) return;
    if (quillTimeout) return;
    quillTimeout = setTimeout(() => { quillTimeout = null; }, 1200);

    const ctx = getAudioContext();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;
      const duration = 0.22;
      const bufferSize = Math.floor(ctx.sampleRate * duration);
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
      }

      const noise = ctx.createBufferSource();
      noise.buffer = buffer;

      // High-frequency textured noise scratch
      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.setValueAtTime(3600, now);
      filter.Q.setValueAtTime(3.2, now);

      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.2, now + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.02, now + 0.08);
      gain.gain.linearRampToValueAtTime(0.16, now + 0.11);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      noise.start(now);
      noise.stop(now + duration);
    } catch (err) {
      // Audio fallback safe
    }
  }

  function playSound(id) {
    if (!audioEnabled) return;
    if (id === 'sfx-page-turn' || id === 'page-turn') {
      playPaperTurnSound();
      return;
    }
    if (id === 'sfx-forge-chime' || id === 'forge-chime') {
      playForgeChimeSound();
      return;
    }
    if (id === 'sfx-quill' || id === 'quill') {
      playQuillSound();
      return;
    }
    const audioEl = document.getElementById(id);
    if (audioEl) {
      audioEl.currentTime = 0;
      audioEl.play().catch(() => {});
    }
  }
  window.playSound = playSound;

  // ── Account Telemetry ───────────────────────────────────────────────────────
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
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          savedRecipes = parsed;
        } else {
          savedRecipes = [];
        }
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
    if (savedRecipesTabs) {
      savedRecipesTabs.innerHTML = "";
      savedRecipes.forEach((recipe, idx) => {
        const tab = document.createElement("button");
        const targetSpread = 4 + idx;
        tab.className = `tome-tab recipe-tab ${currentSpreadIndex === targetSpread ? "active" : ""}`;
        tab.title = `Chapter V: ${recipe.goal_name}`;
        tab.innerHTML = `<span class="tab-label">${escapeHtml(recipe.goal_name)}</span>`;
        tab.addEventListener("click", () => {
          if (isFlipping) return;
          if (targetSpread !== currentSpreadIndex) {
            turnPageTo(targetSpread, targetSpread > currentSpreadIndex ? "forward" : "backward");
          }
        });
        savedRecipesTabs.appendChild(tab);
      });
    }

    if (tabInscribe) tabInscribe.classList.toggle("active", currentSpreadIndex === 0);
    if (tabPlanner) tabPlanner.classList.toggle("active", currentSpreadIndex === 1);
    if (tabArbitrage) tabArbitrage.classList.toggle("active", currentSpreadIndex === 2);
    if (tabPrereqs) tabPrereqs.classList.toggle("active", currentSpreadIndex === 3);
  }

  // ── Smooth 2D Page Turn Controller ──────────────────────────────────────────
  function turnPageTo(targetIndex, direction = "forward") {
    if (targetIndex === currentSpreadIndex || isFlipping) return;
    isFlipping = true;
    document.body.classList.add('no-select');

    // Procedural Web Audio API sound synthesis
    playPaperTurnSound();

    if (bookAura) {
      bookAura.classList.add("casting");
    }

    // Keep legacy 3D flipper completely hidden
    if (flipperLeaf) {
      flipperLeaf.classList.add("hidden");
    }

    const turnClass = direction === "forward" ? "turning-forward" : "turning-backward";

    if (pagesSpread) {
      pagesSpread.classList.remove("turning-forward", "turning-backward");
      pagesSpread.classList.add(turnClass);
    }
    if (pageLeft) {
      pageLeft.classList.remove("turning-forward", "turning-backward");
      pageLeft.classList.add(turnClass);
    }
    if (pageRight) {
      pageRight.classList.remove("turning-forward", "turning-backward");
      pageRight.classList.add(turnClass);
    }

    // Midpoint: swap content when opacity is low, reset scroll
    setTimeout(() => {
      currentSpreadIndex = targetIndex;
      renderCurrentSpread();
      if (leftPageBody) leftPageBody.scrollTop = 0;
      if (rightPageBody) rightPageBody.scrollTop = 0;
    }, 220);

    // Completion: cleanly remove all transition classes
    setTimeout(() => {
      if (pagesSpread) {
        pagesSpread.classList.remove("turning-forward", "turning-backward");
      }
      if (pageLeft) {
        pageLeft.classList.remove("turning-forward", "turning-backward");
        pageLeft.style.boxShadow = "";
      }
      if (pageRight) {
        pageRight.classList.remove("turning-forward", "turning-backward");
        pageRight.style.boxShadow = "";
      }
      if (bookAura) {
        bookAura.classList.remove("casting");
      }
      document.body.classList.remove('no-select');
      isFlipping = false;
    }, 450);
  }

  function renderCurrentSpread() {
    const totalSpreads = 4 + savedRecipes.length;
    if (btnPrev) btnPrev.disabled = currentSpreadIndex === 0;
    if (btnNext) btnNext.disabled = currentSpreadIndex >= totalSpreads - 1;

    if (currentSpreadIndex === 0) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = `Chapter I • Inscription • Spread 1 of ${totalSpreads}`;
      renderInscriptionSpread();
    } else if (currentSpreadIndex === 1) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = `Chapter II • Daily Session Planner • Spread 2 of ${totalSpreads}`;
      renderSessionPlannerSpread();
    } else if (currentSpreadIndex === 2) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = `Chapter III • Buy vs Craft Arbitrage • Spread 3 of ${totalSpreads}`;
      renderArbitrageSpread();
    } else if (currentSpreadIndex === 3) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = `Chapter IV • Prerequisite Audit • Spread 4 of ${totalSpreads}`;
      renderPrerequisitesSpread();
    } else {
      const recipeIdx = currentSpreadIndex - 4;
      const recipe = savedRecipes[recipeIdx];
      if (pageCounterDisplay) pageCounterDisplay.textContent = `Chapter V • ${recipe ? recipe.goal_name : 'Recipe'} • Spread ${currentSpreadIndex + 1} of ${totalSpreads}`;
      if (recipe) renderRecipeSpread(recipe);
    }

    updateRecipeTabs();
  }

  // ── CHAPTER I: INSCRIPTION ──────────────────────────────────────────────────
  function renderInscriptionSpread() {
    const armory = accountTelemetry?.account_armory_count ?? "—";
    const mats = accountTelemetry?.account_materials_count ?? "—";
    const gold = accountTelemetry?.wallet?.liquid_gold != null
      ? accountTelemetry.wallet.liquid_gold.toLocaleString(undefined, { maximumFractionDigits: 0 }) + " g"
      : "—";
    const shards = accountTelemetry?.wallet?.spirit_shards?.toLocaleString() ?? "—";
    const aa = accountTelemetry?.wallet?.astral_acclaim?.toLocaleString() ?? "—";
    const vm = accountTelemetry?.wallet?.volatile_magic?.toLocaleString() ?? "—";

    if (leftPageBody) {
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
    }

    if (rightPageBody) {
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
    }

    const form = document.getElementById("inscribe-query-form");
    const input = document.getElementById("inscribe-query-input");
    
    if (input) {
      input.addEventListener("input", playQuillSound);
    }

    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        const q = input ? input.value.trim() : "";
        if (q) executeNewQuery(q);
      });
    }

    document.querySelectorAll(".incantation-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const q = btn.getAttribute("data-q");
        if (input) input.value = q;
        if (q) executeNewQuery(q);
      });
    });
  }

  function addDynamicStyles() {
    if (document.getElementById('app-dynamic-styles')) return;
    const style = document.createElement('style');
    style.id = 'app-dynamic-styles';
    style.innerHTML = `
      /* ── 2D Smooth Page Turn Transitions ── */
      .pages-spread.turning-forward .page-sheet,
      .page-sheet.turning-forward {
        animation: pageTurnForward 0.45s cubic-bezier(0.4, 0, 0.2, 1) forwards;
      }
      .pages-spread.turning-backward .page-sheet,
      .page-sheet.turning-backward {
        animation: pageTurnBackward 0.45s cubic-bezier(0.4, 0, 0.2, 1) forwards;
      }
      @keyframes pageTurnForward {
        0% { opacity: 1; transform: translateX(0); filter: brightness(1); }
        48% { opacity: 0.12; transform: translateX(-16px) scale(0.99); filter: brightness(0.85); box-shadow: inset -24px 0 32px rgba(40, 20, 5, 0.35); }
        52% { opacity: 0.12; transform: translateX(16px) scale(0.99); filter: brightness(0.85); box-shadow: inset 24px 0 32px rgba(40, 20, 5, 0.35); }
        100% { opacity: 1; transform: translateX(0); filter: brightness(1); }
      }
      @keyframes pageTurnBackward {
        0% { opacity: 1; transform: translateX(0); filter: brightness(1); }
        48% { opacity: 0.12; transform: translateX(16px) scale(0.99); filter: brightness(0.85); box-shadow: inset 24px 0 32px rgba(40, 20, 5, 0.35); }
        52% { opacity: 0.12; transform: translateX(-16px) scale(0.99); filter: brightness(0.85); box-shadow: inset -24px 0 32px rgba(40, 20, 5, 0.35); }
        100% { opacity: 1; transform: translateX(0); filter: brightness(1); }
      }

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

  const LEGENDARY_PRESETS = [
    { id: 30704, name: "Twilight", type: "Gen 1 Greatsword" },
    { id: 30689, name: "Sunrise", type: "Gen 1 Greatsword" },
    { id: 30687, name: "Incinerator", type: "Gen 1 Dagger" },
    { id: 30694, name: "The Bifrost", type: "Gen 1 Staff" },
    { id: 30685, name: "Kudzu", type: "Gen 1 Longbow" },
    { id: 30684, name: "Frostfang", type: "Gen 1 Axe" },
    { id: 30695, name: "Bolt", type: "Gen 1 Sword" },
    { id: 30693, name: "The Predator", type: "Gen 1 Rifle" },
    { id: 30690, name: "The Juggernaut", type: "Gen 1 Hammer" },
    { id: 30686, name: "The Dreamer", type: "Gen 1 Shortbow" },
    { id: 76158, name: "Nevermore", type: "Gen 2 Staff" },
    { id: 76159, name: "Astralaria", type: "Gen 2 Axe" },
    { id: 96203, name: "Aurene's Bite", type: "Gen 3 Greatsword" },
    { id: 100806, name: "Obsidian Breastplate", type: "Heavy Legendary Armor" }
  ];

  function getLegendaryIdByName(name, defaultId = 30704) {
    if (!name) return defaultId;
    const clean = name.toLowerCase().replace(/^(the|aurene's)\s+/, "").trim();
    const found = LEGENDARY_PRESETS.find(p => {
      const pName = p.name.toLowerCase().replace(/^(the|aurene's)\s+/, "").trim();
      return pName === clean || clean.includes(pName) || pName.includes(clean);
    });
    return found ? found.id : defaultId;
  }

  function isComparativeRanking(guide) {
    if (!guide) return false;
    const name = (guide.goal_name || "").toLowerCase();
    if (name.includes("closest:") || name.includes("closest") || name.includes("ranking") || name.includes("rankings") || name.includes("recommendation") || name.includes("leaderboard")) {
      return true;
    }
    if (guide.target_quantity > 1 && (!guide.master_roadmap_phases || guide.master_roadmap_phases.length === 0)) {
      return true;
    }
    if ((!guide.master_roadmap_phases || guide.master_roadmap_phases.length === 0) && (guide.strategic_recommendations && guide.strategic_recommendations.length > 0)) {
      return true;
    }
    if (guide.strategic_recommendations && guide.strategic_recommendations.some(r => r.includes("Leaderboard") || r.includes("Closest Legendaries") || r.includes("Recommendations:"))) {
      return true;
    }
    return false;
  }

  function getLeaderboardTitle(guide) {
    if (!guide || !guide.goal_name) return "CHAPTER II: THE PRIORY LEADERBOARD";
    const raw = guide.goal_name.trim();
    const upper = raw.toUpperCase();
    if (upper.includes("ACCESSOR")) return "LEGENDARY ACCESSORY LEADERBOARD";
    if (upper.includes("WEAPON")) return "LEGENDARY WEAPONS LEADERBOARD";
    if (upper.includes("ARMOR")) return "LEGENDARY ARMOR LEADERBOARD";
    if (upper.includes("TRINKET")) return "LEGENDARY TRINKET LEADERBOARD";
    if (upper.includes("AMULET")) return "LEGENDARY AMULET LEADERBOARD";
    if (upper.includes("RING")) return "LEGENDARY RING LEADERBOARD";
    if (upper.includes("BACKPACK")) return "LEGENDARY BACKPACK LEADERBOARD";
    return "CHAPTER II: THE PRIORY LEADERBOARD";
  }

  function extractLeaderboardData(guide) {
    const items = [];
    if (!guide) return items;

    const recs = guide.strategic_recommendations || [];
    for (const raw of recs) {
      const line = (raw || "").trim();
      if (!line) continue;
      const clean = line.replace(/\*\*/g, "").trim();

      const match = clean.match(/^#(\d+)\s+([^(]+?)(?:\s*\(([^)]+)\))?:\s*([\d.]+)%?\s*Ready\s*\|\s*(?:Est\.?\s*Cost:\s*)?~?([\d.,]+)g\s*\|\s*\[([^\]]+)\](.*)/i);
      if (match) {
        const gateMatch = clean.match(/⏳\s*(~?[\w\s]+gate)/i);
        items.push({
          rank: parseInt(match[1], 10),
          name: match[2].trim(),
          subtype: match[3] ? match[3].trim() : "Item",
          readiness: parseFloat(match[4]),
          cost: parseFloat(match[5].replace(/,/g, "")),
          archetype: match[6].trim(),
          hasKit: clean.includes("Bank Kit") || clean.includes("Starter Kit"),
          hasGate: clean.includes("gate") || clean.includes("⏳"),
          gateText: gateMatch ? gateMatch[1] : (clean.includes("gate") ? "Time-Gated" : null)
        });
        continue;
      }

      const m2 = clean.match(/#(\d+)\s+([A-Za-z0-9' -]+?)(?:\s*\(([^)]+)\))?[:\s-]+(\d+(?:\.\d+)?)%/i);
      if (m2) {
        const goldM = clean.match(/([\d.,]+)\s*g\b/);
        const archM = clean.match(/\[([^\]]+)\]/);
        const gateMatch = clean.match(/⏳\s*(~?[\w\s]+gate)/i);
        items.push({
          rank: parseInt(m2[1], 10),
          name: m2[2].trim(),
          subtype: m2[3] ? m2[3].trim() : "Item",
          readiness: parseFloat(m2[4]),
          cost: goldM ? parseFloat(goldM[1].replace(/,/g, "")) : 0,
          archetype: archM ? archM[1] : "Standard Crafting",
          hasKit: clean.includes("Bank Kit") || clean.includes("Starter Kit"),
          hasGate: clean.includes("gate") || clean.includes("⏳"),
          gateText: gateMatch ? gateMatch[1] : (clean.includes("gate") ? "Time-Gated" : null)
        });
      }
    }

    if (items.length === 0 && guide.goal_name) {
      const topName = guide.goal_name.replace(/^(?:Closest|Ranking|Recommendation|Leaderboard):\s*/i, "").trim();
      items.push({
        rank: 1,
        name: topName || "Top Recommendation",
        subtype: "Legendary",
        readiness: parseFloat(guide.readiness_percentage) || 0,
        cost: 0,
        archetype: "Precursor & Gifts",
        hasKit: (guide.strategic_recommendations || []).some(r => r.includes("Starter Kit") || r.includes("Bank Kit")),
        hasGate: false,
        gateText: null
      });
    }

    return items;
  }

  function renderLeaderboardSpread(guide) {
    const items = extractLeaderboardData(guide);
    const topItem = items[0] || {
      rank: 1,
      name: guide.goal_name || "Top Recommendation",
      subtype: "Legendary",
      readiness: parseFloat(guide.readiness_percentage) || 0,
      cost: 0,
      archetype: "Precursor & Gifts",
      hasKit: false,
      hasGate: false,
      gateText: null
    };
    const subItems = items.slice(1, 5);
    const heroItemId = getLegendaryIdByName(topItem.name, guide.goal_item_id || 30704);
    const title = getLeaderboardTitle(guide);

    const starterKitRec = (guide.strategic_recommendations || []).find(r => r.includes("Starter Kit") || r.includes("Bank Kit"));
    const boosterRec = (guide.strategic_recommendations || []).find(r => r.includes("Booster") || r.includes("Speed Analysis") || r.includes("Zhaitaffy") || r.includes("Speed Tips") || r.includes("Wizard"));

    if (leftPageBody) {
      leftPageBody.innerHTML = `
        <div class="runic-header">ᚠ ᛟ ᚱ ᚷ ᛖ ✦ ᛏ ᚱ ᚢ ᛏ ᚺ</div>
        <h3 class="page-title">${escapeHtml(title)}</h3>
        <div class="handwritten-subtitle">~ Top Ranked Recommendations ~</div>
        <div class="ink-divider">✦</div>

        <div class="priory-leaderboard-spread">
          <div class="priory-hero-card">
            <div class="hero-card-header">
              <div class="rank-badge rank-top">
                <span>#1</span>
                <span class="top-pick-sub">TOP PICK</span>
              </div>
              <div class="hero-item-info">
                <div class="hero-item-title">
                  <span class="hero-name">${escapeHtml(topItem.name)}</span>
                  <span class="hero-subtype">(${escapeHtml(topItem.subtype)})</span>
                </div>
                <div class="hero-archetype-row">
                  <span class="archetype-badge">${escapeHtml(topItem.archetype)}</span>
                  ${topItem.hasKit ? `<span class="kit-badge">🎁 Bank Starter Kit Ready (0g Precursor)</span>` : ''}
                  ${topItem.hasGate ? `<span class="gate-badge">⏳ ${escapeHtml(topItem.gateText || 'Time-Gated')}</span>` : ''}
                </div>
              </div>
              <div class="hero-metrics">
                <div class="hero-readiness-label">Account Readiness</div>
                <div class="hero-readiness-val">${topItem.readiness}%</div>
                <div class="hero-cost-val">${topItem.cost > 0 ? `Est. Cost: ~${topItem.cost.toLocaleString()}g` : 'Est. Cost: ~0g (Kit Ready)'}</div>
              </div>
            </div>

            <div class="hero-bar-wrap">
              <div class="readiness-bar-fill" style="width: ${Math.min(100, Math.max(0, topItem.readiness))}%;"></div>
            </div>

            ${topItem.hasKit || starterKitRec ? `
              <div class="starter-kit-callout">
                <span class="kit-icon">🎁</span>
                <div class="kit-callout-text">
                  ${starterKitRec ? formatTextWithWaypoints(starterKitRec) : `<strong>Bank Starter Kit Ready:</strong> Select this weapon to claim its Precursor and Gift for <strong>0 gold</strong> from your Legendary Weapon Starter Kit!`}
                </div>
              </div>
            ` : ''}

            <div class="recipe-jump-bar hero-jump-bar">
              <button type="button" class="btn-jump-tool" onclick="jumpToPlanner(${heroItemId})">⏱ Plan Session</button>
              <button type="button" class="btn-jump-tool" onclick="jumpToArbitrage(${heroItemId})">⚖ Arbitrage Matrix</button>
              <button type="button" class="btn-jump-tool" onclick="jumpToPrereqs(${heroItemId})">📜 Prerequisite Audit</button>
            </div>
          </div>

          ${subItems.length > 0 ? `
            <div class="priory-subcards-list">
              ${subItems.map(item => {
                const subId = getLegendaryIdByName(item.name, guide.goal_item_id || 30704);
                return `
                  <div class="priory-sub-card">
                    <div class="rank-badge rank-sub">#${item.rank}</div>
                    <div class="sub-card-main">
                      <div class="sub-card-title-row">
                        <span class="sub-item-name">${escapeHtml(item.name)}</span>
                        <span class="sub-item-subtype">(${escapeHtml(item.subtype)})</span>
                        <span class="sub-item-cost">${item.cost > 0 ? `~${item.cost.toLocaleString()}g` : '~0g'}</span>
                        <span class="sub-item-readiness">${item.readiness}%</span>
                      </div>
                      <div class="sub-bar-wrap">
                        <div class="readiness-bar-fill" style="width: ${Math.min(100, Math.max(0, item.readiness))}%;"></div>
                      </div>
                      <div class="sub-badges-row">
                        <span class="archetype-pill">${escapeHtml(item.archetype)}</span>
                        ${item.hasKit ? `<span class="kit-pill">🎁 Kit Ready</span>` : ''}
                        ${item.hasGate ? `<span class="gate-pill">⏳ ${escapeHtml(item.gateText || 'Time-Gated')}</span>` : ''}
                        <div class="sub-card-actions">
                          <button type="button" class="btn-sub-jump" onclick="jumpToPlanner(${subId})" title="Plan Session">⏱ Plan</button>
                          <button type="button" class="btn-sub-jump" onclick="jumpToArbitrage(${subId})" title="Buy vs Craft">⚖ Arbitrage</button>
                          <button type="button" class="btn-sub-jump" onclick="jumpToPrereqs(${subId})" title="Prerequisite Audit">📜 Prereqs</button>
                        </div>
                      </div>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          ` : ''}
        </div>

        <div class="handwritten-marginalia" style="margin-top: 6px;">
          "The wise arcanist observes all paths before committing the first ingot."
        </div>
      `;
    }

    const checklist = guide.session_checklist && guide.session_checklist.length > 0
      ? guide.session_checklist
      : [
          {
            step_number: 1,
            title: "Claim Precursor / Starter Kit",
            estimated_time_minutes: 2,
            game_mode: "Account",
            description: "Withdraw your Starter Kit or Precursor from the Bank or inventory.",
            chat_code: null
          },
          {
            step_number: 2,
            title: "Complete Wizard's Vault Objectives",
            estimated_time_minutes: 10,
            game_mode: "OpenWorld",
            description: "Clear daily objectives and exchange Astral Acclaim for Mystic Clovers.",
            chat_code: null
          }
        ];

    const boosterText = boosterRec
      ? boosterRec
      : "⚡ **Speed Analysis & Boosters:** Stack Experience + Heroic + Guild Tavern WvW buff (Gift of Battle in ~4.5h vs 8h). Convert Astral Acclaim into Mystic Clovers from Wizard's Vault to bypass Mystic Forge gambling.";

    if (rightPageBody) {
      rightPageBody.innerHTML = `
        <div class="runic-header">ᛋ ᛏ ᚱ ᚨ ᛏ ᛖ ᚷ ᛁ ᚲ ✦ ᛈ ᚨ ᚦ</div>
        <h3 class="page-title">Strategic Acceleration</h3>
        <div class="handwritten-subtitle">~ Priority Action Items & Speed Protocol ~</div>
        <div class="ink-divider">✦</div>

        <div class="leaderboard-synergy-box booster-synergy-box">
          <div class="synergy-box-title">
            <span class="synergy-icon">⚡</span>
            <span>Speed Tips & Booster Acceleration</span>
          </div>
          <div class="synergy-box-content">
            ${formatTextWithWaypoints(boosterText)}
          </div>
        </div>

        <div class="journal-section" style="margin-top: 4px;">
          <h4>Actionable Session Checklist</h4>
          <div class="leaderboard-checklist">
            ${checklist.map(step => `
              <div class="leaderboard-ck-item">
                <div class="ck-item-top">
                  <span class="ck-step-num">Step ${step.step_number}</span>
                  <span class="ck-step-title"><strong>${escapeHtml(step.title)}</strong></span>
                  <span class="ck-step-time">~${step.estimated_time_minutes}m</span>
                  ${step.game_mode ? `<span class="ck-mode-badge mode-${escapeHtml((step.game_mode||'').toLowerCase())}">[${escapeHtml(step.game_mode)}]</span>` : ''}
                </div>
                <div class="ck-item-desc">
                  ${formatTextWithWaypoints(step.description)}
                </div>
                ${step.chat_code ? `
                  <div class="ck-item-footer">
                    <button class="chatcode-stamp ck-wp-btn" onclick="copyChatCode('${step.chat_code}', this, event)" title="Click to copy waypoint">
                      <span>📍</span> WP: ${escapeHtml(step.chat_code)}
                    </button>
                  </div>
                ` : ''}
              </div>
            `).join('')}
          </div>
        </div>

        ${renderMarginaliaTip(guide.motivational_tip || "Archivist Note: Align your daily routines with live currency conversion spikes.")}
      `;
    }
  }

  function renderRecipeSpread(guide) {
    if (isComparativeRanking(guide)) {
      renderLeaderboardSpread(guide);
      return;
    }
    const qty = guide.target_quantity > 1 ? `${guide.target_quantity}x ` : "";
    const name = `${qty}${guide.goal_name}`;
    const chatCode = guide.chat_code || "[&AgErZgAA]";

    if (leftPageBody) {
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
          <div class="recipe-jump-bar">
            <button type="button" class="btn-jump-tool" onclick="jumpToPlanner(${guide.goal_item_id || 30704})">⏱ Plan Session</button>
            <button type="button" class="btn-jump-tool" onclick="jumpToArbitrage(${guide.goal_item_id || 30704})">⚖ Arbitrage Matrix</button>
            <button type="button" class="btn-jump-tool" onclick="jumpToPrereqs(${guide.goal_item_id || 30704})">📜 Prerequisite Audit</button>
          </div>
        </div>

        ${renderRecommendationsSection(guide.strategic_recommendations)}
        ${renderRoadmapSection(guide.master_roadmap_phases)}
      `;
    }

    if (rightPageBody) {
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
  }
  window.renderRecipeSpread = renderRecipeSpread;
  window.isComparativeRanking = isComparativeRanking;
  
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

  // ── CHAPTER II: SESSION PLANNER ─────────────────────────────────────────────
  function renderGoalSelectOptions(selectedId) {
    return LEGENDARY_PRESETS.map(p => 
      `<option value="${p.id}" ${p.id === selectedId ? 'selected' : ''}>${escapeHtml(p.name)} (${p.type})</option>`
    ).join("");
  }

  function formatCopper(copper) {
    if (copper == null || isNaN(copper)) return "—";
    const negative = copper < 0;
    const absVal = Math.abs(Math.round(copper));
    const gold = Math.floor(absVal / 10000);
    const silver = Math.floor((absVal % 10000) / 100);
    const cop = absVal % 100;

    const prefix = negative ? "-" : "";
    if (gold > 0) {
      return `${prefix}<span class="coin-gold">${gold.toLocaleString()}g</span> <span class="coin-silver">${silver}s</span> <span class="coin-copper">${cop}c</span>`;
    } else if (silver > 0) {
      return `${prefix}<span class="coin-silver">${silver}s</span> <span class="coin-copper">${cop}c</span>`;
    } else {
      return `${prefix}<span class="coin-copper">${cop}c</span>`;
    }
  }

  function renderSessionPlannerSpread() {
    const goalOptions = renderGoalSelectOptions(plannerGoalId);

    if (leftPageBody) {
      leftPageBody.innerHTML = `
        <div class="runic-header">ᛟ ᚱ ᛞ ᛖ ᚱ ✦ ᚲ ᛚ ᛟ ᚲ ᚲ</div>
        <h2 class="page-title">Chapter II: Session Planner</h2>
        <div class="handwritten-subtitle">~ Knapsack Activity Scheduler ~</div>
        <div class="ink-divider">✦</div>

        <div class="inscribe-form">
          <label class="inscribe-label" for="planner-goal-select">Target Legendary Goal:</label>
          <select id="planner-goal-select" class="priory-select">
            ${goalOptions}
          </select>

          <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 8px;">
            <label class="inscribe-label" for="planner-budget-slider" style="font-size: 1.15rem;">Playtime Budget:</label>
            <span id="budget-val-display" style="font-family: var(--font-head); font-weight: 700; color: var(--leather-gold); font-size: 1.05rem;">${plannerBudgetMinutes} mins</span>
          </div>
          <input type="range" id="planner-budget-slider" min="30" max="120" step="30" value="${plannerBudgetMinutes}" class="priory-slider">
          
          <div class="playtime-quick-btns">
            <button type="button" class="playtime-btn ${plannerBudgetMinutes === 30 ? 'active' : ''}" data-mins="30">30m</button>
            <button type="button" class="playtime-btn ${plannerBudgetMinutes === 60 ? 'active' : ''}" data-mins="60">60m</button>
            <button type="button" class="playtime-btn ${plannerBudgetMinutes === 90 ? 'active' : ''}" data-mins="90">90m</button>
            <button type="button" class="playtime-btn ${plannerBudgetMinutes === 120 ? 'active' : ''}" data-mins="120">120m</button>
          </div>

          <button type="button" class="btn-forge-inscribe" id="btn-calc-itinerary" style="margin-top: 10px;">
            <span id="btn-itinerary-text">${plannerLoading ? 'Computing Knapsack Schedule...' : 'Schedule Optimal Itinerary'}</span>
            <span id="btn-itinerary-spinner" class="spinner-ink ${plannerLoading ? '' : 'hidden'}"></span>
          </button>
        </div>

        <div id="planner-summary-container" style="margin-top: 10px;">
          ${renderPlannerSummaryBox()}
        </div>
      `;
    }

    if (rightPageBody) {
      rightPageBody.innerHTML = `
        <div class="runic-header">ᚱ ᛟ ᚢ ᛏ ᛖ ✦ ᛏ ᚨ ᛊ ᚲ ᛊ</div>
        <h3 class="page-title">Prioritized Tasks</h3>
        <div class="handwritten-subtitle">~ Logical Waypoint Route ~</div>
        <div class="ink-divider">✦</div>

        <div id="planner-tasks-container">
          ${renderPlannerTasksList()}
        </div>
      `;
    }

    const goalSelect = document.getElementById("planner-goal-select");
    if (goalSelect) {
      goalSelect.addEventListener("change", (e) => {
        plannerGoalId = parseInt(e.target.value, 10);
      });
    }

    const slider = document.getElementById("planner-budget-slider");
    const valDisplay = document.getElementById("budget-val-display");
    if (slider) {
      slider.addEventListener("input", (e) => {
        plannerBudgetMinutes = parseInt(e.target.value, 10);
        if (valDisplay) valDisplay.textContent = `${plannerBudgetMinutes} mins`;
        document.querySelectorAll(".playtime-btn").forEach(btn => {
          btn.classList.toggle("active", parseInt(btn.getAttribute("data-mins"), 10) === plannerBudgetMinutes);
        });
      });
    }

    document.querySelectorAll(".playtime-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const mins = parseInt(btn.getAttribute("data-mins"), 10);
        plannerBudgetMinutes = mins;
        if (slider) slider.value = mins;
        if (valDisplay) valDisplay.textContent = `${mins} mins`;
        document.querySelectorAll(".playtime-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        executeFetchItinerary(plannerGoalId, plannerBudgetMinutes);
      });
    });

    const btnCalc = document.getElementById("btn-calc-itinerary");
    if (btnCalc) {
      btnCalc.addEventListener("click", () => {
        executeFetchItinerary(plannerGoalId, plannerBudgetMinutes);
      });
    }

    if (!plannerItineraryData && !plannerLoading) {
      executeFetchItinerary(plannerGoalId, plannerBudgetMinutes);
    }
  }

  function renderPlannerSummaryBox() {
    if (!plannerItineraryData) {
      return `
        <div class="essence-journal-box">
          <div class="essence-journal-title">Knapsack Strategy</div>
          <div style="font-size: 0.82rem; color: var(--ink-soft); line-height: 1.4;">
            Applies a 0/1 knapsack priority algorithm over daily time-gated activities (Quartz Crystal Charging, Account Refinements, Ley-Line Anomaly, Provisioner Tokens, Fractals/Vault Clovers, and Antique Summoning Stones) to maximize progression per minute played.
          </div>
        </div>
      `;
    }
    const itin = plannerItineraryData;
    return `
      <div class="essence-journal-box">
        <div class="essence-journal-title">
          <span>${escapeHtml(itin.goal_name)} Itinerary</span>
          <span style="color: var(--leather-gold); font-weight: bold;">${itin.time_utilization_pct}% Utilization</span>
        </div>
        <div class="essence-stats-grid">
          <div class="stat-item"><span class="lbl">Time Budget:</span><span class="val">${itin.time_budget_minutes}m</span></div>
          <div class="stat-item"><span class="lbl">Scheduled Time:</span><span class="val">${itin.total_scheduled_minutes}m</span></div>
          <div class="stat-item"><span class="lbl">Tasks Queued:</span><span class="val">${itin.tasks.length}</span></div>
          <div class="stat-item"><span class="lbl">Unused Window:</span><span class="val">${Math.max(0, itin.time_budget_minutes - itin.total_scheduled_minutes)}m</span></div>
        </div>
        <div style="font-size: 0.8rem; color: var(--ink-mid); margin-top: 8px; font-style: italic;">
          "${escapeHtml(itin.summary)}"
        </div>
      </div>
    `;
  }

  function renderPlannerTasksList() {
    if (plannerLoading) {
      return `<div style="text-align: center; padding: 40px;"><span class="spinner-ink" style="width: 28px; height: 28px; border-width: 3px; border-top-color: var(--leather-gold);"></span><div style="margin-top: 10px; font-family: var(--font-head); color: var(--ink-mid);">Solving 0/1 Knapsack Schedule...</div></div>`;
    }
    if (!plannerItineraryData || !plannerItineraryData.tasks || plannerItineraryData.tasks.length === 0) {
      return `<div style="text-align: center; padding: 30px; color: var(--ink-soft); font-family: var(--font-hand); font-size: 1.15rem;">No tasks scheduled for this duration.</div>`;
    }

    return plannerItineraryData.tasks.map((task, idx) => {
      const inputs = task.required_inputs?.name 
        ? `${task.required_inputs.count || ''}x ${task.required_inputs.name}`
        : (task.required_inputs?.description || (task.required_inputs?.currencies ? Object.entries(task.required_inputs.currencies).map(([k, v]) => `${v} ${k}`).join(', ') : 'None'));
      
      const rewardVal = task.reward_output?.value_towards_goal || task.reward_output?.name || '';
      const charTag = task.character_name 
        ? `<div style="font-size: 0.75rem; color: var(--ink-soft);">👤 Character: <strong style="color: var(--leather-gold);">${escapeHtml(task.character_name)}</strong></div>`
        : '';

      return `
        <div class="task-item-card">
          <div class="task-header-row">
            <span class="task-title">${idx + 1}. ${escapeHtml(task.title)}</span>
            <span class="task-duration-badge">⏱ ${task.estimated_duration_minutes}m</span>
          </div>
          <div class="task-loc-row">
            <span>📍 ${escapeHtml(task.location_name)}</span>
            <button class="chatcode-stamp" onclick="copyChatCode('${task.waypoint_code}', this, event)" title="Copy Waypoint Code">
              ${escapeHtml(task.waypoint_code)}
            </button>
          </div>
          ${charTag}
          <div class="task-desc">${formatTextWithWaypoints(task.instructions)}</div>
          <div class="task-reward-box">
            <div><strong>Inputs:</strong> ${escapeHtml(inputs)}</div>
            <div><strong>Reward:</strong> ${escapeHtml(rewardVal)}</div>
          </div>
        </div>
      `;
    }).join("");
  }

  async function executeFetchItinerary(goalId, minutes) {
    plannerLoading = true;
    const btnText = document.getElementById("btn-itinerary-text");
    const btnSpinner = document.getElementById("btn-itinerary-spinner");
    if (btnText) btnText.textContent = "Computing Knapsack Schedule...";
    if (btnSpinner) btnSpinner.classList.remove("hidden");

    try {
      const res = await fetch("/api/solver/itinerary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal_item_id: goalId, time_budget_minutes: minutes })
      });
      const data = await res.json();
      if (data.success && data.itinerary) {
        plannerItineraryData = data.itinerary;
        const sumCont = document.getElementById("planner-summary-container");
        if (sumCont) sumCont.innerHTML = renderPlannerSummaryBox();
        const taskCont = document.getElementById("planner-tasks-container");
        if (taskCont) taskCont.innerHTML = renderPlannerTasksList();
      } else {
        alert(data.error || "Failed to schedule itinerary.");
      }
    } catch (e) {
      console.error("Itinerary error:", e);
    } finally {
      plannerLoading = false;
      if (btnText) btnText.textContent = "Schedule Optimal Itinerary";
      if (btnSpinner) btnSpinner.classList.add("hidden");
    }
  }

  // ── CHAPTER III: BUY VS CRAFT ARBITRAGE ─────────────────────────────────────
  function renderArbitrageSpread() {
    const goalOptions = renderGoalSelectOptions(arbitrageGoalId);

    if (leftPageBody) {
      leftPageBody.innerHTML = `
        <div class="runic-header">ᚷ ᛟ ᛚ ᛞ ✦ ᛏ ᚨ ᛪ ✦ ᛗ ᚨ ᛏ</div>
        <h2 class="page-title">Chapter III: Arbitrage Matrix</h2>
        <div class="handwritten-subtitle">~ Buy vs Craft vs Vault ~</div>
        <div class="ink-divider">✦</div>

        <div class="inscribe-form">
          <label class="inscribe-label" for="arbitrage-goal-select">Analyze Legendary Item:</label>
          <select id="arbitrage-goal-select" class="priory-select">
            ${goalOptions}
          </select>
          <button type="button" class="btn-forge-inscribe" id="btn-run-arbitrage" style="margin-top: 6px;">
            <span id="btn-arb-text">${arbitrageLoading ? 'Evaluating Arbitrage Matrix...' : 'Evaluate Multi-Way Arbitrage'}</span>
            <span id="btn-arb-spinner" class="spinner-ink ${arbitrageLoading ? '' : 'hidden'}"></span>
          </button>
        </div>

        <div id="arbitrage-left-results" style="margin-top: 10px;">
          ${renderArbitrageLeftContent()}
        </div>
      `;
    }

    if (rightPageBody) {
      rightPageBody.innerHTML = `
        <div class="runic-header">ᛊ ᛏ ᚱ ᚨ ᛏ ᛖ ᚷ ᛁ ᛖ ᛊ</div>
        <h3 class="page-title">Component Paths & Costs</h3>
        <div class="handwritten-subtitle">~ Precursor, Clovers & Opportunity Cost ~</div>
        <div class="ink-divider">✦</div>

        <div id="arbitrage-right-results">
          ${renderArbitrageRightContent()}
        </div>
      `;
    }

    const goalSelect = document.getElementById("arbitrage-goal-select");
    if (goalSelect) {
      goalSelect.addEventListener("change", (e) => {
        arbitrageGoalId = parseInt(e.target.value, 10);
      });
    }

    const btnRun = document.getElementById("btn-run-arbitrage");
    if (btnRun) {
      btnRun.addEventListener("click", () => {
        executeFetchArbitrage(arbitrageGoalId);
      });
    }

    attachOpportunityCostListeners();

    if (!arbitrageData && !arbitrageLoading) {
      executeFetchArbitrage(arbitrageGoalId);
    }
  }

  function renderArbitrageLeftContent() {
    if (arbitrageLoading) {
      return `<div style="text-align: center; padding: 40px;"><span class="spinner-ink" style="width: 28px; height: 28px; border-width: 3px; border-top-color: var(--leather-gold);"></span><div style="margin-top: 10px; font-family: var(--font-head); color: var(--ink-mid);">Calculating Arbitrage Matrices...</div></div>`;
    }
    if (!arbitrageData) {
      return `<div style="text-align: center; padding: 20px; color: var(--ink-soft); font-family: var(--font-hand); font-size: 1.1rem;">Select a legendary and evaluate the multi-way arbitrage matrix.</div>`;
    }

    const rep = arbitrageData;
    let verdictClass = 'craft';
    let verdictLabel = 'RECOMMENDED: CRAFT FOR SELF';
    if (rep.recommended_action === 'CRAFT_FOR_PROFIT') {
      verdictClass = 'profit';
      verdictLabel = '✦ HIGH VALUE: CRAFT FOR PROFIT (TP FLIP) ✦';
    } else if (rep.recommended_action === 'BUY_FINISHED_DIRECT') {
      verdictClass = 'buy';
      verdictLabel = 'RECOMMENDED: BUY DIRECT FROM TRADING POST';
    }

    const marginVal = rep.profit_margin_if_sold != null ? rep.profit_margin_if_sold : 0;
    const marginColor = marginVal >= 0 ? '#2e7d32' : '#c62828';
    const marginSign = marginVal >= 0 ? '+' : '';

    return `
      <div class="verdict-banner ${verdictClass}">
        ${verdictLabel}
      </div>

      <div class="arbitrage-grid">
        <div class="arb-card">
          <span class="arb-card-lbl">Instant TP Buy</span>
          <span class="arb-card-val">${formatCopper(rep.instant_buy_total)}</span>
        </div>
        <div class="arb-card">
          <span class="arb-card-lbl">TP Buy Order</span>
          <span class="arb-card-val">${formatCopper(rep.buy_order_total)}</span>
        </div>
        <div class="arb-card">
          <span class="arb-card-lbl">Scratch Craft Cost</span>
          <span class="arb-card-val">${formatCopper(rep.craft_from_scratch_total)}</span>
        </div>
        <div class="arb-card" style="border-color: var(--leather-gold); background: rgba(200, 150, 62, 0.08);">
          <span class="arb-card-lbl" style="color: var(--leather-gold); font-weight: bold;">My Account Craft Cost</span>
          <span class="arb-card-val" style="font-weight: bold;">${formatCopper(rep.my_account_craft_cost)}</span>
        </div>
      </div>

      <div class="tax-breakdown-box">
        <div style="font-family: var(--font-head); font-weight: 700; color: var(--ink-dark); text-transform: uppercase;">
          Wallace's 15% TP Tax Liquidation Model
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span style="color: var(--ink-soft);">TP Gross Liquidation:</span>
          <span>${formatCopper(rep.buy_order_total)}</span>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span style="color: var(--ink-soft);">Wallace 15% TP Tax (10% + 5% listing):</span>
          <span>-${formatCopper(Math.round(rep.buy_order_total * 0.15))}</span>
        </div>
        <div style="display: flex; justify-content: space-between; border-top: 1px dotted var(--parch-line); padding-top: 3px;">
          <span style="color: var(--ink-dark); font-weight: bold;">Net Payout If Sold:</span>
          <span style="font-weight: bold;">${formatCopper(rep.net_sell_if_sold)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; border-top: 1px solid var(--parch-line); padding-top: 3px; font-size: 0.85rem;">
          <span style="font-weight: bold;">Net Profit Margin (vs Scratch):</span>
          <span style="font-weight: bold; color: ${marginColor};">${marginSign}${formatCopper(marginVal)}</span>
        </div>
      </div>
    `;
  }

  function renderArbitrageRightContent() {
    if (!arbitrageData) {
      return `<div style="text-align: center; padding: 20px; color: var(--ink-soft); font-family: var(--font-hand); font-size: 1.1rem;">Component breakdown will appear upon evaluation.</div>`;
    }
    const rep = arbitrageData;
    const prec = rep.precursor_strategy || {};
    const clover = rep.clover_strategy || {};

    let t6Rows = "";
    if (rep.t6_promotion_strategy && Object.keys(rep.t6_promotion_strategy).length > 0) {
      t6Rows = Object.entries(rep.t6_promotion_strategy).slice(0, 4).map(([name, info]) => {
        const isPromote = info.recommended_option === "PROMOTE_T5_FORGE";
        const badgeStyle = isPromote ? "background: #e8f5e9; color: #2e7d32;" : "background: #e3f2fd; color: #1565c0;";
        return `
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.76rem; border-bottom: 1px dotted var(--parch-line); padding: 2px 0;">
            <span>${escapeHtml(name)}</span>
            <span style="${badgeStyle} padding: 1px 5px; border-radius: 3px; font-weight: 600;">${isPromote ? 'Promote T5 Forge' : 'Buy Direct TP'}</span>
          </div>
        `;
      }).join("");
    }

    return `
      <div class="task-item-card" style="margin-bottom: 6px;">
        <div class="task-header-row">
          <span class="task-title">🗡️ Precursor Acquisition</span>
          <span class="task-duration-badge" style="background: var(--leather-gold); color: #fff;">${escapeHtml(prec.recommended_strategy || 'BUY_ORDER')}</span>
        </div>
        <div style="font-size: 0.78rem; color: var(--ink-mid); margin-top: 2px;">
          <strong>Target:</strong> ${escapeHtml(prec.precursor_name || 'Precursor')} ${prec.precursor_id ? `(ID: ${prec.precursor_id})` : ''}
        </div>
        <div style="font-size: 0.78rem; color: var(--ink-soft); line-height: 1.35;">
          ${escapeHtml(prec.details || 'Compare TP buy order vs Grandmaster Craftsman Hobbs collection vs Wizard Vault Starter Kit.')}
        </div>
      </div>

      <div class="task-item-card" style="margin-bottom: 6px;">
        <div class="task-header-row">
          <span class="task-title">🍀 Mystic Clover EV Path</span>
          <span class="task-duration-badge" style="background: #70338a; color: #fff;">${escapeHtml(clover.recommended_strategy || 'WIZARDS_VAULT')}</span>
        </div>
        <div style="font-size: 0.78rem; color: var(--ink-soft); line-height: 1.35; margin-top: 2px;">
          ${escapeHtml(clover.notes || 'Evaluates Mystic Forge recipe expected value (3.2 Mystic Coins + 3.2 Ecto per Clover) vs Fractal BLING-9988 and Astral Acclaim discounted caps.')}
        </div>
      </div>

      ${t6Rows ? `
        <div class="essence-journal-box" style="margin-bottom: 6px; padding: 6px 10px;">
          <div class="essence-journal-title" style="font-size: 0.72rem; margin-bottom: 4px;">T6 Material Promotion Spreads</div>
          ${t6Rows}
        </div>
      ` : ''}

      <div class="tax-breakdown-box" id="opp-cost-widget">
        <div style="font-family: var(--font-head); font-weight: 700; color: var(--ink-dark); font-size: 0.76rem; text-transform: uppercase;">
          Cross-Role Opportunity Cost Analyzer
        </div>
        <div style="display: flex; gap: 6px; align-items: center;">
          <select id="opp-currency-select" class="priory-select" style="font-size: 0.75rem; padding: 4px 6px;">
            <option value="63" ${oppCurrencyId === 63 ? 'selected' : ''}>Astral Acclaim (ID: 63)</option>
            <option value="29" ${oppCurrencyId === 29 ? 'selected' : ''}>Provisioner Token (ID: 29)</option>
            <option value="23" ${oppCurrencyId === 23 ? 'selected' : ''}>Spirit Shards (ID: 23)</option>
            <option value="3" ${oppCurrencyId === 3 ? 'selected' : ''}>Laurels (ID: 3)</option>
            <option value="45" ${oppCurrencyId === 45 ? 'selected' : ''}>Volatile Magic (ID: 45)</option>
          </select>
          <button type="button" class="btn-jump-tool" id="btn-eval-opp" style="white-space: nowrap; padding: 4px 8px;">
            Analyze
          </button>
        </div>
        <div id="opp-results-container" style="font-size: 0.76rem; color: var(--ink-mid);">
          ${renderOppCostResults()}
        </div>
      </div>
    `;
  }

  function renderOppCostResults() {
    if (oppLoading) return "<span>Evaluating cross-role value...</span>";
    if (!oppData) return "<span>Select a currency to evaluate cross-role trade-offs.</span>";
    const d = oppData;
    return `
      <div style="margin-top: 4px; border-top: 1px dotted var(--parch-line); padding-top: 4px;">
        <div>Recommended: <strong style="color: var(--leather-gold);">${escapeHtml(d.optimal_role_disposition || d.recommended_disposition)}</strong></div>
        <div style="display: flex; justify-content: space-between; color: var(--ink-soft);">
          <span>Direct Currency Val: ${d.direct_exchange_value ? formatCopper(d.direct_exchange_value * 10000) : '0g'}</span>
          <span>TP Liquidation: ${formatCopper(d.tp_liquidation_value)}</span>
        </div>
      </div>
    `;
  }

  function attachOpportunityCostListeners() {
    const oppSelect = document.getElementById("opp-currency-select");
    if (oppSelect) {
      oppSelect.addEventListener("change", (e) => {
        oppCurrencyId = parseInt(e.target.value, 10);
      });
    }
    const btnOpp = document.getElementById("btn-eval-opp");
    if (btnOpp) {
      btnOpp.addEventListener("click", () => {
        executeFetchOpportunityCost(oppCurrencyId, oppQuantity);
      });
    }
  }

  async function executeFetchArbitrage(goalId) {
    arbitrageLoading = true;
    const btnText = document.getElementById("btn-arb-text");
    const btnSpinner = document.getElementById("btn-arb-spinner");
    if (btnText) btnText.textContent = "Evaluating Arbitrage Matrix...";
    if (btnSpinner) btnSpinner.classList.remove("hidden");

    try {
      const res = await fetch("/api/solver/arbitrage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal_item_id: goalId })
      });
      const data = await res.json();
      if (data.success && data.arbitrage) {
        arbitrageData = data.arbitrage;
        const leftCont = document.getElementById("arbitrage-left-results");
        if (leftCont) leftCont.innerHTML = renderArbitrageLeftContent();
        const rightCont = document.getElementById("arbitrage-right-results");
        if (rightCont) {
          rightCont.innerHTML = renderArbitrageRightContent();
          attachOpportunityCostListeners();
        }
      } else {
        alert(data.error || "Failed to evaluate arbitrage.");
      }
    } catch (e) {
      console.error("Arbitrage error:", e);
    } finally {
      arbitrageLoading = false;
      if (btnText) btnText.textContent = "Evaluate Multi-Way Arbitrage";
      if (btnSpinner) btnSpinner.classList.add("hidden");
    }
  }

  async function executeFetchOpportunityCost(currencyId, qty) {
    oppLoading = true;
    const oppCont = document.getElementById("opp-results-container");
    if (oppCont) oppCont.innerHTML = renderOppCostResults();

    try {
      const res = await fetch("/api/solver/opportunity-cost", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ currency_id: currencyId, quantity: qty })
      });
      const data = await res.json();
      if (data.success && data.opportunity_cost) {
        oppData = data.opportunity_cost;
        if (oppCont) oppCont.innerHTML = renderOppCostResults();
      }
    } catch (e) {
      console.error("Opportunity cost error:", e);
    } finally {
      oppLoading = false;
      if (oppCont) oppCont.innerHTML = renderOppCostResults();
    }
  }

  // ── CHAPTER IV: PREREQUISITE AUDIT ──────────────────────────────────────────
  function renderPrerequisitesSpread() {
    const goalOptions = renderGoalSelectOptions(prereqGoalId);

    if (leftPageBody) {
      leftPageBody.innerHTML = `
        <div class="runic-header">ᚨ ᚢ ᛞ ᛁ ᛏ ✦ ᚱ ᛖ ᚨ ᛞ ᛁ</div>
        <h2 class="page-title">Chapter IV: Prerequisite Audit</h2>
        <div class="handwritten-subtitle">~ Masteries, Crafting & Collections ~</div>
        <div class="ink-divider">✦</div>

        <div class="inscribe-form">
          <label class="inscribe-label" for="prereq-goal-select">Audit Account for Legendary:</label>
          <select id="prereq-goal-select" class="priory-select">
            ${goalOptions}
          </select>
          <button type="button" class="btn-forge-inscribe" id="btn-run-prereqs" style="margin-top: 6px;">
            <span id="btn-prereq-text">${prereqLoading ? 'Auditing Account Readiness...' : 'Audit Account Prerequisites'}</span>
            <span id="btn-prereq-spinner" class="spinner-ink ${prereqLoading ? '' : 'hidden'}"></span>
          </button>
        </div>

        <div id="prereq-left-results" style="margin-top: 10px;">
          ${renderPrereqLeftContent()}
        </div>
      `;
    }

    if (rightPageBody) {
      rightPageBody.innerHTML = `
        <div class="runic-header">ᛒ ᛚ ᛟ ᚲ ᚲ ᛖ ᚱ ᛊ ✦ ᚱ ᛟ ᚢ ᛏ ᛖ</div>
        <h3 class="page-title">Discipline Routing & Blockers</h3>
        <div class="handwritten-subtitle">~ Zero-Fee Character Assignments ~</div>
        <div class="ink-divider">✦</div>

        <div id="prereq-right-results">
          ${renderPrereqRightContent()}
        </div>
      `;
    }

    const goalSelect = document.getElementById("prereq-goal-select");
    if (goalSelect) {
      goalSelect.addEventListener("change", (e) => {
        prereqGoalId = parseInt(e.target.value, 10);
      });
    }

    const btnRun = document.getElementById("btn-run-prereqs");
    if (btnRun) {
      btnRun.addEventListener("click", () => {
        executeFetchPrerequisites(prereqGoalId);
      });
    }

    if (!prereqData && !prereqLoading) {
      executeFetchPrerequisites(prereqGoalId);
    }
  }

  function renderPrereqLeftContent() {
    if (prereqLoading) {
      return `<div style="text-align: center; padding: 40px;"><span class="spinner-ink" style="width: 28px; height: 28px; border-width: 3px; border-top-color: var(--leather-gold);"></span><div style="margin-top: 10px; font-family: var(--font-head); color: var(--ink-mid);">Auditing Masteries & Prerequisites...</div></div>`;
    }
    if (!prereqData) {
      return `<div style="text-align: center; padding: 20px; color: var(--ink-soft); font-family: var(--font-hand); font-size: 1.1rem;">Select a legendary to audit account masteries and readiness.</div>`;
    }

    const rep = prereqData;
    const canCraft = rep.can_craft_immediately;
    const verdictBanner = canCraft
      ? `<div class="verdict-banner profit">✦ READY TO CRAFT IMMEDIATELY ✦<br><span style="font-size:0.75rem; font-weight:normal;">All Masteries, World Completion & Active Crafting Satisfied</span></div>`
      : `<div class="verdict-banner craft">⚠️ PREREQUISITES PENDING<br><span style="font-size:0.75rem; font-weight:normal;">Account satisfies some conditions but action items remain</span></div>`;

    const worldBadge = rep.has_world_completion ? "pass" : "fail";
    const worldText = rep.has_world_completion ? "Completed" : "Incomplete";

    const craftBadge = rep.active_crafting_ready ? "pass" : "warn";
    const craftText = rep.active_crafting_ready ? "Ready (500)" : "Needs Discipline";

    const masteryBadge = rep.mastery_requirements_met ? "pass" : "warn";
    const masteryText = rep.mastery_requirements_met ? "Satisfied" : "Missing Unlocks";

    const precBits = rep.precursor_collection_bits_total > 0
      ? `${rep.precursor_collection_bits_done} / ${rep.precursor_collection_bits_total}`
      : "Standard";

    return `
      ${verdictBanner}

      <div class="prereq-pillars-grid">
        <div class="pillar-card">
          <div class="pillar-header">
            <span>World Completion</span>
            <span class="pillar-badge ${worldBadge}">${worldText}</span>
          </div>
          <div style="font-size: 0.74rem; color: var(--ink-soft);">
            Source: ${escapeHtml(rep.world_completion_source || 'Map / Gift of Exploration')}
          </div>
        </div>

        <div class="pillar-card">
          <div class="pillar-header">
            <span>Crafting Disciplines</span>
            <span class="pillar-badge ${craftBadge}">${craftText}</span>
          </div>
          <div style="font-size: 0.74rem; color: var(--ink-soft);">
            ${rep.active_crafting_ready ? 'Discipline active at level 500' : 'Switch character or level discipline'}
          </div>
        </div>

        <div class="pillar-card">
          <div class="pillar-header">
            <span>Mastery Tracks</span>
            <span class="pillar-badge ${masteryBadge}">${masteryText}</span>
          </div>
          <div style="font-size: 0.74rem; color: var(--ink-soft);">
            ${rep.missing_masteries?.length > 0 ? `${rep.missing_masteries.length} masteries pending` : 'All masteries acquired'}
          </div>
        </div>

        <div class="pillar-card">
          <div class="pillar-header">
            <span>Precursor Step</span>
            <span class="pillar-badge pass">${precBits}</span>
          </div>
          <div style="font-size: 0.74rem; color: var(--ink-soft);">
            ${escapeHtml(rep.precursor_collection_step || 'Tradeable / Finished')}
          </div>
        </div>
      </div>
    `;
  }

  function renderPrereqRightContent() {
    if (!prereqData) {
      return `<div style="text-align: center; padding: 20px; color: var(--ink-soft); font-family: var(--font-hand); font-size: 1.1rem;">Blockers and character assignments will appear here.</div>`;
    }

    const rep = prereqData;
    let blockersHtml = "";
    if (rep.blockers && rep.blockers.length > 0) {
      blockersHtml = rep.blockers.map(b => `
        <div style="font-size: 0.8rem; color: #c62828; margin-bottom: 4px; display: flex; gap: 6px;">
          <span>⛔</span> <span>${escapeHtml(b)}</span>
        </div>
      `).join("");
    } else {
      blockersHtml = `<div style="font-size: 0.82rem; color: #2e7d32; font-style: italic;">✨ Zero hard blockers! All prerequisite requirements are met.</div>`;
    }

    let routingHtml = "";
    if (rep.crafting_assignment_recommendations && rep.crafting_assignment_recommendations.length > 0) {
      routingHtml = rep.crafting_assignment_recommendations.map(r => `
        <div class="task-item-card" style="margin-bottom: 4px; padding: 6px 8px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
            <strong>${escapeHtml(r.gift_or_component || r.gift || 'Gift')}</strong>
            <span style="color: var(--leather-gold); font-weight: bold;">${escapeHtml(r.character_name || r.recommended_character || 'Kerling')}</span>
          </div>
          <div style="font-size: 0.74rem; color: var(--ink-soft);">
            Discipline: ${escapeHtml(r.discipline || 'Weaponsmith')} (Rating: ${r.current_rating || 500})
          </div>
        </div>
      `).join("");
    } else if (rep.character_discipline_assignments && Object.keys(rep.character_discipline_assignments).length > 0) {
      routingHtml = Object.entries(rep.character_discipline_assignments).map(([charName, discInfo]) => `
        <div class="task-item-card" style="margin-bottom: 4px; padding: 6px 8px;">
          <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
            <strong>${escapeHtml(charName)}</strong>
            <span style="color: var(--leather-gold); font-weight: bold;">Level ${discInfo.rating || 500}</span>
          </div>
          <div style="font-size: 0.74rem; color: var(--ink-soft);">
            Discipline: ${escapeHtml(discInfo.discipline || 'Crafting')}
          </div>
        </div>
      `).join("");
    } else {
      routingHtml = `<div style="font-size: 0.8rem; color: var(--ink-soft);">No character discipline reassignments needed.</div>`;
    }

    return `
      <div class="essence-journal-box" style="margin-bottom: 8px;">
        <div class="essence-journal-title" style="color: #c62828;">Active Crafting Blockers</div>
        ${blockersHtml}
      </div>

      <div class="essence-journal-box" style="margin-bottom: 8px;">
        <div class="essence-journal-title">Multi-Alt Discipline Routing (Avoid 50s Fee)</div>
        ${routingHtml}
      </div>

      ${rep.missing_masteries && rep.missing_masteries.length > 0 ? `
        <div class="essence-journal-box">
          <div class="essence-journal-title" style="color: var(--leather-gold);">Missing Masteries</div>
          <ul style="padding-left: 16px; font-size: 0.78rem; color: var(--ink-mid);">
            ${rep.missing_masteries.map(m => `<li>${escapeHtml(m)}</li>`).join("")}
          </ul>
        </div>
      ` : ''}
    `;
  }

  async function executeFetchPrerequisites(goalId) {
    prereqLoading = true;
    const btnText = document.getElementById("btn-prereq-text");
    const btnSpinner = document.getElementById("btn-prereq-spinner");
    if (btnText) btnText.textContent = "Auditing Account Readiness...";
    if (btnSpinner) btnSpinner.classList.remove("hidden");

    const leftCont = document.getElementById("prereq-left-results");
    if (leftCont) leftCont.innerHTML = renderPrereqLeftContent();

    try {
      const res = await fetch("/api/solver/prerequisites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal_item_id: goalId })
      });
      const data = await res.json();
      if (data.success && data.prerequisites) {
        prereqData = data.prerequisites;
        if (leftCont) leftCont.innerHTML = renderPrereqLeftContent();
        const rightCont = document.getElementById("prereq-right-results");
        if (rightCont) rightCont.innerHTML = renderPrereqRightContent();
      } else {
        alert(data.error || "Failed to audit prerequisites.");
      }
    } catch (e) {
      console.error("Prerequisites audit error:", e);
    } finally {
      prereqLoading = false;
      if (btnText) btnText.textContent = "Audit Account Prerequisites";
      if (btnSpinner) btnSpinner.classList.add("hidden");
      if (leftCont && !prereqData) leftCont.innerHTML = renderPrereqLeftContent();
    }
  }

  // ── CHAPTER I: QUERY SUBMISSION ─────────────────────────────────────────────
  async function executeNewQuery(query) {
    const btnSubmit = document.getElementById("btn-forge-submit");
    const btnText = document.getElementById("btn-forge-text");
    const btnSpinner = document.getElementById("btn-forge-spinner");

    if (btnSubmit) {
      btnSubmit.disabled = true;
      if (btnText) btnText.classList.add("hidden");
      if (btnSpinner) btnSpinner.classList.remove("hidden");
    }

    if (bookAura) {
      bookAura.classList.add("casting");
    }

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
          turnPageTo(4 + existingIdx, "forward");
        } else {
          savedRecipes.push(data.guide);
          saveRecipesToStorage();
          turnPageTo(4 + savedRecipes.length - 1, "forward");
        }
      } else {
        alert(data.error || "The Priory could not resolve this recipe.");
      }
    } catch (err) {
      alert("Arcane connection error: " + err.message);
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        if (btnText) btnText.classList.remove("hidden");
        if (btnSpinner) btnSpinner.classList.add("hidden");
      }
      if (bookAura) {
        bookAura.classList.remove("casting");
      }
    }
  }

  // ── Formatting & Chat Code Copy Helpers ─────────────────────────────────────
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
    if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(code).catch(() => {});
    }
    
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

  // ── Ambient Arcane Canvas Particles ────────────────────────────────────────
  function initParticles() {
    const c = document.getElementById("particles");
    if (!c || typeof c.getContext !== "function") return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
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
      if (typeof requestAnimationFrame === "function") {
        requestAnimationFrame(frame);
      }
    })();
  }
  
  // ── Tooltip Delegation ──────────────────────────────────────────────────────
  function initTooltipDelegation() {
    if (!gw2Tooltip) {
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
      if (el && el.classList && el.classList.contains("has-tooltip")) {
        const dataStr = el.getAttribute("data-tooltip");
        if (dataStr) {
          try {
            const data = JSON.parse(dataStr);
            showGw2Tooltip(el, data, e);
          } catch(err) {}
        }
      }
    }, true);
    
    document.addEventListener("mousemove", (e) => {
      const el = e.target;
      if (el && el.classList && el.classList.contains("has-tooltip")) {
        if (gw2Tooltip && gw2Tooltip.style.display !== "none") {
          let x = e.clientX + 15;
          let y = e.clientY + 10;
          const rect = gw2Tooltip.getBoundingClientRect();
          if (x + rect.width > window.innerWidth) x = window.innerWidth - rect.width - 10;
          if (y + rect.height > window.innerHeight) y = window.innerHeight - rect.height - 10;
          gw2Tooltip.style.left = x + "px";
          gw2Tooltip.style.top = y + "px";
        }
      }
    }, true);
    
    document.addEventListener("mouseleave", (e) => {
      const el = e.target;
      if (el && el.classList && el.classList.contains("has-tooltip")) {
        if (gw2Tooltip) gw2Tooltip.style.display = "none";
      }
    }, true);
  }

  function showGw2Tooltip(el, data, e) {
    if (!gw2Tooltip) return;
    
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
    gw2Tooltip.style.left = x + "px";
    gw2Tooltip.style.top = y + "px";
  }

});
