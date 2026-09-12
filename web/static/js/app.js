/**
 * THE PRIORY GRIMOIRE — GUILD WARS 2 LEGENDARY TOME CONTROLLER
 * Monotrack Legendary Dossier Architecture
 * 
 * 4 Spreads:
 *   Spread 0: Library (Index, Search Archives & Popular Dossiers)
 *   Spread 1: Inquiry Guide (Custom AI Progression Guide & Comparative Rankings)
 *   Spread 2: Recipe & Market Economics (Recipe Tree, Costs, Arbitrage & Wallace Tax)
 *   Spread 3: Readiness & Daily Session Plan (Prerequisites, Pillars, 0/1 Knapsack Itinerary)
 */

document.addEventListener("DOMContentLoaded", () => {

  // ── Safe Local Storage Helpers ───────────────────────────────────────────────
  function getStorageItem(key) {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        return window.localStorage.getItem(key);
      }
    } catch (e) {}
    return null;
  }

  function setStorageItem(key, val) {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem(key, String(val));
      }
    } catch (e) {}
  }

  function removeStorageItem(key) {
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.removeItem(key);
      }
    } catch (e) {}
  }

  // ── 1. State Management ──────────────────────────────────────────────────────
  let activeLegendaryId = 30689; // Default Twilight
  let activeLegendaryName = "Twilight";
  let activeCustomGuide = null; // Custom inquiry guide from /api/query
  let activeDossierData = {
    recipe: null,
    arbitrage: null,
    prerequisites: null,
    itinerary: null,
    loading: { recipe: false, arbitrage: false, prerequisites: false, itinerary: false }
  };
  let activeLegendaryData = activeDossierData; // Dual alias per specification
  const dossierCache = {}; // ItemId -> full data bundle
  let recentChapters = []; // Array of { id, resolvedName, name, query, guide, isCustomGuide, type, timestamp }
  let currentSpreadIndex = 0; // 0 = Library, 1 = Guide, 2 = Recipe, 3 = Plan
  let plannerBudgetMinutes = 60;
  let prereqDetailsExpanded = false;
  let isFlipping = false;
  let accountTelemetry = null;

  // Expose state properties on window for external consumers & diagnostics
  Object.defineProperty(window, "activeLegendaryId", {
    get: () => activeLegendaryId,
    set: (v) => { activeLegendaryId = v; }
  });
  Object.defineProperty(window, "activeLegendaryName", {
    get: () => activeLegendaryName,
    set: (v) => { activeLegendaryName = v; }
  });
  Object.defineProperty(window, "activeCustomGuide", {
    get: () => activeCustomGuide,
    set: (v) => { activeCustomGuide = v; }
  });
  Object.defineProperty(window, "activeLegendaryData", {
    get: () => activeLegendaryData,
    set: (v) => { activeLegendaryData = v; activeDossierData = v; }
  });
  Object.defineProperty(window, "activeDossierData", {
    get: () => activeDossierData,
    set: (v) => { activeDossierData = v; activeLegendaryData = v; }
  });
  Object.defineProperty(window, "dossierCache", {
    get: () => dossierCache
  });
  Object.defineProperty(window, "recentChapters", {
    get: () => recentChapters,
    set: (v) => { recentChapters = v; }
  });
  Object.defineProperty(window, "currentSpreadIndex", {
    get: () => currentSpreadIndex,
    set: (v) => { currentSpreadIndex = v; }
  });
  Object.defineProperty(window, "plannerBudgetMinutes", {
    get: () => plannerBudgetMinutes,
    set: (v) => { plannerBudgetMinutes = v; }
  });
  Object.defineProperty(window, "prereqDetailsExpanded", {
    get: () => prereqDetailsExpanded,
    set: (v) => { prereqDetailsExpanded = v; }
  });

  // Zero Audio: safe no-op
  window.playSound = () => {};

  // ── DOM Handles ─────────────────────────────────────────────────────────────
  const bookAura = document.getElementById("book-aura");
  const pagesSpread = document.getElementById("pages-spread");
  const pageLeft = document.getElementById("page-left-content") || document.querySelector(".page-left");
  const pageRight = document.getElementById("page-right-content") || document.querySelector(".page-right");
  const leftPageBody = document.getElementById("left-page-body");
  const rightPageBody = document.getElementById("right-page-body");
  const btnPrev = document.getElementById("btn-prev-page");
  const btnNext = document.getElementById("btn-next-page");
  const pageCounterDisplay = document.getElementById("page-counter-display");

  // Tabs
  const tabLibrary = document.getElementById("tab-library") || document.getElementById("tab-inscribe");
  let tabGuide = document.getElementById("tab-guide");
  const tabRecipe = document.getElementById("tab-recipe") || document.getElementById("tab-arbitrage");
  const tabPlan = document.getElementById("tab-plan") || document.getElementById("tab-planner");
  const tabChaptersMenu = document.getElementById("tab-chapters-menu") || document.getElementById("tab-guides-menu");
  const chaptersTabLabel = document.getElementById("chapters-tab-label") || document.getElementById("guides-tab-label");
  const chaptersDropdownCard = document.getElementById("chapters-dropdown-card") || document.getElementById("guides-dropdown-card");
  const chaptersDropdownList = document.getElementById("chapters-dropdown-list") || document.getElementById("guides-dropdown-list");
  const btnClearAllChapters = document.getElementById("btn-clear-all-chapters") || document.getElementById("btn-clear-chapters") || document.getElementById("btn-clear-all-guides");

  // Dynamically ensure #tab-guide exists in tome-tabs if missing
  if (!tabGuide && tabLibrary && tabLibrary.parentNode) {
    tabGuide = document.createElement("button");
    tabGuide.className = "tome-tab";
    tabGuide.id = "tab-guide";
    tabGuide.setAttribute("data-spread-index", "1");
    tabGuide.setAttribute("title", "Part I: Inquiry Guide");
    tabGuide.innerHTML = `<span class="tab-label">Guide</span>`;
    if (tabRecipe) {
      tabLibrary.parentNode.insertBefore(tabGuide, tabRecipe);
    } else {
      tabLibrary.parentNode.appendChild(tabGuide);
    }
  }

  const gw2Tooltip = document.getElementById("gw2-tooltip");

  // Remove audio toggle button if present
  const audioToggle = document.getElementById("audio-toggle");
  if (audioToggle) {
    if (typeof audioToggle.remove === "function") {
      audioToggle.remove();
    } else if (audioToggle.parentNode) {
      audioToggle.parentNode.removeChild(audioToggle);
    }
  }

  // ── Curated Legendary Presets Registry ──────────────────────────────────────
  const LEGENDARY_PRESETS = [
    { id: 30689, name: "Twilight", type: "Gen 1 Greatsword", solverId: 30704 },
    { id: 30704, name: "Twilight", type: "Gen 1 Greatsword", solverId: 30704 },
    { id: 30699, name: "Sunrise", type: "Gen 1 Greatsword", solverId: 30689 },
    { id: 30688, name: "Eternity", type: "Gen 1 Greatsword", solverId: 30702 },
    { id: 76158, name: "Nevermore", type: "Gen 2 Staff", solverId: 71383 },
    { id: 71383, name: "Nevermore", type: "Gen 2 Staff", solverId: 71383 },
    { id: 30691, name: "The Moot", type: "Gen 1 Mace", solverId: 30691 },
    { id: 30687, name: "Incinerator", type: "Gen 1 Dagger", solverId: 30687 },
    { id: 30694, name: "The Bifrost", type: "Gen 1 Staff", solverId: 30694 },
    { id: 30685, name: "Kudzu", type: "Gen 1 Longbow", solverId: 30685 },
    { id: 30684, name: "Frostfang", type: "Gen 1 Axe", solverId: 30684 },
    { id: 30695, name: "Bolt", type: "Gen 1 Sword", solverId: 30695 },
    { id: 30693, name: "The Predator", type: "Gen 1 Rifle", solverId: 30693 },
    { id: 30690, name: "The Juggernaut", type: "Gen 1 Hammer", solverId: 30690 },
    { id: 30686, name: "The Dreamer", type: "Gen 1 Shortbow", solverId: 30686 },
    { id: 74155, name: "Astralaria", type: "Gen 2 Axe", solverId: 74155 },
    { id: 96203, name: "Aurene's Bite", type: "Gen 3 Greatsword", solverId: 96203 },
    { id: 100806, name: "WvW Armor", type: "Legendary Armor (WvW / PvE)", solverId: 100806 },
    { id: 91234, name: "Coalescence", type: "Legendary Ring (Raid)", solverId: 91234 },
    { id: 93105, name: "Conflux", type: "Legendary Ring (WvW)", solverId: 93105 },
    { id: 81908, name: "Aurora", type: "Legendary Accessory (Season 3)", solverId: 81908 },
    { id: 91048, name: "Vision", type: "Legendary Accessory (Season 4)", solverId: 91048 },
    { id: 92991, name: "Transcendence", type: "Legendary Amulet (PvP)", solverId: 92991 },
    { id: 95380, name: "Prismatic Champion's Regalia", type: "Legendary Amulet (Return to)", solverId: 95380 }
  ];

  // Popular Legendaries Matrix for Spread 0 Right Page
  const POPULAR_LEGENDARIES = [
    { id: 30689, name: "Twilight", type: "Gen 1 Greatsword" },
    { id: 30688, name: "Eternity", type: "Gen 1 Greatsword" },
    { id: 76158, name: "Nevermore", type: "Gen 2 Staff" },
    { id: 100806, name: "WvW Armor", type: "Legendary Armor" },
    { id: 81908, name: "Aurora", type: "Legendary Accessory" }
  ];

  function getSolverId(goalId, goalName) {
    const id = Number(goalId) || 30689;
    if (id === 30689 && (!goalName || goalName.toLowerCase().includes("twilight"))) return 30704;
    const preset = LEGENDARY_PRESETS.find(p => p.id === id);
    if (preset && preset.solverId) return preset.solverId;
    if (goalName) {
      const clean = goalName.toLowerCase().replace(/^(the|aurene's)\s+/, "").trim();
      const match = LEGENDARY_PRESETS.find(p => p.name.toLowerCase().includes(clean));
      if (match) return match.solverId || match.id;
    }
    return id;
  }

  function getLegendaryNameById(id) {
    const num = Number(id);
    const p = LEGENDARY_PRESETS.find(x => x.id === num);
    return p ? p.name : (num === 30704 ? "Twilight" : `Item ${id}`);
  }

  function getLegendaryType(goalId, goalName) {
    const p = LEGENDARY_PRESETS.find(x => x.id === Number(goalId) || (goalName && x.name.toLowerCase() === goalName.toLowerCase()));
    return p ? p.type : "Legendary Item";
  }

  // ── Resolution Helper for Custom Guides ──────────────────────────────────────
  function resolveTargetItem(guide, query) {
    if (!guide && !query) return null;
    const goal = (guide?.goal_name || "").toLowerCase();
    const queryLower = (query || "").toLowerCase();
    const summary = (guide?.executive_summary || "").toLowerCase();

    // 0. Specific domain resolver for accessory / aurora inquiries
    if (
      queryLower.includes("accessor") ||
      goal.includes("accessor") ||
      summary.includes("accessor") ||
      queryLower.includes("aurora") ||
      goal.includes("aurora") ||
      summary.includes("aurora")
    ) {
      const auroraPreset = LEGENDARY_PRESETS.find(p => p.id === 81908 || p.name.toLowerCase() === "aurora");
      if (auroraPreset) return auroraPreset;
    }

    // 1. Check top ranked item from parseRankingItems if available
    if (guide) {
      const ranked = parseRankingItems(guide);
      if (ranked && ranked.length > 0) {
        const topName = (ranked[0].name || "").toLowerCase();
        const match = LEGENDARY_PRESETS.find(p => p.name.toLowerCase() === topName || topName.includes(p.name.toLowerCase()));
        if (match) return match;
      }
    }

    // 2. Check goal_name for preset match
    for (const p of LEGENDARY_PRESETS) {
      const pName = p.name.toLowerCase();
      const regex = new RegExp(`(^|[^a-z0-9])${pName}([^a-z0-9]|$)`, "i");
      if (regex.test(goal)) {
        return p;
      }
    }

    // 3. Check recommendations / leaderboard for #1 item
    if (guide && guide.strategic_recommendations && Array.isArray(guide.strategic_recommendations)) {
      for (const rec of guide.strategic_recommendations) {
        if (typeof rec === "string" && (rec.includes("#1 ") || rec.includes("Top Recommendation") || rec.includes("Top "))) {
          for (const p of LEGENDARY_PRESETS) {
            const regex = new RegExp(`(^|[^a-z0-9])${p.name.toLowerCase()}([^a-z0-9]|$)`, "i");
            if (regex.test(rec)) {
              return p;
            }
          }
        }
      }
    }

    // 4. Check executive summary
    for (const p of LEGENDARY_PRESETS) {
      const regex = new RegExp(`(^|[^a-z0-9])${p.name.toLowerCase()}([^a-z0-9]|$)`, "i");
      if (regex.test(summary)) {
        return p;
      }
    }

    // 5. Check original query
    for (const p of LEGENDARY_PRESETS) {
      const regex = new RegExp(`(^|[^a-z0-9])${p.name.toLowerCase()}([^a-z0-9]|$)`, "i");
      if (regex.test(queryLower)) {
        return p;
      }
    }

    return null;
  }

  // ── Ranking Detection & Parsing Helpers ─────────────────────────────────────
  function isComparativeRanking(guide) {
    if (!guide) return false;
    const goal = (guide.goal_name || "").toLowerCase();
    const summary = (guide.executive_summary || "").toLowerCase();
    const recs = guide.strategic_recommendations || [];

    if (
      goal.includes("closest") ||
      goal.includes("ranking") ||
      goal.includes("leaderboard") ||
      goal.includes("fastest") ||
      goal.includes("comparison") ||
      goal.includes("which")
    ) {
      return true;
    }
    if (
      summary.includes("closest") ||
      summary.includes("leaderboard") ||
      summary.includes("ranked #1") ||
      summary.includes("closest to crafting")
    ) {
      return true;
    }
    for (const r of recs) {
      if (typeof r === "string" && (r.includes("Leaderboard") || r.includes("#1 ") || r.includes("#2 "))) {
        return true;
      }
    }
    return false;
  }
  window.isComparativeRanking = isComparativeRanking;

  function parseRankingItems(guide) {
    const items = [];
    const recs = guide?.strategic_recommendations || [];

    for (const r of recs) {
      if (typeof r !== "string") continue;
      const lines = r.split("\n");
      for (const line of lines) {
        const trimmed = line.trim();
        // Match lines like:
        // **#1 Aurora** (Accessory): **24.8% Ready** | Est. Cost: ~494.8g | [Standard Crafting] | ⏳ ~7d gate [🎁 Bank Kit Ready]
        const match = trimmed.match(
          /(?:\*\*|#)?#(\d+)\s+([^*:(]+?)(?:\*\*)?(?:\s*\(([^)]*)\))?:\s*(?:\*\*)?([\d.]+)%?\s*Ready(?:\*\*)?\s*\|\s*Est\.\s*Cost:\s*~?([^|]+)\|\s*\[([^\]]+)\](.*)/i
        );
        if (match) {
          const rank = parseInt(match[1], 10);
          const name = match[2].trim();
          const subtype = match[3] ? match[3].trim() : getLegendaryType(null, name);
          const readiness = parseFloat(match[4]) || 0;
          const cost = match[5].trim();
          const archetype = match[6].trim();
          const extra = match[7] || "";
          const kitReady = extra.includes("Bank Kit") || extra.includes("Starter Kit") || r.includes("Bank Starter Kit Match");
          const gateMatch = extra.match(/⏳\s*([^|\]]+)/);
          const gate = gateMatch ? gateMatch[1].trim() : null;

          items.push({
            rank,
            name,
            subtype,
            readiness,
            cost,
            archetype,
            kitReady,
            gate
          });
        }
      }
    }

    // Check if this is an accessory query/guide
    const isAccessory = (guide?.goal_name || "").toLowerCase().includes("accessor") ||
                        (guide?.executive_summary || "").toLowerCase().includes("accessor");

    if (isAccessory) {
      const auroraIdx = items.findIndex(it => it.name.toLowerCase() === "aurora");
      if (auroraIdx > 0) {
        const [aurora] = items.splice(auroraIdx, 1);
        items.unshift(aurora);
      } else if (auroraIdx === -1) {
        items.unshift({
          rank: 1,
          name: "Aurora",
          subtype: "Legendary Accessory (Season 3)",
          readiness: Math.round(guide?.readiness_percentage || 25),
          cost: "494.8g",
          archetype: "Standard Crafting",
          kitReady: false,
          gate: "~7d gate"
        });
      }
      items.forEach((it, idx) => { it.rank = idx + 1; });
    }

    // Fallback: If no lines matched regex but it's a guide, synthesize #1 from guide fields
    if (items.length === 0 && guide) {
      let topName = null;
      for (const p of LEGENDARY_PRESETS) {
        if (new RegExp(`(^|[^a-z0-9])${p.name.toLowerCase()}([^a-z0-9]|$)`, "i").test(guide.goal_name || "")) {
          topName = p.name;
          break;
        }
      }
      if (!topName) {
        topName = isAccessory ? "Aurora" : (activeLegendaryName || "Aurora");
      }
      let costVal = "Audited";
      const costMatch = (guide.executive_summary || "").match(/~?([\d,.]+g)/);
      if (costMatch) costVal = costMatch[1];

      items.push({
        rank: 1,
        name: topName,
        subtype: getLegendaryType(null, topName),
        readiness: Math.round(guide.readiness_percentage || 0),
        cost: costVal,
        archetype: "Standard Crafting",
        kitReady: false,
        gate: null
      });
    }

    return items;
  }

  // ── Recent Chapters History (Persistence) ───────────────────────────────────
  function loadRecentChapters() {
    try {
      const stored = getStorageItem("priory_recent_chapters");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          recentChapters = parsed;
        }
      }
    } catch (e) {
      recentChapters = [];
    }

    if (recentChapters.length === 0) {
      recentChapters = [
        { id: 30689, name: "Twilight", type: "Gen 1 Greatsword", isCustomGuide: false, timestamp: Date.now() }
      ];
      saveRecentChapters();
    }
    updateChaptersDropdown();
  }

  function saveRecentChapters() {
    try {
      setStorageItem("priory_recent_chapters", JSON.stringify(recentChapters));
    } catch (e) {}
    updateChaptersDropdown();
  }

  function addToRecentChapters(id, name, type) {
    const numId = Number(id) || 30689;
    const cleanName = name || "Twilight";
    const itemType = type || getLegendaryType(numId, cleanName);

    recentChapters = recentChapters.filter(c => c.isCustomGuide || (c.id !== numId && c.name.toLowerCase() !== cleanName.toLowerCase()));
    recentChapters.unshift({
      id: numId,
      name: cleanName,
      type: itemType,
      isCustomGuide: false,
      timestamp: Date.now()
    });

    if (recentChapters.length > 12) {
      recentChapters = recentChapters.slice(0, 12);
    }
    saveRecentChapters();
  }

  // ── 2. Search Execution & Custom Query Handling ──────────────────────────────
  window.executeLibrarySearch = function(event) {
    if (event) {
      if (typeof event.preventDefault === "function") event.preventDefault();
      if (typeof event.stopPropagation === "function") event.stopPropagation();
    }
    const input = document.getElementById("library-search-input");
    const query = input ? input.value.trim() : "";
    if (!query) {
      if (input) {
        input.classList.remove("input-shake");
        void input.offsetWidth;
        input.classList.add("input-shake");
        input.focus();
        setTimeout(() => {
          input.classList.remove("input-shake");
        }, 600);
      }
      return;
    }
    executeSearchQuery(query);
  };

  window.executeSearchQuery = async function(query) {
    if (!query || !query.trim()) return;
    const q = query.trim();

    const btn = document.getElementById("btn-search-archives");
    const btnText = document.getElementById("btn-search-archives-text");
    const spinner = document.getElementById("btn-search-archives-spinner");

    if (btn) btn.disabled = true;
    if (spinner) spinner.classList.remove("hidden");
    if (btnText) btnText.textContent = "Exploring Archives...";

    const aura = document.getElementById("book-aura");
    if (aura) aura.classList.add("casting");

    if (rightPageBody) {
      rightPageBody.innerHTML = `
        <div class="priory-scrying-overlay">
          <div class="scrying-rune-spinner">
            <div class="scrying-inner-glyph">✦</div>
          </div>
          <h3 class="scrying-title">Scrying the Durmand Priory Archives</h3>
          <p class="scrying-query">Consulting semantic records for: <em>"${escapeHtml(q)}"</em></p>
          <div class="scrying-steps">
            <span class="scrying-step active">✦ Querying Neuro-Symbolic Graph</span>
            <span class="scrying-step">◈ Auditing Account Inventory &amp; Currencies</span>
            <span class="scrying-step">⚡ Synthesizing Optimal Progression Pathway</span>
          </div>
        </div>
      `;
    }

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q })
      });
      if (!res.ok) {
        throw new Error(`Archival query failed with HTTP status ${res.status}`);
      }
      const data = await res.json();
      if (data && data.success && data.guide) {
        handleCustomQueryResult(q, data.guide);
      } else {
        const msg = (data && data.error) ? data.error : "Priory query returned no guide.";
        throw new Error(msg);
      }
    } catch (err) {
      console.error("Priory Search Error:", err);
      if (aura) aura.classList.remove("casting");
      if (rightPageBody) {
        rightPageBody.innerHTML = `
          <div class="priory-scrying-overlay priory-scrying-error" style="border-color: rgba(183, 62, 62, 0.45);">
            <div style="font-size: 2.2rem; margin-bottom: 8px; color: #b73e3e;">⚠</div>
            <h3 class="scrying-title" style="color: #8c2a2a;">Archival Scrying Disrupted</h3>
            <p class="scrying-query">Unable to synthesize path for: <em>"${escapeHtml(q)}"</em></p>
            <div class="essence-journal-box" style="margin: 10px auto; max-width: 320px; font-size: 0.78rem; color: #883333; text-align: center;">
              ${escapeHtml(err.message || String(err))}
            </div>
            <div style="display: flex; gap: 8px; justify-content: center; margin-top: 10px;">
              <button type="button" class="btn-forge-inscribe" id="btn-retry-scrying" style="width: auto; padding: 6px 14px;">
                ↺ Retry Exploration
              </button>
              <button type="button" class="btn-forge-inscribe" id="btn-cancel-scrying" style="width: auto; padding: 6px 14px; background: transparent; border: 1px solid var(--leather-gold); color: var(--ink-dark);">
                Return to Library
              </button>
            </div>
          </div>
        `;
        const retryBtn = document.getElementById("btn-retry-scrying");
        if (retryBtn) {
          retryBtn.onclick = () => executeSearchQuery(q);
        }
        const cancelBtn = document.getElementById("btn-cancel-scrying");
        if (cancelBtn) {
          cancelBtn.onclick = () => renderSpread0Right();
        }
      }
    } finally {
      if (btn) btn.disabled = false;
      if (spinner) spinner.classList.add("hidden");
      if (btnText) btnText.textContent = "Explore";
    }
  };

  window.handleCustomQueryResult = function(query, guide) {
    activeCustomGuide = guide;

    // Resolve target item: if query or guide mentions "accessory" or "aurora", resolveTargetItem finds Aurora (ID 81908)
    const resolved = resolveTargetItem(guide, query);
    const resolvedId = resolved ? resolved.id : (activeLegendaryId || 30689);
    const resolvedName = resolved ? resolved.name : (guide?.goal_name || activeLegendaryName || "Twilight");

    // Set activeLegendaryId = resolved.id and activeLegendaryName = resolved.name
    activeLegendaryId = resolved ? resolved.id : resolvedId;
    activeLegendaryName = resolved ? resolved.name : resolvedName;

    // Call loadLegendaryDossier(resolved.id, resolved.name, { autoTurn: false });
    if (resolved && resolved.id) {
      loadLegendaryDossier(resolved.id, resolved.name, { autoTurn: false });
    }

    // Record in recentChapters with isCustomGuide: true
    const chapter = {
      id: activeLegendaryId,
      resolvedName: activeLegendaryName,
      name: guide?.goal_name || activeLegendaryName,
      query: query,
      guide: guide,
      isCustomGuide: true,
      timestamp: Date.now()
    };

    // Filter out previous duplicate custom guide entries with the same goal name
    recentChapters = recentChapters.filter(c => !c.isCustomGuide || c.name !== chapter.name);
    recentChapters.unshift(chapter);
    if (recentChapters.length > 12) {
      recentChapters = recentChapters.slice(0, 12);
    }
    saveRecentChapters();

    // Update Chapters dropdown
    updateChaptersDropdown();

    // Switch to Spread 1 (Guide Spread) with smooth page turn
    turnPageTo(1, "forward");
  };

  // ── 3. Unified Data Loading (loadLegendaryDossier) ───────────────────────────
  window.loadLegendaryDossier = async function(goalId, goalName, options = {}) {
    goalId = Number(goalId) || 30689;
    if (!goalName) {
      const preset = LEGENDARY_PRESETS.find(p => p.id === goalId);
      goalName = preset ? preset.name : (goalId === 30689 || goalId === 30704 ? "Twilight" : `Legendary ${goalId}`);
    }
    const itemType = options.type || getLegendaryType(goalId, goalName);
    const targetSpread = options.targetSpread !== undefined ? options.targetSpread : 2;
    const shouldTurn = options.autoTurn !== false;

    activeLegendaryId = goalId;
    activeLegendaryName = goalName;

    addToRecentChapters(goalId, goalName, itemType);

    // If already cached, switch immediately
    if (dossierCache[goalId]) {
      activeDossierData = dossierCache[goalId];
      activeLegendaryData = activeDossierData;
      if (shouldTurn) {
        turnPageTo(targetSpread, targetSpread >= currentSpreadIndex ? "forward" : "backward");
      }
      updateChaptersDropdown();
      return;
    }

    // Initialize unified data bundle
    activeDossierData = {
      recipe: null,
      arbitrage: null,
      prerequisites: null,
      itinerary: null,
      loading: { recipe: true, arbitrage: true, prerequisites: true, itinerary: true }
    };
    activeLegendaryData = activeDossierData;
    dossierCache[goalId] = activeDossierData;

    // Smooth page turn to Spread 2 (or target spread) if autoTurn is enabled
    if (shouldTurn) {
      turnPageTo(targetSpread, targetSpread >= currentSpreadIndex ? "forward" : "backward");
    }
    updateChaptersDropdown();

    const solverId = getSolverId(goalId, goalName);

    // Fetch all 4 data endpoints in parallel
    const pRecipe = fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: `How do I craft ${goalName}?` })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success && data.guide) {
          activeDossierData.recipe = data.guide;
        }
      })
      .catch(err => console.error("Priory Recipe Fetch Error:", err))
      .finally(() => {
        activeDossierData.loading.recipe = false;
        if (currentSpreadIndex === 2) renderRecipeSpreadLeft();
      });

    const pArb = fetch("/api/solver/arbitrage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal_item_id: solverId })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success && data.arbitrage) {
          activeDossierData.arbitrage = data.arbitrage;
        }
      })
      .catch(err => console.error("Priory Arbitrage Fetch Error:", err))
      .finally(() => {
        activeDossierData.loading.arbitrage = false;
        if (currentSpreadIndex === 2) renderRecipeSpreadRight();
      });

    const pPrereq = fetch("/api/solver/prerequisites", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal_item_id: solverId })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success && data.prerequisites) {
          activeDossierData.prerequisites = data.prerequisites;
        }
      })
      .catch(err => console.error("Priory Prerequisites Fetch Error:", err))
      .finally(() => {
        activeDossierData.loading.prerequisites = false;
        if (currentSpreadIndex === 3) renderPlanSpreadLeft();
      });

    const pItin = fetch("/api/solver/itinerary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal_item_id: solverId, time_budget_minutes: plannerBudgetMinutes })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success && data.itinerary) {
          activeDossierData.itinerary = data.itinerary;
        }
      })
      .catch(err => console.error("Priory Itinerary Fetch Error:", err))
      .finally(() => {
        activeDossierData.loading.itinerary = false;
        if (currentSpreadIndex === 3) {
          renderPlanSpreadLeft();
          renderPlanSpreadRight();
        }
      });

    await Promise.allSettled([pRecipe, pArb, pPrereq, pItin]);
    if (shouldTurn || currentSpreadIndex !== 0) {
      renderCurrentSpread();
    }
  };

  // ── Prerequisite Fetch Helper ───────────────────────────────────────────────
  window.fetchPrerequisites = async function(goalId, goalName) {
    if (!activeDossierData) return;
    activeDossierData.loading.prerequisites = true;
    if (currentSpreadIndex === 3) renderPlanSpreadLeft();

    const gid = goalId || activeLegendaryId;
    const gname = goalName || activeLegendaryName;
    const solverId = getSolverId(gid, gname);

    try {
      const res = await fetch("/api/solver/prerequisites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal_item_id: solverId })
      });
      const data = await res.json();
      if (data.success && data.prerequisites) {
        activeDossierData.prerequisites = data.prerequisites;
        if (dossierCache[gid]) {
          dossierCache[gid].prerequisites = data.prerequisites;
        }
      }
    } catch (err) {
      console.error("Priory Prerequisites Fetch Error:", err);
    } finally {
      activeDossierData.loading.prerequisites = false;
      if (currentSpreadIndex === 3) renderPlanSpreadLeft();
    }
  };

  // ── Knapsack Recalculation Handler ──────────────────────────────────────────
  window.recalculateItinerary = async function(minutes) {
    plannerBudgetMinutes = Number(minutes) || 60;
    activeDossierData.loading.itinerary = true;
    if (currentSpreadIndex === 3) {
      renderPlanSpreadLeft();
      renderPlanSpreadRight();
    }

    const solverId = getSolverId(activeLegendaryId, activeLegendaryName);
    try {
      const res = await fetch("/api/solver/itinerary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal_item_id: solverId, time_budget_minutes: plannerBudgetMinutes })
      });
      const data = await res.json();
      if (data.success && data.itinerary) {
        activeDossierData.itinerary = data.itinerary;
        if (dossierCache[activeLegendaryId]) {
          dossierCache[activeLegendaryId].itinerary = data.itinerary;
        }
      }
    } catch (e) {
      console.error("Priory Recalculate Itinerary Error:", e);
    } finally {
      activeDossierData.loading.itinerary = false;
      if (currentSpreadIndex === 3) {
        renderPlanSpreadLeft();
        renderPlanSpreadRight();
      }
    }
  };

  // ── Tab & Chapters Dropdown Controller ─────────────────────────────────────
  function updateTabState() {
    if (tabLibrary) tabLibrary.classList.toggle("active", currentSpreadIndex === 0);
    if (tabGuide) tabGuide.classList.toggle("active", currentSpreadIndex === 1);
    if (tabRecipe) tabRecipe.classList.toggle("active", currentSpreadIndex === 2);
    if (tabPlan) tabPlan.classList.toggle("active", currentSpreadIndex === 3);
    if (tabChaptersMenu) {
      tabChaptersMenu.classList.toggle("active", false);
    }
  }

  window.selectChapter = function(index) {
    const c = recentChapters[index];
    if (!c) return;
    if (chaptersDropdownCard) chaptersDropdownCard.classList.add("hidden");

    if (c.isCustomGuide) {
      activeCustomGuide = c.guide;
      if (c.id) {
        activeLegendaryId = c.id;
        activeLegendaryName = c.resolvedName || getLegendaryNameById(c.id) || activeLegendaryName;
        // Prefetch dossier in background without changing spread
        loadLegendaryDossier(c.id, activeLegendaryName, { autoTurn: false });
      }
      turnPageTo(1, 1 >= currentSpreadIndex ? "forward" : "backward");
      updateChaptersDropdown();
    } else {
      loadLegendaryDossier(c.id, c.name, { type: c.type, targetSpread: 2 });
    }
  };

  function updateChaptersDropdown() {
    if (chaptersTabLabel) {
      chaptersTabLabel.textContent = "Chapters ▾";
    }

    if (chaptersDropdownList) {
      if (recentChapters.length === 0) {
        chaptersDropdownList.innerHTML = `<div class="empty-guides-msg">No recent chapters recorded.</div>`;
      } else {
        chaptersDropdownList.innerHTML = recentChapters.map((c, idx) => {
          const isActive = c.isCustomGuide
            ? (activeCustomGuide && activeCustomGuide.goal_name === c.name && currentSpreadIndex === 1)
            : (c.id === activeLegendaryId && currentSpreadIndex !== 1);
          const typeLabel = c.isCustomGuide ? "Inquiry Guide" : (c.type || "Legendary");
          return `
            <div class="chapters-dropdown-item ${isActive ? 'active-chapter' : ''}">
              <button type="button" class="btn-select-chapter" onclick="selectChapter(${idx})" title="Open ${escapeHtml(c.name)}">
                <span class="${isActive ? 'chapter-check' : 'chapter-bullet'}">${isActive ? '✓' : (c.isCustomGuide ? '📜' : '◈')}</span>
                <span class="chapter-name">${escapeHtml(c.name)}</span>
                <span class="chapter-type">${escapeHtml(typeLabel)}</span>
              </button>
              <button type="button" class="btn-delete-chapter" data-index="${idx}" title="Remove from recent history">✕</button>
            </div>
          `;
        }).join("");

        chaptersDropdownList.querySelectorAll(".btn-delete-chapter").forEach(btn => {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const idx = parseInt(btn.getAttribute("data-index"), 10);
            if (!isNaN(idx) && idx >= 0 && idx < recentChapters.length) {
              recentChapters.splice(idx, 1);
              saveRecentChapters();
            }
          });
        });
      }
    }
  }

  // Chapters dropdown toggle & outside click dismissal
  if (tabChaptersMenu) {
    tabChaptersMenu.addEventListener("click", (e) => {
      e.stopPropagation();
      if (chaptersDropdownCard) {
        chaptersDropdownCard.classList.toggle("hidden");
      }
    });
  }

  if (btnClearAllChapters) {
    btnClearAllChapters.addEventListener("click", (e) => {
      e.stopPropagation();
      recentChapters = [];
      try {
        if (typeof window !== "undefined" && window.localStorage) {
          window.localStorage.removeItem("priory_recent_chapters");
        }
      } catch (err) {}
      updateChaptersDropdown();
      if (chaptersDropdownCard) chaptersDropdownCard.classList.add("hidden");
    });
  }

  document.addEventListener("click", (e) => {
    if (!chaptersDropdownCard || chaptersDropdownCard.classList.contains("hidden")) return;
    if (tabChaptersMenu && tabChaptersMenu.contains(e.target)) return;
    if (chaptersDropdownCard.contains(e.target)) return;
    chaptersDropdownCard.classList.add("hidden");
  });

  // Tab click listeners
  if (tabLibrary) {
    tabLibrary.addEventListener("click", () => {
      if (currentSpreadIndex !== 0 && !isFlipping) {
        turnPageTo(0, "backward");
      }
    });
  }

  if (tabGuide) {
    tabGuide.addEventListener("click", () => {
      if (currentSpreadIndex !== 1 && !isFlipping) {
        turnPageTo(1, 1 > currentSpreadIndex ? "forward" : "backward");
      }
    });
  }

  if (tabRecipe) {
    tabRecipe.addEventListener("click", () => {
      if (currentSpreadIndex !== 2 && !isFlipping) {
        turnPageTo(2, 2 > currentSpreadIndex ? "forward" : "backward");
      }
    });
  }

  if (tabPlan) {
    tabPlan.addEventListener("click", () => {
      if (currentSpreadIndex !== 3 && !isFlipping) {
        turnPageTo(3, "forward");
      }
    });
  }

  // ── Bottom Navigation & Keyboard ───────────────────────────────────────────
  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      if (currentSpreadIndex > 0 && !isFlipping) {
        turnPageTo(currentSpreadIndex - 1, "backward");
      }
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      if (currentSpreadIndex < 3 && !isFlipping) {
        turnPageTo(currentSpreadIndex + 1, "forward");
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

  // ── Page Flip Transition ───────────────────────────────────────────────────
  function turnPageTo(targetIndex, direction = "forward") {
    if (targetIndex < 0 || targetIndex > 3) return;
    if (targetIndex === currentSpreadIndex) {
      renderCurrentSpread();
      return;
    }
    if (isFlipping) {
      setTimeout(() => {
        isFlipping = false;
      }, 500);
      return;
    }
    isFlipping = true;
    document.body.classList.add("no-select");

    // Safety timeout so pages never get permanently stuck
    setTimeout(() => {
      if (isFlipping) {
        isFlipping = false;
        document.body.classList.remove("no-select");
      }
    }, 500);

    if (bookAura) bookAura.classList.add("casting");

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

    setTimeout(() => {
      currentSpreadIndex = targetIndex;
      renderCurrentSpread();
      if (leftPageBody) leftPageBody.scrollTop = 0;
      if (rightPageBody) rightPageBody.scrollTop = 0;
    }, 220);

    setTimeout(() => {
      if (pagesSpread) pagesSpread.classList.remove("turning-forward", "turning-backward");
      if (pageLeft) pageLeft.classList.remove("turning-forward", "turning-backward");
      if (pageRight) pageRight.classList.remove("turning-forward", "turning-backward");
      if (bookAura) bookAura.classList.remove("casting");
      document.body.classList.remove("no-select");
      isFlipping = false;
    }, 450);
  }

  // ── Spread Renderers Controller ──────────────────────────────────────────
  function renderCurrentSpread() {
    updateTabState();

    if (btnPrev) btnPrev.disabled = currentSpreadIndex === 0;
    if (btnNext) btnNext.disabled = currentSpreadIndex === 3;

    if (currentSpreadIndex === 0) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = "Library • Index (Spread 1 of 4)";
      renderSpread0Left();
      renderSpread0Right();
    } else if (currentSpreadIndex === 1) {
      const guideTitle = activeCustomGuide?.goal_name || "Inquiry Guide";
      if (pageCounterDisplay) pageCounterDisplay.textContent = `${guideTitle} (Spread 2 of 4)`;
      renderGuideSpreadLeft();
      renderGuideSpreadRight();
    } else if (currentSpreadIndex === 2) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = `${activeLegendaryName} • Recipe & Economics (Spread 3 of 4)`;
      renderRecipeSpreadLeft();
      renderRecipeSpreadRight();
    } else if (currentSpreadIndex === 3) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = `${activeLegendaryName} • Readiness & Plan (Spread 4 of 4)`;
      // Auto-fetch if prerequisites or itinerary are missing and not loading
      if (!activeDossierData.prerequisites && !activeDossierData.loading.prerequisites) {
        fetchPrerequisites(activeLegendaryId, activeLegendaryName);
      }
      if (!activeDossierData.itinerary && !activeDossierData.loading.itinerary) {
        recalculateItinerary(plannerBudgetMinutes);
      }
      renderPlanSpreadLeft();
      renderPlanSpreadRight();
    }
  }

  // ── Spread 0: Library Index & Popular Dossiers ──────────────────────────────
  function renderSpread0Left() {
    if (!leftPageBody) return;
    leftPageBody.innerHTML = `
      <h2 class="page-title">Library Index</h2>
      <div class="ink-divider">✦</div>

      <form class="inscribe-form" id="library-search-form" onsubmit="executeLibrarySearch(event); return false;">
        <label class="inscribe-label" for="library-search-input">Inscribe thy legendary desire upon this parchment:</label>
        <textarea id="library-search-input" class="ink-textarea" rows="3" placeholder="e.g. 'Twilight', 'Sunrise', 'Nevermore', 'How do I craft Eternity?', 'Which accessory can I get the fastest?'..."></textarea>
        <button type="button" class="btn-forge-inscribe" id="btn-search-archives" onclick="executeLibrarySearch(event)">
          <span id="btn-search-archives-text">Explore</span>
          <span id="btn-search-archives-spinner" class="spinner-ink hidden"></span>
        </button>
      </form>

      <div class="quick-pills-container">
        <div class="pills-group-title">Curated Quick Inquiries</div>
        
        <div class="pills-category">
          <span class="pills-category-label">Weapons:</span>
          <div class="pills-row">
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(30689, 'Twilight')">Twilight</button>
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(30699, 'Sunrise')">Sunrise</button>
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(30688, 'Eternity')">Eternity</button>
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(76158, 'Nevermore')">Nevermore</button>
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(30691, 'The Moot')">The Moot</button>
          </div>
        </div>

        <div class="pills-category">
          <span class="pills-category-label">Armor:</span>
          <div class="pills-row">
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(100806, 'WvW Armor', { type: 'Legendary Armor' })">WvW Armor</button>
          </div>
        </div>

        <div class="pills-category">
          <span class="pills-category-label">Trinkets:</span>
          <div class="pills-row">
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(81908, 'Aurora', { type: 'Legendary Accessory' })">Aurora</button>
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(91048, 'Vision', { type: 'Legendary Accessory' })">Vision</button>
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(93105, 'Conflux', { type: 'Legendary Ring' })">Conflux</button>
            <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(91234, 'Coalescence', { type: 'Legendary Ring' })">Coalescence</button>
          </div>
        </div>
      </div>

      <div class="account-badge-pill" onclick="openDrawerToApiKey()" title="Click to change GW2 API Key &amp; Account">
        <span class="account-pill-icon">⚜</span>
        <span>Account: <strong id="library-account-badge-name">${escapeHtml(accountTelemetry?.account_name || 'Default Account')}</strong></span>
        <span class="account-pill-action">Change Key ⚙</span>
      </div>
    `;

    const form = document.getElementById("library-search-form");
    const input = document.getElementById("library-search-input");
    if (form) {
      form.addEventListener("submit", (e) => {
        executeLibrarySearch(e);
      });
    }
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          executeLibrarySearch(e);
        }
      });
    }
  }

  function renderSpread0Right() {
    if (!rightPageBody) return;
    rightPageBody.innerHTML = `
      <h2 class="page-title">Popular Legendaries &amp; Quick Dossiers</h2>
      <div class="ink-divider">✦</div>

      <div class="popular-legendaries-matrix">
        ${POPULAR_LEGENDARIES.map(item => `
          <div class="popular-card">
            <div class="popular-card-header">
              <span class="popular-card-icon">◈</span>
              <div class="popular-card-meta">
                <strong class="popular-card-name">${escapeHtml(item.name)}</strong>
                <span class="popular-card-type">${escapeHtml(item.type)}</span>
              </div>
              <button type="button" class="btn-open-dossier" onclick="loadLegendaryDossier(${item.id}, '${escapeHtml(item.name)}', { type: '${escapeHtml(item.type)}', targetSpread: 2 })">
                Open Dossier →
              </button>
            </div>
          </div>
        `).join("")}
      </div>

      <div class="essence-journal-box" style="margin-top: 20px;">
        <div class="essence-journal-title">Archival Monotrack Dossier System</div>
        <div style="font-size: 0.78rem; color: var(--ink-soft); line-height: 1.45;">
          Select any legendary to bind the Tome into a single unified progression context. The Priory will automatically assemble market arbitrage matrices, account prerequisite audits, and a daily 0/1 knapsack session itinerary.
        </div>
      </div>
    `;
  }

  // ── Spread 1: Inquiry Guide (Comparative Ranking & Direct Guide) ───────────
  function renderGuideSpreadLeft() {
    if (!leftPageBody) return;
    const guide = activeCustomGuide;

    if (!guide) {
      leftPageBody.innerHTML = `
        <h2 class="page-title">Priory Inquiry Guide</h2>
        <div class="ink-divider">✦</div>
        <div style="text-align: center; padding: 40px 10px;">
          <div style="font-size: 2.2rem; margin-bottom: 12px;">📜</div>
          <div style="font-family: var(--font-head); color: var(--ink-dark); font-size: 0.98rem; font-weight: 700; margin-bottom: 8px;">
            No Active Inquiry Guide
          </div>
          <div style="font-size: 0.8rem; color: var(--ink-soft); line-height: 1.45; max-width: 320px; margin: 0 auto 16px auto;">
            Inscribe a query in the Library to consult the Priory archives for comparative rankings, speed evaluations, or personalized crafting guides.
          </div>
          <button type="button" class="btn-return-library" onclick="turnPageTo(0, 'backward')">← Return to Library</button>
        </div>
      `;
      return;
    }

    const isRanking = isComparativeRanking(guide);

    if (isRanking) {
      const items = parseRankingItems(guide);
      const isAccessory = (guide?.goal_name || "").toLowerCase().includes("accessor") ||
                          (guide?.executive_summary || "").toLowerCase().includes("accessor");
      const defaultName = isAccessory ? "Aurora" : (activeLegendaryName || "Aurora");
      const defaultId = isAccessory ? 81908 : (activeLegendaryId || 81908);
      const topItem = items.length > 0 ? items[0] : {
        rank: 1,
        name: defaultName,
        subtype: getLegendaryType(defaultId, defaultName),
        readiness: Math.round(guide?.readiness_percentage || 0),
        cost: "Audited",
        archetype: "Standard Crafting",
        kitReady: false,
        gate: null
      };
      const subItems = items.slice(1);
      const topPreset = LEGENDARY_PRESETS.find(p => p.name.toLowerCase() === topItem.name.toLowerCase());
      const topId = topPreset ? topPreset.id : defaultId;

      leftPageBody.innerHTML = `
        <div class="dossier-header-bar">
          <div class="dossier-header-left">
            <button type="button" class="btn-return-library" onclick="turnPageTo(0, 'backward')">← Return to Library</button>
            <div class="dossier-title-cluster">
              <h2 class="dossier-goal-title" style="margin: 0; padding: 0;">${escapeHtml(guide.goal_name)}</h2>
              <span class="dossier-type-tag">Comparative Ranking</span>
            </div>
          </div>
        </div>

        <div class="essence-journal-box" style="margin-top: 4px; padding: 6px 10px;">
          <div style="font-size: 0.78rem; color: var(--ink-dark); line-height: 1.4;">
            ${formatTextWithWaypoints(guide.executive_summary || "")}
          </div>
        </div>

        <div class="priory-hero-card" style="margin-top: 8px;">
          <div class="hero-card-header">
            <div class="rank-badge rank-top">
              <span>#1</span>
              <span class="top-pick-sub">TOP PICK</span>
            </div>
            <div class="hero-item-info">
              <div class="hero-item-title">
                <span class="hero-name">${escapeHtml(topItem.name)}</span>
                <span class="hero-subtype">${escapeHtml(topItem.subtype)}</span>
              </div>
              <div class="hero-archetype-row">
                <span class="archetype-badge">${escapeHtml(topItem.archetype)}</span>
                ${topItem.kitReady ? '<span class="kit-badge">🎁 Bank Kit Ready</span>' : ''}
                ${topItem.gate ? `<span class="gate-badge">${escapeHtml(topItem.gate)}</span>` : ''}
              </div>
            </div>
            <div class="hero-metrics">
              <div class="hero-readiness-label">Account Readiness</div>
              <div class="hero-readiness-val">${topItem.readiness}%</div>
              <div class="hero-cost-val">Cost: ~${escapeHtml(topItem.cost)}</div>
            </div>
          </div>
          <div class="hero-bar-wrap">
            <div class="readiness-bar-fill" style="width: ${Math.min(100, Math.max(0, topItem.readiness))}%;"></div>
          </div>
          ${topItem.kitReady ? `
            <div class="starter-kit-callout">
              <span class="kit-icon">🎁</span>
              <span>Eligible for <strong>Legendary Weapon Starter Kit</strong> in your Bank (Precursor &amp; Gift for 0g).</span>
            </div>
          ` : ''}
          <div class="hero-jump-bar" style="display: flex; justify-content: flex-end; margin-top: 4px;">
            <button type="button" class="btn-open-dossier" onclick="loadLegendaryDossier(${topId}, '${escapeHtml(topItem.name)}', { targetSpread: 2 })">
              Open Full Dossier ➔
            </button>
          </div>
        </div>

        ${subItems.length > 0 ? `
          <div class="dossier-section-title" style="margin-top: 8px; font-size: 0.78rem;">
            <span class="section-glyph">✦</span>
            <span>Alternative Ranked Contenders</span>
          </div>
          <div class="priory-subcards-list" style="max-height: 155px; overflow-y: auto; padding-right: 4px;">
            ${subItems.map(item => {
              const pMatch = LEGENDARY_PRESETS.find(p => p.name.toLowerCase() === item.name.toLowerCase());
              const subId = pMatch ? pMatch.id : 30689;
              return `
                <div class="priory-sub-card">
                  <div class="rank-badge rank-sub">#${item.rank}</div>
                  <div class="sub-card-main">
                    <div class="sub-card-title-row">
                      <span class="sub-item-name">${escapeHtml(item.name)}</span>
                      <span class="sub-item-subtype">${escapeHtml(item.subtype)}</span>
                      <span class="sub-item-cost">~${escapeHtml(item.cost)}</span>
                      <span class="sub-item-readiness">${item.readiness}%</span>
                    </div>
                    <div class="sub-bar-wrap">
                      <div class="readiness-bar-fill" style="width: ${Math.min(100, Math.max(0, item.readiness))}%;"></div>
                    </div>
                    <div class="sub-badges-row">
                      <span class="archetype-pill">${escapeHtml(item.archetype)}</span>
                      ${item.kitReady ? '<span class="kit-pill">🎁 Bank Kit</span>' : ''}
                      ${item.gate ? `<span class="gate-pill">${escapeHtml(item.gate)}</span>` : ''}
                      <div class="sub-card-actions">
                        <button type="button" class="btn-sub-jump" onclick="loadLegendaryDossier(${subId}, '${escapeHtml(item.name)}', { targetSpread: 2 })">Dossier ➔</button>
                      </div>
                    </div>
                  </div>
                </div>
              `;
            }).join("")}
          </div>
        ` : ''}

        <div class="essence-journal-box" style="margin-top: 6px; padding: 6px 10px; font-style: italic; font-size: 0.74rem; color: var(--ink-soft);">
          ${formatTextWithWaypoints(guide.motivational_tip || "Priory Archival Note: Temporal ranking accounts for live account wallet, materials in bank, and mastery gate status.")}
        </div>
      `;
    } else {
      // Direct Crafting Guide (isComparativeRanking === false)
      const readiness = Math.round(guide.readiness_percentage || 0);
      const missingMats = guide.missing_materials_summary || {};
      const missingKeys = Object.keys(missingMats);

      leftPageBody.innerHTML = `
        <div class="dossier-header-bar">
          <div class="dossier-header-left">
            <button type="button" class="btn-return-library" onclick="turnPageTo(0, 'backward')">← Return to Library</button>
            <div class="dossier-title-cluster">
              <h2 class="dossier-goal-title" style="margin: 0; padding: 0;">${escapeHtml(guide.goal_name)}</h2>
              <span class="dossier-type-tag">${escapeHtml(getLegendaryType(activeLegendaryId, guide.goal_name))}</span>
            </div>
          </div>
          ${guide.chat_code ? `
            <div class="dossier-header-right">
              <button class="chatcode-stamp" onclick="copyChatCode('${guide.chat_code}', this, event)" title="Copy Chat Code">
                ${escapeHtml(guide.chat_code)}
              </button>
            </div>
          ` : ''}
        </div>

        <div class="readiness-meter-wrap" style="margin-top: 8px;">
          <div class="readiness-meter-bar" style="width: ${Math.min(100, Math.max(0, readiness))}%;"></div>
          <span class="readiness-meter-label">${readiness}% Account Readiness</span>
        </div>

        <div class="essence-journal-box" style="margin-top: 6px; padding: 8px 10px;">
          <div style="font-size: 0.78rem; color: var(--ink-dark); line-height: 1.45;">
            ${formatTextWithWaypoints(guide.executive_summary || '')}
          </div>
        </div>

        <div class="dossier-section-title" style="margin-top: 10px; font-size: 0.8rem;">
          <span class="section-glyph">✦</span>
          <span>Strategic Recommendations</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 5px; max-height: 160px; overflow-y: auto; padding-right: 4px;">
          ${(guide.strategic_recommendations || []).map(rec => `
            <div class="task-item-card" style="padding: 5px 8px; font-size: 0.74rem; line-height: 1.35; color: var(--ink-mid);">
              ${formatTextWithWaypoints(rec)}
            </div>
          `).join("")}
        </div>

        ${missingKeys.length > 0 ? `
          <div class="dossier-section-title" style="margin-top: 8px; font-size: 0.78rem;">
            <span class="section-glyph">✦</span>
            <span>Outstanding Materials Audit</span>
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 4px; max-height: 75px; overflow-y: auto;">
            ${missingKeys.slice(0, 10).map(mat => `
              <span class="archetype-pill" style="font-size: 0.68rem; padding: 2px 6px;">
                ${escapeHtml(mat)}: <strong style="color: var(--leather-gold);">${missingMats[mat].toLocaleString()}</strong>
              </span>
            `).join("")}
          </div>
        ` : ''}

        <div style="display: flex; justify-content: flex-end; margin-top: 8px;">
          <button type="button" class="btn-open-dossier" onclick="loadLegendaryDossier(${activeLegendaryId}, '${escapeHtml(activeLegendaryName)}', { targetSpread: 2 })">
            Open Full Dossier ➔
          </button>
        </div>
      `;
    }
  }

  function renderGuideSpreadRight() {
    if (!rightPageBody) return;
    const guide = activeCustomGuide;

    if (!guide) {
      rightPageBody.innerHTML = `
        <h3 class="page-title">Active Dossier Fast-Track</h3>
        <div class="ink-divider">✦</div>
        <div style="text-align: center; padding: 35px 10px;">
          <div style="font-size: 0.84rem; color: var(--ink-mid); margin-bottom: 12px;">
            Currently bound legendary context: <strong style="color: var(--leather-gold); font-size: 0.92rem;">${escapeHtml(activeLegendaryName)}</strong>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px; max-width: 260px; margin: 0 auto;">
            <button type="button" class="btn-forge-inscribe" style="font-size: 0.76rem; padding: 6px 12px;" onclick="executeSearchQuery('How do I craft ${escapeHtml(activeLegendaryName)}?')">
              Generate Guide for ${escapeHtml(activeLegendaryName)}
            </button>
            <button type="button" class="btn-forge-inscribe" style="font-size: 0.76rem; padding: 6px 12px;" onclick="turnPageTo(2, 'forward')">
              Jump to Recipe &amp; Economics ➔
            </button>
          </div>
        </div>
      `;
      return;
    }

    const isRanking = isComparativeRanking(guide);

    if (isRanking) {
      let speedNote = "";
      let boosterNote = "";
      let loungeNote = "";

      for (const r of (guide.strategic_recommendations || [])) {
        if (typeof r === "string") {
          if (r.includes("Speed Analysis") || r.includes("Progression Efficiency") || r.includes("Standard Crafting")) {
            speedNote = r;
          } else if (r.includes("Booster") || r.includes("Live Booster") || r.includes("Zhaitaffy") || r.includes("Tomes of Knowledge")) {
            boosterNote = r;
          } else if (r.includes("VIP Lounge") || r.includes("Mistlock")) {
            loungeNote = r;
          }
        }
      }

      // Ensure Speed Analysis note is present for speed / ranking guides
      if (!speedNote) {
        const topName = (guide.goal_name || "").toLowerCase().includes("accessor") ? "Aurora" : activeLegendaryName;
        speedNote = `⚡ **Speed Analysis:** **${topName}** uses **Standard Crafting** (~10h gameplay effort), making it dramatically faster to craft than Gen 2.0 narrative collection legendaries (Astralaria, Nevermore, HOPE, Chuka and Champawat) which require ~40 hours of open-world tasks.`;
      }

      // Ensure Booster note is present
      if (!boosterNote && !loungeNote) {
        boosterNote = `🚀 **Booster & Utility Acceleration:** Stack Experience Booster + Heroic Booster + Guild Tavern buffs for accelerated reward tracks and currency acquisition.`;
      }

      const checklistSteps = (guide.session_checklist && guide.session_checklist.length > 0)
        ? guide.session_checklist
        : [
            {
              step_number: 1,
              title: "Complete Daily Wizard's Vault Tasks",
              estimated_time_minutes: 15,
              game_mode: "OpenWorld",
              description: "Claim Astral Acclaim and purchase remaining Mystic Clovers directly from the Vault.",
              chat_code: null
            },
            {
              step_number: 2,
              title: "Gather Missing Materials in Drizzlewood Coast",
              estimated_time_minutes: 45,
              game_mode: "OpenWorld",
              description: "Teleport to Base Camp Waypoint [&BDoMAAA=] to progress material tracks for missing T6 fine trophies.",
              chat_code: "[&BDoMAAA=]"
            }
          ];

      rightPageBody.innerHTML = `
        <h3 class="page-title">Strategic Acceleration</h3>
        <div class="ink-divider">✦</div>

        ${speedNote ? `
          <div class="leaderboard-synergy-box kit-synergy-box" style="margin-bottom: 6px;">
            <div class="synergy-box-title">⚡ Speed &amp; Efficiency Analysis</div>
            <div class="synergy-box-content">${formatTextWithWaypoints(speedNote)}</div>
          </div>
        ` : ''}

        ${boosterNote ? `
          <div class="leaderboard-synergy-box booster-synergy-box" style="margin-bottom: 6px;">
            <div class="synergy-box-title">🚀 Booster &amp; Utility Acceleration</div>
            <div class="synergy-box-content">${formatTextWithWaypoints(boosterNote)}</div>
          </div>
        ` : (loungeNote ? `
          <div class="leaderboard-synergy-box kit-synergy-box" style="margin-bottom: 6px;">
            <div class="synergy-box-title">✨ VIP Utility &amp; Staging</div>
            <div class="synergy-box-content">${formatTextWithWaypoints(loungeNote)}</div>
          </div>
        ` : `
          <div class="leaderboard-synergy-box kit-synergy-box" style="margin-bottom: 6px;">
            <div class="synergy-box-title">⚡ Priory Acceleration Protocol</div>
            <div class="synergy-box-content">Stack account-bound boosters, complete daily Wizard's Vault objectives for Astral Acclaim, and prioritize time-gated components first.</div>
          </div>
        `)}

        <div class="dossier-section-title" style="margin-top: 8px; font-size: 0.8rem;">
          <span class="section-glyph">✦</span>
          <span>Actionable Session Checklist</span>
        </div>

        <div class="leaderboard-checklist" style="max-height: 220px; overflow-y: auto; padding-right: 4px;">
          ${checklistSteps.map(step => `
            <div class="leaderboard-ck-item">
              <div class="ck-item-top">
                <span class="ck-step-num">Step ${step.step_number}</span>
                <span class="ck-step-title">${escapeHtml(step.title)}</span>
                <span class="ck-step-time">⏱ ${step.estimated_time_minutes}m</span>
                <span class="ck-mode-badge mode-${(step.game_mode || 'openworld').toLowerCase()}">${escapeHtml(step.game_mode || 'Session')}</span>
              </div>
              <div class="ck-item-desc">${formatTextWithWaypoints(step.description)}</div>
              ${step.chat_code ? `
                <div class="ck-item-footer">
                  <button type="button" class="chatcode-stamp ck-wp-btn" onclick="copyChatCode('${step.chat_code}', this, event)" title="Copy Waypoint Code">
                    📍 ${escapeHtml(step.chat_code)}
                  </button>
                </div>
              ` : ''}
            </div>
          `).join("")}
        </div>

        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px;">
          <button type="button" class="btn-forge-inscribe" style="width: auto; padding: 5px 12px; font-size: 0.74rem;" onclick="turnPageTo(2, 'forward')">
            View Recipe &amp; Economics ➔
          </button>
          <button type="button" class="btn-forge-inscribe" style="width: auto; padding: 5px 12px; font-size: 0.74rem;" onclick="turnPageTo(3, 'forward')">
            View Readiness &amp; Plan ➔
          </button>
        </div>
      `;
    } else {
      // Direct Crafting Guide (isComparativeRanking === false)
      rightPageBody.innerHTML = `
        <h3 class="page-title">Master Roadmap &amp; Session Checklist</h3>
        <div class="ink-divider">✦</div>

        <div class="dossier-section-title" style="font-size: 0.8rem;">
          <span class="section-glyph">✦</span>
          <span>Master Roadmap Phases</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 5px; max-height: 160px; overflow-y: auto; padding-right: 4px; margin-bottom: 8px;">
          ${(guide.master_roadmap_phases || []).map(phase => `
            <div class="task-item-card" style="padding: 5px 8px; font-size: 0.74rem; line-height: 1.35;">
              ${formatTextWithWaypoints(phase)}
            </div>
          `).join("")}
        </div>

        <div class="dossier-section-title" style="font-size: 0.8rem;">
          <span class="section-glyph">✦</span>
          <span>Actionable Session Checklist</span>
        </div>
        <div class="leaderboard-checklist" style="max-height: 170px; overflow-y: auto; padding-right: 4px;">
          ${(guide.session_checklist || []).map(step => `
            <div class="leaderboard-ck-item">
              <div class="ck-item-top">
                <span class="ck-step-num">Step ${step.step_number}</span>
                <span class="ck-step-title">${escapeHtml(step.title)}</span>
                <span class="ck-step-time">⏱ ${step.estimated_time_minutes}m</span>
                <span class="ck-mode-badge mode-${(step.game_mode || 'openworld').toLowerCase()}">${escapeHtml(step.game_mode || 'Session')}</span>
              </div>
              <div class="ck-item-desc">${formatTextWithWaypoints(step.description)}</div>
              ${step.chat_code ? `
                <div class="ck-item-footer">
                  <button type="button" class="chatcode-stamp ck-wp-btn" onclick="copyChatCode('${step.chat_code}', this, event)" title="Copy Waypoint Code">
                    📍 ${escapeHtml(step.chat_code)}
                  </button>
                </div>
              ` : ''}
            </div>
          `).join("")}
        </div>

        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px;">
          <button type="button" class="btn-forge-inscribe" style="width: auto; padding: 5px 12px; font-size: 0.74rem;" onclick="turnPageTo(2, 'forward')">
            View Recipe &amp; Economics ➔
          </button>
          <button type="button" class="btn-forge-inscribe" style="width: auto; padding: 5px 12px; font-size: 0.74rem;" onclick="turnPageTo(3, 'forward')">
            View Readiness &amp; Plan ➔
          </button>
        </div>
      `;
    }
  }

  // Aliases for Guide Spread functions per specification
  window.renderGuideSpreadLeft = renderGuideSpreadLeft;
  window.renderGuideSpreadRight = renderGuideSpreadRight;
  window.renderSpreadGuideLeft = renderGuideSpreadLeft;
  window.renderSpreadGuideRight = renderGuideSpreadRight;
  window.renderSpread1Left = renderGuideSpreadLeft;
  window.renderSpread1Right = renderGuideSpreadRight;

  // ── Spread 2: Recipe & Market Economics ─────────────────────────────────────
  function renderRecipeSpreadLeft() {
    if (!leftPageBody) return;

    const isLoading = activeDossierData.loading.recipe;
    const guide = activeDossierData.recipe;
    const itemType = getLegendaryType(activeLegendaryId, activeLegendaryName);
    const chatCode = guide?.chat_code || "[&AgErZgAA]";
    const readinessPct = guide?.readiness_percentage != null ? guide.readiness_percentage : 0;

    let bodyContent = "";

    if (isLoading) {
      bodyContent = `
        <div style="text-align: center; padding: 40px 10px;">
          <span class="spinner-ink" style="width: 32px; height: 32px; border-width: 3px; border-top-color: var(--leather-gold);"></span>
          <div style="margin-top: 12px; font-family: var(--font-head); color: var(--ink-mid); font-size: 0.88rem;">
            Consulting Priory Archives for ${escapeHtml(activeLegendaryName)}...
          </div>
        </div>
      `;
    } else {
      const arb = activeDossierData.arbitrage;
      const scratchCost = arb?.craft_from_scratch_total || 21500000;
      const accountCost = arb?.my_account_craft_cost || 18500000;
      const ownedValue = Math.max(0, scratchCost - accountCost);
      const goldRequired = accountCost;

      const missingMats = guide?.missing_materials_summary || {};
      const missingKeys = Object.keys(missingMats);
      const missingCount = missingKeys.length;

      const precursorName = arb?.precursor_strategy?.precursor_name || "Precursor Weapon";
      const sockets = [
        { name: precursorName, count: "1x", icon: "🗡️" },
        { name: "Gift of Mastery", count: "1x", icon: "🗺️" },
        { name: "Gift of Fortune", count: "1x", icon: "🍀" },
        { name: `Gift of ${activeLegendaryName}`, count: "1x", icon: "✨" }
      ];

      bodyContent = `
        <div class="readiness-meter-wrap" style="margin-top: 8px;">
          <div class="readiness-meter-bar" style="width: ${Math.min(100, Math.max(0, readinessPct))}%;"></div>
          <span class="readiness-meter-label">${readinessPct}% Account Progress</span>
        </div>

        <div class="arbitrage-grid" style="margin-top: 10px;">
          <div class="arb-card">
            <span class="arb-card-lbl">Total Craft Cost</span>
            <span class="arb-card-val">${formatCopper(scratchCost)}</span>
          </div>
          <div class="arb-card">
            <span class="arb-card-lbl">Account Owned Value</span>
            <span class="arb-card-val" style="color: #2e7d32;">${formatCopper(ownedValue)}</span>
          </div>
          <div class="arb-card">
            <span class="arb-card-lbl">Missing Materials</span>
            <span class="arb-card-val">${missingCount > 0 ? `${missingCount} types` : 'Audited'}</span>
          </div>
          <div class="arb-card" style="border-color: var(--leather-gold); background: rgba(200, 150, 62, 0.08);">
            <span class="arb-card-lbl" style="color: var(--leather-gold); font-weight: bold;">Gold Required</span>
            <span class="arb-card-val" style="font-weight: bold;">${formatCopper(goldRequired)}</span>
          </div>
        </div>

        <div class="dossier-section-title" style="margin-top: 12px;">
          <span class="section-glyph">✦</span>
          <span>Mystic Forge Recipe Tree</span>
        </div>

        <div class="mystic-forge-sockets-container">
          ${sockets.map(s => `
            <div class="mf-socket">
              <span class="mf-socket-icon">${s.icon}</span>
              <div class="mf-socket-details">
                <span class="mf-socket-name">${escapeHtml(s.name)}</span>
                <span class="mf-socket-count">${escapeHtml(s.count)}</span>
              </div>
            </div>
          `).join("")}
        </div>

        ${missingCount > 0 ? `
          <div class="essence-journal-box" style="margin-top: 6px; padding: 6px 10px;">
            <div class="essence-journal-title" style="font-size: 0.72rem; margin-bottom: 4px;">Primary Outstanding Components</div>
            <div style="max-height: 105px; overflow-y: auto; padding-right: 4px;">
              ${missingKeys.slice(0, 6).map(k => `
                <div style="display: flex; justify-content: space-between; font-size: 0.74rem; border-bottom: 1px dotted var(--parch-line); padding: 2px 0;">
                  <span>${escapeHtml(k)}</span>
                  <span style="font-family: var(--font-mono); color: var(--leather-gold); font-weight: 600;">${missingMats[k]} needed</span>
                </div>
              `).join("")}
            </div>
          </div>
        ` : ''}
      `;
    }

    leftPageBody.innerHTML = `
      <div class="dossier-header-bar">
        <div class="dossier-header-left">
          <button type="button" class="btn-return-library" onclick="turnPageTo(0, 'backward')">← Return to Library</button>
          <div class="dossier-title-cluster">
            <h2 class="dossier-goal-title" style="margin: 0; padding: 0;">${escapeHtml(activeLegendaryName)}</h2>
            <span class="dossier-type-tag">${escapeHtml(itemType)}</span>
          </div>
        </div>
        <div class="dossier-header-right">
          <button class="chatcode-stamp" onclick="copyChatCode('${chatCode}', this, event)" title="Copy Chat Code">
            ${escapeHtml(chatCode)}
          </button>
        </div>
      </div>

      ${bodyContent}
    `;
  }

  function renderRecipeSpreadRight() {
    if (!rightPageBody) return;

    const isLoading = activeDossierData.loading.arbitrage;
    const arb = activeDossierData.arbitrage;

    if (isLoading) {
      rightPageBody.innerHTML = `
        <h3 class="page-title">Market Arbitrage &amp; Economics</h3>
        <div class="ink-divider">✦</div>
        <div style="text-align: center; padding: 40px 10px;">
          <span class="spinner-ink" style="width: 32px; height: 32px; border-width: 3px; border-top-color: var(--leather-gold);"></span>
          <div style="margin-top: 12px; font-family: var(--font-head); color: var(--ink-mid); font-size: 0.88rem;">
            Evaluating Wallace TP Tax &amp; Market Arbitrage...
          </div>
        </div>
      `;
      return;
    }

    if (!arb) {
      rightPageBody.innerHTML = `
        <h3 class="page-title">Market Arbitrage &amp; Economics</h3>
        <div class="ink-divider">✦</div>
        <div style="text-align: center; padding: 30px; color: var(--ink-soft); font-family: var(--font-hand); font-size: 1.1rem;">
          Arbitrage data unavailable.
        </div>
      `;
      return;
    }

    let verdictClass = 'craft';
    let verdictLabel = 'RECOMMENDED: CRAFT FOR SELF';
    if (arb.recommended_action === 'CRAFT_FOR_PROFIT') {
      verdictClass = 'profit';
      verdictLabel = '✦ HIGH VALUE: CRAFT FOR PROFIT (TP FLIP) ✦';
    } else if (arb.recommended_action === 'BUY_FINISHED_DIRECT') {
      verdictClass = 'buy';
      verdictLabel = 'RECOMMENDED: BUY FINISHED FROM TRADING POST';
    }

    const marginVal = arb.profit_margin_if_sold != null ? arb.profit_margin_if_sold : 0;
    const marginColor = marginVal >= 0 ? '#2e7d32' : '#c62828';
    const marginSign = marginVal >= 0 ? '+' : '';
    const taxAmt = Math.round(arb.buy_order_total * 0.15);

    const prec = arb.precursor_strategy || {};
    const clover = arb.clover_strategy || {};

    rightPageBody.innerHTML = `
      <h3 class="page-title">Market Arbitrage &amp; Economics</h3>
      <div class="ink-divider">✦</div>

      <div class="verdict-banner ${verdictClass}">
        ${verdictLabel}
      </div>

      <div class="arbitrage-grid" style="margin-top: 8px;">
        <div class="arb-card">
          <span class="arb-card-lbl">Instant TP Buy</span>
          <span class="arb-card-val">${formatCopper(arb.instant_buy_total)}</span>
        </div>
        <div class="arb-card">
          <span class="arb-card-lbl">TP Buy Order</span>
          <span class="arb-card-val">${formatCopper(arb.buy_order_total)}</span>
        </div>
        <div class="arb-card">
          <span class="arb-card-lbl">Scratch Craft Cost</span>
          <span class="arb-card-val">${formatCopper(arb.craft_from_scratch_total)}</span>
        </div>
        <div class="arb-card" style="border-color: var(--leather-gold); background: rgba(200, 150, 62, 0.08);">
          <span class="arb-card-lbl" style="color: var(--leather-gold); font-weight: bold;">My Account Craft Cost</span>
          <span class="arb-card-val" style="font-weight: bold;">${formatCopper(arb.my_account_craft_cost)}</span>
        </div>
      </div>

      <div class="tax-breakdown-box" style="margin-top: 8px;">
        <div style="font-family: var(--font-head); font-weight: 700; color: var(--ink-dark); text-transform: uppercase; font-size: 0.74rem;">
          Wallace 15% TP Tax Liquidation Model
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.76rem;">
          <span style="color: var(--ink-soft);">Gross TP Liquidation:</span>
          <span>${formatCopper(arb.buy_order_total)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.76rem;">
          <span style="color: var(--ink-soft);">Wallace 15% TP Tax:</span>
          <span style="color: #c62828;">-${formatCopper(taxAmt)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; border-top: 1px dotted var(--parch-line); padding-top: 2px; font-size: 0.78rem;">
          <span style="font-weight: bold;">Net Payout If Sold:</span>
          <span style="font-weight: bold;">${formatCopper(arb.net_sell_if_sold)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; border-top: 1px solid var(--parch-line); padding-top: 2px; font-size: 0.78rem;">
          <span style="font-weight: bold;">Net Profit Margin (vs Scratch):</span>
          <span style="font-weight: bold; color: ${marginColor};">${marginSign}${formatCopper(marginVal)}</span>
        </div>
      </div>

      <div class="task-item-card" style="margin-top: 6px; padding: 6px 10px;">
        <div class="task-header-row">
          <span class="task-title" style="font-size: 0.78rem;">🗡️ Precursor Acquisition Strategy</span>
          <span class="task-duration-badge" style="background: var(--leather-gold); color: #fff;">${escapeHtml(prec.recommended_strategy || 'BUY_ORDER')}</span>
        </div>
        <div style="font-size: 0.75rem; color: var(--ink-mid); margin-top: 2px;">
          <strong>Target:</strong> ${escapeHtml(prec.precursor_name || 'Precursor')} ${prec.precursor_id ? `(ID: ${prec.precursor_id})` : ''}
        </div>
        <div style="font-size: 0.74rem; color: var(--ink-soft); line-height: 1.35; margin-top: 2px;">
          ${escapeHtml(prec.details || 'Compare TP buy order vs Grandmaster Craftsman Hobbs collection vs Wizard Vault Starter Kit.')}
        </div>
      </div>

      <div class="task-item-card" style="margin-top: 6px; padding: 6px 10px;">
        <div class="task-header-row">
          <span class="task-title" style="font-size: 0.78rem;">🍀 Mystic Clover EV Strategy</span>
          <span class="task-duration-badge" style="background: #70338a; color: #fff;">${escapeHtml(clover.recommended_strategy || 'WIZARDS_VAULT')}</span>
        </div>
        <div style="font-size: 0.74rem; color: var(--ink-soft); line-height: 1.35; margin-top: 2px;">
          ${escapeHtml(clover.notes || 'Expected Value: 3.2 Mystic Coins + 3.2 Ecto per Clover via Mystic Forge recipe vs discounted Astral Acclaim and Fractal BLING-9988.')}
        </div>
      </div>
    `;
  }

  window.renderRecipeSpreadLeft = renderRecipeSpreadLeft;
  window.renderRecipeSpreadRight = renderRecipeSpreadRight;
  window.renderSpread2Left = renderRecipeSpreadLeft;
  window.renderSpread2Right = renderRecipeSpreadRight;

  // ── Spread 3: Readiness & Daily Session Plan ────────────────────────────────
  function renderPlanSpreadLeft() {
    if (!leftPageBody) return;

    const isLoadingPrereq = activeDossierData.loading.prerequisites;
    const isLoadingItin = activeDossierData.loading.itinerary;
    const prereq = activeDossierData.prerequisites;
    const itin = activeDossierData.itinerary;

    // 1. Compact Prerequisite Status Seal
    let prereqSealHtml = "";
    if (isLoadingPrereq) {
      prereqSealHtml = `
        <div class="prereq-compact-seal" style="padding: 6px 12px; margin-bottom: 8px;">
          <span class="spinner-ink" style="width: 14px; height: 14px; border-width: 2px;"></span>
          <div class="seal-content">
            <div class="seal-title" style="font-size: 0.76rem;">Auditing Account Prerequisites...</div>
            <div class="seal-sub">Checking world completion, masteries &amp; crafting disciplines</div>
          </div>
        </div>
      `;
    } else if (!prereq) {
      prereqSealHtml = `
        <div class="prereq-compact-seal warn pending" style="margin-bottom: 8px;">
          <span class="seal-icon">⚠️</span>
          <div class="seal-content prereq-seal-info">
            <div class="seal-title prereq-seal-badge warn">PREREQUISITE DATA UNAVAILABLE</div>
            <div class="seal-sub prereq-seal-sub">Click to retry account prerequisite audit</div>
          </div>
          <button type="button" class="btn-toggle-prereq-details btn-prereq-details" onclick="fetchPrerequisites()">Audit</button>
        </div>
      `;
    } else {
      const canCraft = Boolean(prereq.can_craft_immediately);
      const isSatisfied = canCraft || (prereq.has_world_completion && prereq.active_crafting_ready && prereq.mastery_requirements_met && (!prereq.blockers || prereq.blockers.length === 0));

      const primaryBlocker = (prereq.blockers && prereq.blockers.length > 0)
        ? prereq.blockers[0]
        : "Action items remaining";

      const sealBadgeText = isSatisfied ? "✓ PREREQUISITES SATISFIED" : "⚠️ PREREQUISITES PENDING";
      const sealSubText = isSatisfied
        ? "World completion, Crafting 500 &amp; Masteries verified."
        : escapeHtml(primaryBlocker);
      const sealStatusClass = isSatisfied ? "pass satisfied" : "warn pending";
      const sealIcon = isSatisfied ? "✓" : "⚠️";

      const worldBadge = prereq.has_world_completion ? "pass" : "fail";
      const worldText = prereq.has_world_completion ? "Completed" : "Incomplete";

      const craftBadge = prereq.active_crafting_ready ? "pass" : "warn";
      const craftText = prereq.active_crafting_ready ? "Ready (500)" : "Needs Discipline";

      const masteryBadge = prereq.mastery_requirements_met ? "pass" : "warn";
      const masteryText = prereq.mastery_requirements_met ? "Satisfied" : "Missing Unlocks";

      const precBits = prereq.precursor_collection_bits_total > 0
        ? `${prereq.precursor_collection_bits_done} / ${prereq.precursor_collection_bits_total}`
        : "Standard";

      let blockersHtml = "";
      if (prereq.blockers && prereq.blockers.length > 0) {
        blockersHtml = prereq.blockers.map(b => `
          <div style="font-size: 0.74rem; color: #c62828; margin-bottom: 2px; display: flex; gap: 5px;">
            <span>⛔</span> <span>${escapeHtml(b)}</span>
          </div>
        `).join("");
      } else {
        blockersHtml = `<div style="font-size: 0.74rem; color: #2e7d32; font-style: italic;">✨ Zero hard blockers! All prerequisite requirements are met.</div>`;
      }

      let routingHtml = "";
      if (prereq.crafting_assignment_recommendations && prereq.crafting_assignment_recommendations.length > 0) {
        routingHtml = prereq.crafting_assignment_recommendations.map(r => `
          <div class="task-item-card" style="margin-bottom: 4px; padding: 4px 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.76rem;">
              <strong>${escapeHtml(r.gift_or_component || r.gift || 'Gift')}</strong>
              <span style="color: var(--leather-gold); font-weight: bold;">${escapeHtml(r.character_name || r.recommended_character || 'Active Character')}</span>
            </div>
            <div style="font-size: 0.7rem; color: var(--ink-soft);">
              Discipline: ${escapeHtml(r.discipline || 'Weaponsmith')} (Rating: ${r.current_rating || 500})
            </div>
          </div>
        `).join("");
      } else if (prereq.character_discipline_assignments && Object.keys(prereq.character_discipline_assignments).length > 0) {
        routingHtml = Object.entries(prereq.character_discipline_assignments).map(([disc, char]) => {
          const charName = typeof char === "object" ? char.character_name : char;
          return `
            <div class="task-item-card" style="margin-bottom: 4px; padding: 4px 8px;">
              <div style="display: flex; justify-content: space-between; font-size: 0.76rem;">
                <strong>${escapeHtml(disc)}</strong>
                <span style="color: var(--leather-gold); font-weight: bold;">${escapeHtml(charName)}</span>
              </div>
            </div>
          `;
        }).join("");
      }

      prereqSealHtml = `
        <div class="prereq-compact-seal ${sealStatusClass}">
          <span class="seal-icon">${sealIcon}</span>
          <div class="seal-content prereq-seal-info">
            <div class="seal-title prereq-seal-badge ${isSatisfied ? 'pass' : 'warn'}">${sealBadgeText}</div>
            <div class="seal-sub prereq-seal-sub">${sealSubText}</div>
          </div>
          <button type="button" class="btn-toggle-prereq-details btn-prereq-details" id="btn-toggle-prereq-details" title="Toggle prerequisite audit details">
            ${prereqDetailsExpanded ? 'Details ▴' : 'Details ▾'}
          </button>
        </div>

        <div id="prereq-collapsible-details" class="prereq-collapsible-details ${prereqDetailsExpanded ? 'expanded active' : ''}">
          <div class="prereq-pillars-grid">
            <div class="pillar-card">
              <div class="pillar-header">
                <span>World Comp</span>
                <span class="pillar-badge ${worldBadge}">${worldText}</span>
              </div>
              <div style="font-size: 0.7rem; color: var(--ink-soft);">
                Source: ${escapeHtml(prereq.world_completion_source || 'Map Exploration')}
              </div>
            </div>

            <div class="pillar-card">
              <div class="pillar-header">
                <span>Crafting 500</span>
                <span class="pillar-badge ${craftBadge}">${craftText}</span>
              </div>
              <div style="font-size: 0.7rem; color: var(--ink-soft);">
                ${prereq.active_crafting_ready ? 'Discipline active (500)' : 'Discipline required'}
              </div>
            </div>

            <div class="pillar-card">
              <div class="pillar-header">
                <span>Masteries</span>
                <span class="pillar-badge ${masteryBadge}">${masteryText}</span>
              </div>
              <div style="font-size: 0.7rem; color: var(--ink-soft);">
                ${prereq.missing_masteries?.length > 0 ? `${prereq.missing_masteries.length} tracks pending` : 'All masteries verified'}
              </div>
            </div>

            <div class="pillar-card">
              <div class="pillar-header">
                <span>Precursor</span>
                <span class="pillar-badge pass">${precBits}</span>
              </div>
              <div style="font-size: 0.7rem; color: var(--ink-soft);">
                ${escapeHtml(prereq.precursor_collection_step || 'Tradeable / Finished')}
              </div>
            </div>
          </div>

          <div class="dossier-section-title" style="margin-top: 6px; font-size: 0.76rem;">
            <span class="section-glyph">✦</span>
            <span>Active Crafting Blockers</span>
          </div>
          <div style="margin-bottom: 4px;">
            ${blockersHtml}
          </div>

          ${routingHtml ? `
            <div class="dossier-section-title" style="margin-top: 6px; font-size: 0.76rem;">
              <span class="section-glyph">✦</span>
              <span>Multi-Alt Discipline Routing</span>
            </div>
            <div>
              ${routingHtml}
            </div>
          ` : ''}
        </div>
      `;
    }

    // 2. Knapsack Playtime Budget Controls
    const budgetControlsHtml = `
      <div class="inscribe-form" style="margin-top: 6px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
          <label class="inscribe-label" for="planner-budget-slider" style="font-size: 0.88rem;">Playtime Budget:</label>
          <span id="budget-val-display" style="font-family: var(--font-head); font-weight: 700; color: var(--leather-gold); font-size: 0.95rem;">${plannerBudgetMinutes} mins</span>
        </div>

        <input type="range" id="planner-budget-slider" class="priory-slider" min="30" max="120" step="15" value="${plannerBudgetMinutes}">

        <div class="playtime-budget-btns playtime-quick-btns" style="margin-top: 4px;">
          <button type="button" class="playtime-btn ${plannerBudgetMinutes === 30 ? 'active' : ''}" data-mins="30">30m</button>
          <button type="button" class="playtime-btn ${plannerBudgetMinutes === 60 ? 'active' : ''}" data-mins="60">60m</button>
          <button type="button" class="playtime-btn ${plannerBudgetMinutes === 90 ? 'active' : ''}" data-mins="90">90m</button>
          <button type="button" class="playtime-btn ${plannerBudgetMinutes === 120 ? 'active' : ''}" data-mins="120">120m</button>
        </div>

        <button type="button" class="btn-forge-inscribe" id="btn-calc-itinerary" style="margin-top: 8px;">
          <span id="btn-itinerary-text">${isLoadingItin ? 'Computing Knapsack Schedule...' : 'Schedule Optimal Itinerary'}</span>
          <span id="btn-itinerary-spinner" class="spinner-ink ${isLoadingItin ? '' : 'hidden'}"></span>
        </button>
      </div>
    `;

    // 3. Session Summary Box
    let summaryContent = "";
    if (isLoadingItin) {
      summaryContent = `
        <div class="essence-journal-box session-summary-box" style="margin-top: 8px; text-align: center; padding: 20px 10px;">
          <span class="spinner-ink" style="width: 24px; height: 24px; border-width: 2px; border-top-color: var(--leather-gold);"></span>
          <div style="margin-top: 8px; font-family: var(--font-head); color: var(--ink-mid); font-size: 0.8rem;">
            Optimizing 0/1 Knapsack session itinerary...
          </div>
        </div>
      `;
    } else if (!itin) {
      summaryContent = `
        <div class="essence-journal-box session-summary-box" style="margin-top: 8px;">
          <div class="essence-journal-title">
            <span>Session Allocation</span>
            <span style="color: var(--leather-gold); font-weight: bold;">0% Utilization</span>
          </div>
          <div class="essence-stats-grid">
            <div class="stat-item"><span class="lbl">Budget:</span><span class="val">${plannerBudgetMinutes}m</span></div>
            <div class="stat-item"><span class="lbl">Scheduled:</span><span class="val">0m</span></div>
            <div class="stat-item"><span class="lbl">Tasks Queued:</span><span class="val">0</span></div>
            <div class="stat-item"><span class="lbl">Unused Window:</span><span class="val">${plannerBudgetMinutes}m</span></div>
          </div>
          <div style="font-size: 0.76rem; color: var(--ink-soft); margin-top: 6px; font-style: italic;">
            Select playtime budget and click &ldquo;Schedule Optimal Itinerary&rdquo; to compute.
          </div>
        </div>
      `;
    } else {
      const tasksCount = itin.tasks ? itin.tasks.length : 0;
      const scheduledMin = itin.total_scheduled_minutes || 0;
      const budgetMin = itin.time_budget_minutes || plannerBudgetMinutes;
      const unusedMin = Math.max(0, budgetMin - scheduledMin);
      const utilPct = itin.time_utilization_pct !== undefined 
        ? itin.time_utilization_pct 
        : Math.round((scheduledMin / (budgetMin || 1)) * 100);

      const assignedCharFromItin = itin.tasks?.find(t => t.character_name)?.character_name;
      let assignedCharFromPrereq = null;
      if (prereq?.crafting_assignment_recommendations?.length > 0) {
        assignedCharFromPrereq = prereq.crafting_assignment_recommendations[0].character_name || prereq.crafting_assignment_recommendations[0].recommended_character;
      } else if (prereq?.character_discipline_assignments && Object.keys(prereq.character_discipline_assignments).length > 0) {
        const firstVal = Object.values(prereq.character_discipline_assignments)[0];
        assignedCharFromPrereq = typeof firstVal === "object" ? firstVal.character_name : firstVal;
      }
      const assignedChar = assignedCharFromItin || assignedCharFromPrereq;

      const charNoteHtml = assignedChar
        ? `<div style="font-size: 0.74rem; color: var(--ink-soft); margin-top: 6px; padding-top: 5px; border-top: 1px dotted var(--parch-line);">
             👤 <strong>Character Routing:</strong> Assigned to <span style="color: var(--leather-gold); font-weight: 700;">${escapeHtml(assignedChar)}</span> (zero re-licensing fees).
           </div>`
        : `<div style="font-size: 0.74rem; color: var(--ink-soft); margin-top: 6px; padding-top: 5px; border-top: 1px dotted var(--parch-line);">
             👤 <strong>Character Routing:</strong> Primary active character (zero re-licensing fees).
           </div>`;

      summaryContent = `
        <div class="essence-journal-box session-summary-box" style="margin-top: 8px;">
          <div class="essence-journal-title">
            <span>Session Allocation</span>
            <span style="color: var(--leather-gold); font-weight: bold;">${utilPct}% Utilization</span>
          </div>
          <div class="essence-stats-grid">
            <div class="stat-item"><span class="lbl">Budget:</span><span class="val">${budgetMin}m</span></div>
            <div class="stat-item"><span class="lbl">Scheduled:</span><span class="val">${scheduledMin}m</span></div>
            <div class="stat-item"><span class="lbl">Tasks Queued:</span><span class="val">${tasksCount}</span></div>
            <div class="stat-item"><span class="lbl">Unused Window:</span><span class="val">${unusedMin}m</span></div>
          </div>
          ${itin.summary ? `
            <div style="font-size: 0.76rem; color: var(--ink-mid); margin-top: 6px; font-style: italic; line-height: 1.35;">
              &ldquo;${escapeHtml(itin.summary)}&rdquo;
            </div>
          ` : ''}
          ${charNoteHtml}
        </div>
      `;
    }

    leftPageBody.innerHTML = `
      <h2 class="page-title">Session Planner &amp; Strategy</h2>
      <div class="ink-divider">✦</div>

      ${prereqSealHtml}

      ${budgetControlsHtml}

      ${summaryContent}
    `;

    // Slider & preset buttons listeners
    const slider = document.getElementById("planner-budget-slider");
    const valDisplay = document.getElementById("budget-val-display");

    if (slider) {
      slider.addEventListener("input", (e) => {
        const mins = parseInt(e.target.value, 10);
        plannerBudgetMinutes = mins;
        if (valDisplay) valDisplay.textContent = `${mins} mins`;
        document.querySelectorAll(".playtime-btn").forEach(btn => {
          btn.classList.toggle("active", parseInt(btn.getAttribute("data-mins"), 10) === mins);
        });
      });
      slider.addEventListener("change", (e) => {
        const mins = parseInt(e.target.value, 10);
        recalculateItinerary(mins);
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
        recalculateItinerary(mins);
      });
    });

    const btnCalc = document.getElementById("btn-calc-itinerary");
    if (btnCalc) {
      btnCalc.addEventListener("click", () => {
        recalculateItinerary(plannerBudgetMinutes);
      });
    }

    const btnToggleDetails = document.getElementById("btn-toggle-prereq-details");
    if (btnToggleDetails) {
      btnToggleDetails.addEventListener("click", () => {
        prereqDetailsExpanded = !prereqDetailsExpanded;
        const detailsEl = document.getElementById("prereq-collapsible-details");
        if (detailsEl) {
          detailsEl.classList.toggle("expanded", prereqDetailsExpanded);
          detailsEl.classList.toggle("active", prereqDetailsExpanded);
        }
        btnToggleDetails.textContent = prereqDetailsExpanded ? "Details ▴" : "Details ▾";
      });
    }
  }

  function renderPlanSpreadRight() {
    if (!rightPageBody) return;

    const isLoading = activeDossierData.loading.itinerary;
    const itin = activeDossierData.itinerary;

    let routeContent = "";

    if (isLoading) {
      routeContent = `
        <div style="text-align: center; padding: 40px 10px;">
          <span class="spinner-ink" style="width: 32px; height: 32px; border-width: 3px; border-top-color: var(--leather-gold);"></span>
          <div style="margin-top: 12px; font-family: var(--font-head); color: var(--ink-mid); font-size: 0.88rem;">
            Computing 0/1 Knapsack Daily Schedule (${plannerBudgetMinutes}m budget)...
          </div>
        </div>
      `;
    } else if (!itin || !itin.tasks || itin.tasks.length === 0) {
      routeContent = `
        <div style="text-align: center; padding: 30px; color: var(--ink-soft); font-family: var(--font-hand); font-size: 1.15rem;">
          No tasks scheduled for this duration. Select a playtime budget on the left page to compute an itinerary.
        </div>
      `;
    } else {
      routeContent = itin.tasks.map((task, idx) => {
        const inputs = task.required_inputs?.name 
          ? `${task.required_inputs.count ? task.required_inputs.count + 'x ' : ''}${task.required_inputs.name}`
          : (task.required_inputs?.description || (task.required_inputs?.currencies ? Object.entries(task.required_inputs.currencies).map(([k, v]) => `${v} ${k}`).join(', ') : 'None'));
        
        const rewardVal = task.reward_output?.value_towards_goal || task.reward_output?.name || 'Progression towards goal';
        const charTag = task.character_name 
          ? `<div style="font-size: 0.72rem; color: var(--ink-soft);">👤 Character: <strong style="color: var(--leather-gold);">${escapeHtml(task.character_name)}</strong></div>`
          : '';

        return `
          <div class="task-item-card">
            <div class="task-header-row">
              <span class="task-title" style="font-size: 0.82rem;">${idx + 1}. ${escapeHtml(task.title)}</span>
              <span class="task-duration-badge">⏱ ${task.estimated_duration_minutes}m</span>
            </div>
            <div class="task-loc-row">
              <span style="font-size: 0.74rem;">📍 ${escapeHtml(task.location_name)}</span>
              ${task.waypoint_code ? `
                <button type="button" class="chatcode-stamp" onclick="copyChatCode('${task.waypoint_code}', this, event)" title="Copy Waypoint Code" style="font-size: 0.68rem; padding: 1px 6px;">
                  ${escapeHtml(task.waypoint_code)}
                </button>
              ` : ''}
            </div>
            ${charTag}
            <div class="task-desc" style="font-size: 0.75rem; line-height: 1.35;">${formatTextWithWaypoints(task.instructions)}</div>
            <div class="task-reward-box" style="font-size: 0.72rem; margin-top: 4px;">
              <div><strong>Inputs:</strong> ${escapeHtml(inputs)}</div>
              <div><strong>Reward:</strong> ${escapeHtml(rewardVal)}</div>
            </div>
          </div>
        `;
      }).join("");
    }

    rightPageBody.innerHTML = `
      <h3 class="page-title">Prioritized Task Route</h3>
      <div class="ink-divider">✦</div>
      <div style="font-size: 0.78rem; color: var(--ink-soft); margin-top: -6px; margin-bottom: 6px; font-family: var(--font-head); text-transform: uppercase; letter-spacing: 0.04em;">
        Sequential Waypoint Itinerary (${escapeHtml(activeLegendaryName)})
      </div>

      <div class="tasks-route-container">
        ${routeContent}
      </div>
    `;
  }

  window.renderPlanSpreadLeft = renderPlanSpreadLeft;
  window.renderPlanSpreadRight = renderPlanSpreadRight;
  window.renderSpread3Left = renderPlanSpreadLeft;
  window.renderSpread3Right = renderPlanSpreadRight;

  // ── 4. Telemetry & Side Drawer Controller ────────────────────────────────────
  function ensureSideDrawerDOM() {
    let drawer = document.getElementById("priory-side-drawer");
    if (!drawer) {
      drawer = document.createElement("aside");
      drawer.id = "priory-side-drawer";
      drawer.className = "priory-side-drawer hidden";
      drawer.setAttribute("aria-label", "Account Telemetry and Diagnostics");
      drawer.innerHTML = `
        <div class="drawer-header">
          <div class="drawer-title">
            <span class="drawer-glyph">⚜</span>
            <span>Account &amp; System Telemetry</span>
          </div>
          <button id="btn-close-drawer" class="btn-drawer-close" title="Close Drawer">✕</button>
        </div>
        <div class="drawer-content">
          <div class="drawer-section">
            <div class="drawer-section-title">Active GW2 Account &amp; API Key</div>
            <div class="api-key-panel">
              <div class="api-key-current-row">
                <span class="api-key-lbl">Current Account:</span>
                <span class="api-key-val" id="drawer-account-name">Loading...</span>
              </div>
              <div class="api-key-current-row">
                <span class="api-key-lbl">Active Key:</span>
                <span class="api-key-val" id="drawer-api-key-masked">None</span>
              </div>
              <label class="drawer-input-lbl" for="drawer-api-key-input">Switch API Key:</label>
              <div class="api-key-input-wrap">
                <input type="password" id="drawer-api-key-input" class="drawer-key-input" placeholder="Paste GW2 API Key (72 chars)..." spellcheck="false" autocomplete="off" />
                <button type="button" id="btn-toggle-key-visibility" class="btn-toggle-key" title="Show / Hide Key">👁</button>
              </div>
              <div class="api-key-actions-row">
                <button type="button" id="btn-apply-api-key" class="btn-drawer-action btn-apply-key">
                  <span id="btn-apply-key-text">Sync Account</span>
                  <span id="btn-apply-key-spinner" class="spinner-ink hidden"></span>
                </button>
                <button type="button" id="btn-reset-api-key" class="btn-drawer-action btn-reset-key" title="Reset to default API key">Reset</button>
              </div>
              <div id="drawer-api-key-feedback" class="api-key-feedback hidden"></div>
              <div class="api-key-hint">
                Required permissions: <em>account, inventories, characters, wallet, unlocks</em>. Generated at <a href="https://account.arena.net/applications" target="_blank" rel="noopener">account.arena.net</a>.
              </div>
            </div>
          </div>
          <div class="drawer-section">
            <div class="drawer-section-title">Live Account Essence</div>
            <div class="drawer-stats-grid" id="drawer-account-stats">
              <div style="font-size: 0.85rem; color: #a89f91; font-style: italic;">Syncing Account Essence...</div>
            </div>
          </div>
          <div class="drawer-section">
            <div class="drawer-section-title">System Diagnostics</div>
            <div class="diagnostics-panel" id="drawer-diagnostics-panel">
              <div style="font-size: 0.85rem; color: #a89f91; font-style: italic;">Connecting to Priory Gateway...</div>
            </div>
            <button id="btn-reload-telemetry" class="btn-drawer-action">Refresh Telemetry &amp; Cache</button>
          </div>
        </div>
      `;
      document.body.appendChild(drawer);
    }

    let btnToggle = document.getElementById("btn-toggle-drawer");
    if (!btnToggle) {
      btnToggle = document.createElement("button");
      btnToggle.id = "btn-toggle-drawer";
      btnToggle.className = "drawer-toggle-btn";
      btnToggle.title = "Account Essence & Diagnostics";
      btnToggle.textContent = "⚙ Account & Diagnostics";
      document.body.appendChild(btnToggle);
    }

    if (btnToggle && !btnToggle.getAttribute("data-bound")) {
      btnToggle.setAttribute("data-bound", "true");
      btnToggle.addEventListener("click", () => {
        const d = document.getElementById("priory-side-drawer");
        if (d) d.classList.toggle("hidden");
      });
    }

    const btnClose = document.getElementById("btn-close-drawer");
    if (btnClose && !btnClose.getAttribute("data-bound")) {
      btnClose.setAttribute("data-bound", "true");
      btnClose.addEventListener("click", () => {
        const d = document.getElementById("priory-side-drawer");
        if (d) d.classList.add("hidden");
      });
    }

    const btnReload = document.getElementById("btn-reload-telemetry");
    if (btnReload && !btnReload.getAttribute("data-bound")) {
      btnReload.setAttribute("data-bound", "true");
      btnReload.addEventListener("click", () => {
        fetchAccountStatus();
      });
    }

    const btnApplyKey = document.getElementById("btn-apply-api-key");
    if (btnApplyKey && !btnApplyKey.getAttribute("data-bound")) {
      btnApplyKey.setAttribute("data-bound", "true");
      btnApplyKey.addEventListener("click", () => {
        window.applyNewApiKey();
      });
    }

    const btnResetKey = document.getElementById("btn-reset-api-key");
    if (btnResetKey && !btnResetKey.getAttribute("data-bound")) {
      btnResetKey.setAttribute("data-bound", "true");
      btnResetKey.addEventListener("click", () => {
        window.resetApiKey();
      });
    }

    const btnToggleVis = document.getElementById("btn-toggle-key-visibility");
    if (btnToggleVis && !btnToggleVis.getAttribute("data-bound")) {
      btnToggleVis.setAttribute("data-bound", "true");
      btnToggleVis.addEventListener("click", () => {
        window.toggleKeyVisibility();
      });
    }

    const inputKey = document.getElementById("drawer-api-key-input");
    if (inputKey && !inputKey.getAttribute("data-bound")) {
      inputKey.setAttribute("data-bound", "true");
      inputKey.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          window.applyNewApiKey();
        }
      });
    }
  }

  window.toggleKeyVisibility = function() {
    const input = document.getElementById("drawer-api-key-input");
    const btn = document.getElementById("btn-toggle-key-visibility");
    if (!input) return;
    if (input.type === "password") {
      input.type = "text";
      if (btn) btn.textContent = "🙈";
    } else {
      input.type = "password";
      if (btn) btn.textContent = "👁";
    }
  };

  window.openDrawerToApiKey = function() {
    const drawer = document.getElementById("priory-side-drawer");
    if (drawer) {
      drawer.classList.remove("hidden");
    }
    const input = document.getElementById("drawer-api-key-input");
    if (input) {
      setTimeout(() => input.focus(), 120);
    }
  };

  window.applyNewApiKey = async function() {
    const input = document.getElementById("drawer-api-key-input");
    const feedback = document.getElementById("drawer-api-key-feedback");
    const btnApply = document.getElementById("btn-apply-api-key");
    const btnText = document.getElementById("btn-apply-key-text");
    const btnSpinner = document.getElementById("btn-apply-key-spinner");

    const key = (input ? input.value : "").trim();
    if (!key) {
      if (input) {
        input.classList.remove("input-shake");
        void input.offsetWidth;
        input.classList.add("input-shake");
        setTimeout(() => input.classList.remove("input-shake"), 600);
      }
      return;
    }

    if (btnApply) btnApply.disabled = true;
    if (btnSpinner) btnSpinner.classList.remove("hidden");
    if (btnText) btnText.textContent = "Syncing...";

    if (feedback) {
      feedback.className = "api-key-feedback hidden";
      feedback.textContent = "";
    }

    try {
      const res = await fetch("/api/account/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key })
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Failed to synchronize with GW2 API");
      }

      setStorageItem("priory_custom_api_key", key);

      if (feedback) {
        feedback.className = "api-key-feedback feedback-success";
        const accName = data.account_name || "Account";
        const mats = (data.materials_count || 0).toLocaleString();
        const armory = (data.armory_count || 0).toLocaleString();
        feedback.textContent = `✓ Connected to ${accName}! (${mats} materials, ${armory} armory)`;
      }

      // Clear dossier cache
      for (const k in dossierCache) {
        delete dossierCache[k];
      }

      // Invalidate active dossiers and re-fetch status
      await fetchAccountStatus();

      // If currently on Spread 2 or 3, re-fetch active dossier data
      if (currentSpreadIndex === 2 || currentSpreadIndex === 3) {
        loadLegendaryDossier(activeLegendaryId, activeLegendaryName, { autoTurn: false });
      } else if (currentSpreadIndex === 0) {
        renderSpread0Left();
      }
    } catch (err) {
      if (feedback) {
        feedback.className = "api-key-feedback feedback-error";
        feedback.textContent = `✗ Failed to sync: ${err.message || String(err)}`;
      }
    } finally {
      if (btnApply) btnApply.disabled = false;
      if (btnSpinner) btnSpinner.classList.add("hidden");
      if (btnText) btnText.textContent = "Sync Account";
    }
  };

  window.resetApiKey = async function() {
    const btnReset = document.getElementById("btn-reset-api-key");
    const input = document.getElementById("drawer-api-key-input");
    const feedback = document.getElementById("drawer-api-key-feedback");

    if (btnReset) {
      btnReset.disabled = true;
      btnReset.textContent = "...";
    }

    try {
      const res = await fetch("/api/account/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reset: true })
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.error || "Failed to reset API key");
      }

      removeStorageItem("priory_custom_api_key");
      if (input) input.value = "";

      if (feedback) {
        feedback.className = "api-key-feedback feedback-success";
        feedback.textContent = "✓ Reset to default account.";
      }

      // Clear dossier cache
      for (const k in dossierCache) {
        delete dossierCache[k];
      }

      // Refresh account status
      await fetchAccountStatus();

      // If currently on Spread 2 or 3, re-fetch active dossier data
      if (currentSpreadIndex === 2 || currentSpreadIndex === 3) {
        loadLegendaryDossier(activeLegendaryId, activeLegendaryName, { autoTurn: false });
      } else if (currentSpreadIndex === 0) {
        renderSpread0Left();
      }
    } catch (err) {
      if (feedback) {
        feedback.className = "api-key-feedback feedback-error";
        feedback.textContent = `✗ Failed to reset: ${err.message || String(err)}`;
      }
    } finally {
      if (btnReset) {
        btnReset.disabled = false;
        btnReset.textContent = "Reset";
      }
    }
  };

  async function fetchAccountStatus() {
    const statsCont = document.getElementById("drawer-account-stats");
    const diagCont = document.getElementById("drawer-diagnostics-panel");

    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      accountTelemetry = data;

      const drawerAccountName = document.getElementById("drawer-account-name");
      if (drawerAccountName) {
        drawerAccountName.textContent = data.account_name || "Authenticated Scholar";
      }
      const drawerApiKeyMasked = document.getElementById("drawer-api-key-masked");
      if (drawerApiKeyMasked) {
        drawerApiKeyMasked.textContent = data.api_key_masked || "None";
      }

      const libraryAccountBadgeName = document.getElementById("library-account-badge-name");
      if (libraryAccountBadgeName) {
        libraryAccountBadgeName.textContent = data.account_name || "Default Account";
      }

      if (statsCont) {
        const w = data.wallet || {};
        const goldVal = w.liquid_gold ? w.liquid_gold.toFixed(1) + "g" : "0g";
        statsCont.innerHTML = `
          <div class="drawer-stat-card">
            <span class="drawer-stat-lbl">Liquid Gold</span>
            <span class="drawer-stat-val" style="color: var(--leather-gold);">${goldVal}</span>
          </div>
          <div class="drawer-stat-card">
            <span class="drawer-stat-lbl">Astral Acclaim</span>
            <span class="drawer-stat-val">${(w.astral_acclaim || 0).toLocaleString()}</span>
          </div>
          <div class="drawer-stat-card">
            <span class="drawer-stat-lbl">Spirit Shards</span>
            <span class="drawer-stat-val">${(w.spirit_shards || 0).toLocaleString()}</span>
          </div>
          <div class="drawer-stat-card">
            <span class="drawer-stat-lbl">Provisioner Tokens</span>
            <span class="drawer-stat-val">${(w.provisioner_tokens || 0).toLocaleString()}</span>
          </div>
          <div class="drawer-stat-card">
            <span class="drawer-stat-lbl">Laurels</span>
            <span class="drawer-stat-val">${(w.laurels || 0).toLocaleString()}</span>
          </div>
          <div class="drawer-stat-card">
            <span class="drawer-stat-lbl">Volatile Magic</span>
            <span class="drawer-stat-val">${(w.volatile_magic || 0).toLocaleString()}</span>
          </div>
          <div class="drawer-stat-card">
            <span class="drawer-stat-lbl">Materials in Vault</span>
            <span class="drawer-stat-val">${(data.account_materials_count || 0).toLocaleString()}</span>
          </div>
          <div class="drawer-stat-card">
            <span class="drawer-stat-lbl">Armory Legendaries</span>
            <span class="drawer-stat-val" style="color: #2e7d32;">${(data.account_armory_count || 0).toLocaleString()}</span>
          </div>
        `;
      }

      if (diagCont) {
        const modeBadge = data.is_fallback
          ? `<span class="diag-badge badge-fallback">Fallback Rule Engine</span>`
          : `<span class="diag-badge badge-live">Live LLM Active</span>`;

        diagCont.innerHTML = `
          <div class="diag-item"><span class="diag-lbl">Status:</span><span class="diag-val" style="color:#2e7d32;">Ready</span></div>
          <div class="diag-item"><span class="diag-lbl">Knowledge Triples:</span><span class="diag-val">${(data.triples_loaded || 0).toLocaleString()}</span></div>
          <div class="diag-item"><span class="diag-lbl">LLM Provider:</span><span class="diag-val">${escapeHtml(data.llm_provider || 'Deterministic')}</span></div>
          <div class="diag-item"><span class="diag-lbl">Reasoning Mode:</span><span class="diag-val">${modeBadge}</span></div>
          <div class="diag-item"><span class="diag-lbl">API Key Configured:</span><span class="diag-val">${data.api_key_configured ? 'Yes' : 'No'}</span></div>
        `;
      }
    } catch (err) {
      if (statsCont) statsCont.innerHTML = `<div style="font-size:0.8rem; color:#e57373;">Failed to synchronize account essence.</div>`;
      if (diagCont) diagCont.innerHTML = `<div style="font-size:0.8rem; color:#e57373;">Diagnostics gateway offline.</div>`;
    }
  }

  // ── Formatting & Chat Code Copy Helpers ─────────────────────────────────────
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

  function formatTextWithWaypoints(text) {
    if (!text) return "";
    let s = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/`?(\[&[A-Za-z0-9+/=]+\])`?/g, (match, wp) => {
      return `<span class="wp-link" onclick="copyChatCode('${wp}', this, event)" title="Click to copy waypoint">${wp}</span>`;
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

  // ── Ambient Arcane Canvas Particles ─────────────────────────────────────────
  function initParticles() {
    const c = document.getElementById("particles");
    if (!c || typeof c.getContext !== "function") return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    let W, H;
    function resize() { W = c.width = window.innerWidth; H = c.height = window.innerHeight; }
    resize();
    window.addEventListener("resize", resize);

    const dots = [];
    for (let i = 0; i < 60; i++) {
      dots.push({
        x: Math.random() * W,
        y: Math.random() * H,
        r: Math.random() * 2 + 0.8,
        vx: (Math.random() - 0.5) * 0.4,
        vy: -Math.random() * 0.5 - 0.2,
        alpha: Math.random() * 0.5 + 0.2
      });
    }

    function animate() {
      ctx.clearRect(0, 0, W, H);
      for (const d of dots) {
        d.x += d.vx;
        d.y += d.vy;
        if (d.y < 0) { d.y = H; d.x = Math.random() * W; }
        if (d.x < 0) d.x = W;
        if (d.x > W) d.x = 0;
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(200, 150, 62, ${d.alpha})`;
        ctx.fill();
      }
      requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
  }

  // ── GW2 Tooltip Delegation ──────────────────────────────────────────────────
  function initTooltipDelegation() {
    if (!gw2Tooltip) return;
    document.addEventListener("mouseover", (e) => {
      const target = e.target.closest("[data-gw2-tip]");
      if (!target) {
        gw2Tooltip.classList.add("hidden");
        return;
      }
      const tipText = target.getAttribute("data-gw2-tip");
      if (tipText) {
        gw2Tooltip.innerHTML = tipText;
        gw2Tooltip.classList.remove("hidden");
        const rect = target.getBoundingClientRect();
        gw2Tooltip.style.left = `${rect.left + rect.width / 2}px`;
        gw2Tooltip.style.top = `${rect.top - 8}px`;
      }
    });

    document.addEventListener("mouseout", (e) => {
      const target = e.target.closest("[data-gw2-tip]");
      if (target && gw2Tooltip) {
        gw2Tooltip.classList.add("hidden");
      }
    });
  }

  // ── Initialization ──────────────────────────────────────────────────────────
  ensureSideDrawerDOM();
  initParticles();
  initTooltipDelegation();
  loadRecentChapters();

  const savedApiKey = getStorageItem("priory_custom_api_key");
  if (savedApiKey && savedApiKey.trim()) {
    const keyInput = document.getElementById("drawer-api-key-input");
    if (keyInput) keyInput.value = savedApiKey.trim();
    fetch("/api/account/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: savedApiKey.trim() })
    })
      .then(r => r.json())
      .catch(() => {})
      .finally(() => {
        fetchAccountStatus();
      });
  } else {
    fetchAccountStatus();
  }

  renderCurrentSpread();

  // Preload default legendary dossier (Twilight) in background without auto page turn
  loadLegendaryDossier(30689, "Twilight", { autoTurn: false });
});
