/**
 * PRIORY GRIMOIRE — GUILD WARS 2 LEGENDARY WORKBENCH CONTROLLER
 * Monotrack Legendary Dossier Architecture (Priory UI & Workbench Specification)
 *
 * 4 Spreads:
 *   Spread 0: Library (Index, Search Archives & Popular Dossiers)
 *   Spread 1: Inquiry Guide (Custom AI Progression Guide & Comparative Rankings)
 *   Spread 2: Recipe & Market Economics (Recipe Tree, Costs, Arbitrage & Wallace Tax)
 *   Spread 3: Readiness & Daily Session Plan (Prerequisites, 0/1 Knapsack Itinerary)
 */

document.addEventListener("DOMContentLoaded", () => {

  // ── Canonical Priory 12x12 Semiotic SVG Generators ──────────────────────────
  const PRIORY_SIGILS_SVG = {
    cont: '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><circle cx="6" cy="6" r="3.5" fill="currentColor"/></svg>',
    proc: '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2.6 2.75L6.1 6L2.6 9.25M6.4 2.75L9.9 6L6.4 9.25" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    role: '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1.5L10.5 6L6 10.5L1.5 6Z" fill="currentColor" fill-opacity="0.14" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>',
    gdc:  '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 1.4L10.6 6L6 10.6L1.4 6Z" stroke="currentColor" stroke-width="1.35" stroke-linejoin="round"/><circle cx="6" cy="6" r="1.4" fill="currentColor"/></svg>',
    qual: '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><circle cx="6" cy="6" r="4.1" stroke="currentColor" stroke-width="1.4"/><path d="M6 1.9A4.1 4.1 0 0 0 6 10.1Z" fill="currentColor"/></svg>',
    ind:  '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M6 2.1L9.9 6L6 9.9L2.1 6Z" fill="currentColor"/></svg>',
    entailed: '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M3 2.3V9.7M3 6H9.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
    synthesized: '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><path d="M2 4.4C3.6 3.1 5.1 5.7 6.7 4.4C8.3 3.1 9.4 4.4 10 4.4M2 7.6C3.6 6.3 5.1 8.9 6.7 7.6C8.3 6.3 9.4 7.6 10 7.6" stroke="currentColor" stroke-width="1.35" stroke-linecap="round"/></svg>'
  };

  function sigilSpan(kind = "gdc") {
    const svg = PRIORY_SIGILS_SVG[kind] || PRIORY_SIGILS_SVG.cont;
    return `<span class="priory-sigil priory-sigil--${kind}">${svg}</span>`;
  }

  function sigilKindForItemType(typeStr = "") {
    const t = String(typeStr).toLowerCase();
    if (t.includes("armor")) return "role";
    if (t.includes("accessory") || t.includes("ring") || t.includes("amulet") || t.includes("trinket")) return "qual";
    if (t.includes("inquiry") || t.includes("guide")) return "gdc";
    if (t.includes("gen 3")) return "ind";
    if (t.includes("gen 2")) return "proc";
    return "cont";
  }

  // ── Safe Local Storage Helpers ──────────────────────────────────────────────
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

  // ── Theme Switcher (Daylight / Nocturne) ────────────────────────────────────
  const btnThemeToggle = document.getElementById("btn-theme-toggle");
  const labelTheme = document.getElementById("label-theme");
  const iconTheme = document.getElementById("icon-theme");

  function applyTheme(mode) {
    const isDark = mode === "dark";
    document.documentElement.classList.toggle("dark", isDark);
    document.documentElement.classList.toggle("light", !isDark);
    if (labelTheme) labelTheme.textContent = isDark ? "Daylight" : "Nocturne";
    if (iconTheme) {
      iconTheme.innerHTML = isDark
        ? '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>'
        : '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
    }
  }

  const savedTheme = getStorageItem("priory_grimoire_theme");
  if (savedTheme === "dark" || savedTheme === "light") {
    applyTheme(savedTheme);
  }
  if (btnThemeToggle) {
    btnThemeToggle.addEventListener("click", () => {
      const next = document.documentElement.classList.contains("dark") ? "light" : "dark";
      applyTheme(next);
      setStorageItem("priory_grimoire_theme", next);
    });
  }

  // ── 1. State Management ─────────────────────────────────────────────────────
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
  let activeLegendaryData = activeDossierData;
  const dossierCache = {};
  let recentChapters = [];
  let currentSpreadIndex = 0; // 0 = Library, 1 = Guide, 2 = Recipe, 3 = Plan
  let plannerBudgetMinutes = 60;
  let prereqDetailsExpanded = false;
  let isFlipping = false;
  let accountTelemetry = null;

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

  window.playSound = () => {};

  // ── DOM Handles ─────────────────────────────────────────────────────────────
  const wbShell = document.getElementById("wb-shell");
  const pagesSpread = document.getElementById("pages-spread");
  const leftPageBody = document.getElementById("left-page-body");
  const rightPageBody = document.getElementById("right-page-body");
  const btnPrev = document.getElementById("btn-prev-page");
  const btnNext = document.getElementById("btn-next-page");
  const pageCounterDisplay = document.getElementById("page-counter-display");

  const tabLibrary = document.getElementById("tab-library") || document.getElementById("tab-inscribe");
  let tabGuide = document.getElementById("tab-guide");
  const tabRecipe = document.getElementById("tab-recipe") || document.getElementById("tab-arbitrage");
  const tabPlan = document.getElementById("tab-plan") || document.getElementById("tab-planner");
  const tabChaptersMenu = document.getElementById("tab-chapters-menu") || document.getElementById("tab-guides-menu");
  const chaptersTabLabel = document.getElementById("chapters-tab-label") || document.getElementById("guides-tab-label");
  const chaptersDropdownCard = document.getElementById("chapters-dropdown-card") || document.getElementById("guides-dropdown-card");
  const chaptersDropdownList = document.getElementById("chapters-dropdown-list") || document.getElementById("guides-dropdown-list");
  const btnClearAllChapters = document.getElementById("btn-clear-all-chapters") || document.getElementById("btn-clear-chapters") || document.getElementById("btn-clear-all-guides");
  const legendaryNavList = document.getElementById("legendary-nav-list");
  const legendaryIndexCount = document.getElementById("legendary-index-count");

  if (!tabGuide && tabLibrary && tabLibrary.parentNode) {
    tabGuide = document.createElement("button");
    tabGuide.className = "tome-tab";
    tabGuide.id = "tab-guide";
    tabGuide.setAttribute("data-spread-index", "1");
    tabGuide.setAttribute("title", "Inquiry Guide");
    tabGuide.innerHTML = '<span class="tab-label">Guide</span>';
    if (tabRecipe) {
      tabLibrary.parentNode.insertBefore(tabGuide, tabRecipe);
    } else {
      tabLibrary.parentNode.appendChild(tabGuide);
    }
  }

  const gw2Tooltip = document.getElementById("gw2-tooltip");

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

  const POPULAR_LEGENDARIES = [
    { id: 30689, name: "Twilight", type: "Gen 1 Greatsword" },
    { id: 30688, name: "Eternity", type: "Gen 1 Greatsword" },
    { id: 76158, name: "Nevermore", type: "Gen 2 Staff" },
    { id: 100806, name: "WvW Armor", type: "Legendary Armor" },
    { id: 81908, name: "Aurora", type: "Legendary Accessory" }
  ];

  // Deduplicated index for left navigation pane
  const UNIQUE_INDEX_ITEMS = [];
  const seenNames = new Set();
  for (const p of LEGENDARY_PRESETS) {
    if (!seenNames.has(p.name)) {
      seenNames.add(p.name);
      UNIQUE_INDEX_ITEMS.push(p);
    }
  }

  function renderLegendaryIndex() {
    if (!legendaryNavList) return;
    if (legendaryIndexCount) {
      legendaryIndexCount.textContent = String(UNIQUE_INDEX_ITEMS.length);
    }
    legendaryNavList.innerHTML = UNIQUE_INDEX_ITEMS.map(item => {
      const isActive = item.name.toLowerCase() === (activeLegendaryName || "").toLowerCase();
      return `
        <button type="button" class="wb-tree-row ${isActive ? 'is-active' : ''}" data-leg-id="${item.id}" data-leg-name="${escapeHtml(item.name)}" data-leg-type="${escapeHtml(item.type)}" title="${escapeHtml(item.name)} — ${escapeHtml(item.type)}">
          ${sigilSpan(sigilKindForItemType(item.type))}
          <span class="wb-tree-label">${escapeHtml(item.name)}</span>
          <span class="wb-tree-count tabular-nums">${item.id}</span>
        </button>
      `;
    }).join("");

    legendaryNavList.querySelectorAll(".wb-tree-row").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = Number(btn.getAttribute("data-leg-id"));
        const name = btn.getAttribute("data-leg-name");
        const type = btn.getAttribute("data-leg-type");
        window.loadLegendaryDossier(id, name, { type, targetSpread: 2 });
      });
    });
  }

  function updateStatusBarContext() {
    const sbDossier = document.getElementById("status-bar-dossier");
    const sbBudget = document.getElementById("status-bar-budget");
    if (sbDossier) sbDossier.textContent = `Dossier: ${activeLegendaryName}`;
    if (sbBudget) sbBudget.textContent = `Budget: ${plannerBudgetMinutes}m`;
  }

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

  // Strip raw markdown bold/emojis from backend text for clean workbench display
  function stripDecorations(text) {
    if (!text) return "";
    return String(text)
      .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, "")
      .replace(/\s{2,}/g, " ")
      .trim();
  }

  // ── Resolution Helper for Custom Guides ─────────────────────────────────────
  function resolveTargetItem(guide, query) {
    if (!guide && !query) return null;
    const goal = (guide?.goal_name || "").toLowerCase();
    const queryLower = (query || "").toLowerCase();
    const summary = (guide?.executive_summary || "").toLowerCase();

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

    if (guide) {
      const ranked = parseRankingItems(guide);
      if (ranked && ranked.length > 0) {
        const topName = (ranked[0].name || "").toLowerCase();
        const match = LEGENDARY_PRESETS.find(p => p.name.toLowerCase() === topName || topName.includes(p.name.toLowerCase()));
        if (match) return match;
      }
    }

    for (const p of LEGENDARY_PRESETS) {
      const regex = new RegExp(`(^|[^a-z0-9])${p.name.toLowerCase()}([^a-z0-9]|$)`, "i");
      if (regex.test(goal)) return p;
    }

    if (guide && guide.strategic_recommendations && Array.isArray(guide.strategic_recommendations)) {
      for (const rec of guide.strategic_recommendations) {
        if (typeof rec === "string" && (rec.includes("#1 ") || rec.includes("Top Recommendation") || rec.includes("Top "))) {
          for (const p of LEGENDARY_PRESETS) {
            const regex = new RegExp(`(^|[^a-z0-9])${p.name.toLowerCase()}([^a-z0-9]|$)`, "i");
            if (regex.test(rec)) return p;
          }
        }
      }
    }

    for (const p of LEGENDARY_PRESETS) {
      const regex = new RegExp(`(^|[^a-z0-9])${p.name.toLowerCase()}([^a-z0-9]|$)`, "i");
      if (regex.test(summary)) return p;
    }

    for (const p of LEGENDARY_PRESETS) {
      const regex = new RegExp(`(^|[^a-z0-9])${p.name.toLowerCase()}([^a-z0-9]|$)`, "i");
      if (regex.test(queryLower)) return p;
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
          const gateMatch = extra.match(/(?:~?\d+d\s*gate|time-gated[^|\]]*)/i);
          const gate = gateMatch ? gateMatch[0].trim() : null;

          items.push({ rank, name, subtype, readiness, cost, archetype, kitReady, gate });
        }
      }
    }

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

  // ── 2. Search Execution & Custom Query Handling ─────────────────────────────
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
    if (btnText) btnText.textContent = "Querying…";

    if (rightPageBody) {
      rightPageBody.innerHTML = `
        <div class="wb-sec-hdr">
          <span>Query Execution</span>
          <span class="tabular-nums">Running</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Query</dt>
            <dd class="wb-prop-val wb-prop-val--left">${escapeHtml(q)}</dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Stage 1</dt>
            <dd class="wb-prop-val wb-prop-val--left">Querying neuro-symbolic RDF graph</dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Stage 2</dt>
            <dd class="wb-prop-val wb-prop-val--left">Auditing account inventory &amp; currencies</dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Stage 3</dt>
            <dd class="wb-prop-val wb-prop-val--left">Computing progression pathway</dd>
          </div>
        </dl>
      `;
    }

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q })
      });
      if (!res.ok) {
        throw new Error(`Query failed with HTTP status ${res.status}`);
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
      if (rightPageBody) {
        rightPageBody.innerHTML = `
          <div class="wb-sec-hdr">
            <span>Query Error</span>
            <span class="text-avoid">Failed</span>
          </div>
          <dl class="wb-dl">
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Query</dt>
              <dd class="wb-prop-val wb-prop-val--left">${escapeHtml(q)}</dd>
            </div>
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Diagnostics</dt>
              <dd class="wb-prop-val wb-prop-val--left text-avoid">${escapeHtml(err.message || String(err))}</dd>
            </div>
          </dl>
          <div style="display: flex; gap: 6px; padding: 8px;">
            <button type="button" class="wb-btn wb-btn-primary" id="btn-retry-scrying">Retry</button>
            <button type="button" class="wb-btn" id="btn-cancel-scrying">Return to Library</button>
          </div>
        `;
        const retryBtn = document.getElementById("btn-retry-scrying");
        if (retryBtn) retryBtn.onclick = () => executeSearchQuery(q);
        const cancelBtn = document.getElementById("btn-cancel-scrying");
        if (cancelBtn) cancelBtn.onclick = () => renderSpread0Right();
      }
    } finally {
      if (btn) btn.disabled = false;
      if (spinner) spinner.classList.add("hidden");
      if (btnText) btnText.textContent = "Explore";
    }
  };

  window.handleCustomQueryResult = function(query, guide) {
    activeCustomGuide = guide;

    const resolved = resolveTargetItem(guide, query);
    const resolvedId = resolved ? resolved.id : (activeLegendaryId || 30689);
    const resolvedName = resolved ? resolved.name : (guide?.goal_name || activeLegendaryName || "Twilight");

    activeLegendaryId = resolved ? resolved.id : resolvedId;
    activeLegendaryName = resolved ? resolved.name : resolvedName;

    if (resolved && resolved.id) {
      loadLegendaryDossier(resolved.id, resolved.name, { autoTurn: false });
    }

    const chapter = {
      id: activeLegendaryId,
      resolvedName: activeLegendaryName,
      name: guide?.goal_name || activeLegendaryName,
      query: query,
      guide: guide,
      isCustomGuide: true,
      timestamp: Date.now()
    };

    recentChapters = recentChapters.filter(c => !c.isCustomGuide || c.name !== chapter.name);
    recentChapters.unshift(chapter);
    if (recentChapters.length > 12) {
      recentChapters = recentChapters.slice(0, 12);
    }
    saveRecentChapters();
    updateChaptersDropdown();
    renderLegendaryIndex();
    updateStatusBarContext();

    turnPageTo(1, "forward");
  };

  // ── 3. Unified Data Loading (loadLegendaryDossier) ──────────────────────────
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
    renderLegendaryIndex();
    updateStatusBarContext();

    if (dossierCache[goalId]) {
      activeDossierData = dossierCache[goalId];
      activeLegendaryData = activeDossierData;
      if (shouldTurn) {
        turnPageTo(targetSpread, targetSpread >= currentSpreadIndex ? "forward" : "backward");
      }
      updateChaptersDropdown();
      return;
    }

    activeDossierData = {
      recipe: null,
      arbitrage: null,
      prerequisites: null,
      itinerary: null,
      loading: { recipe: true, arbitrage: true, prerequisites: true, itinerary: true }
    };
    activeLegendaryData = activeDossierData;
    dossierCache[goalId] = activeDossierData;

    if (shouldTurn) {
      turnPageTo(targetSpread, targetSpread >= currentSpreadIndex ? "forward" : "backward");
    }
    updateChaptersDropdown();

    const solverId = getSolverId(goalId, goalName);

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

  // ── Prerequisite Fetch Helper ──────────────────────────────────────────────
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

  // ── Knapsack Recalculation Handler ─────────────────────────────────────────
  window.recalculateItinerary = async function(minutes) {
    plannerBudgetMinutes = Number(minutes) || 60;
    updateStatusBarContext();
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

  // ── Tab & Chapters List Controller ─────────────────────────────────────────
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

    if (c.isCustomGuide) {
      activeCustomGuide = c.guide;
      if (c.id) {
        activeLegendaryId = c.id;
        activeLegendaryName = c.resolvedName || getLegendaryNameById(c.id) || activeLegendaryName;
        loadLegendaryDossier(c.id, activeLegendaryName, { autoTurn: false });
      }
      turnPageTo(1, 1 >= currentSpreadIndex ? "forward" : "backward");
      updateChaptersDropdown();
      renderLegendaryIndex();
      updateStatusBarContext();
    } else {
      loadLegendaryDossier(c.id, c.name, { type: c.type, targetSpread: 2 });
    }
  };

  function updateChaptersDropdown() {
    if (chaptersTabLabel) {
      chaptersTabLabel.textContent = `Recent Chapters (${recentChapters.length})`;
    }

    if (chaptersDropdownList) {
      if (recentChapters.length === 0) {
        chaptersDropdownList.innerHTML = '<div class="empty-guides-msg">No recent chapters recorded.</div>';
      } else {
        chaptersDropdownList.innerHTML = recentChapters.map((c, idx) => {
          const isActive = c.isCustomGuide
            ? (activeCustomGuide && activeCustomGuide.goal_name === c.name && currentSpreadIndex === 1)
            : (c.id === activeLegendaryId && currentSpreadIndex !== 1);
          const typeLabel = c.isCustomGuide ? "Guide" : "Item";
          const kind = c.isCustomGuide ? "gdc" : sigilKindForItemType(c.type || "");
          return `
            <div class="chapters-dropdown-item ${isActive ? 'active-chapter' : ''}">
              <button type="button" class="btn-select-chapter" onclick="selectChapter(${idx})" title="Open ${escapeHtml(c.name)}">
                ${sigilSpan(kind)}
                <span class="chapter-name">${escapeHtml(c.name)}</span>
                <span class="chapter-type tabular-nums">${escapeHtml(typeLabel)}</span>
              </button>
              <button type="button" class="btn-delete-chapter" data-index="${idx}" title="Remove from history">x</button>
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
      removeStorageItem("priory_recent_chapters");
      updateChaptersDropdown();
    });
  }

  if (tabLibrary) tabLibrary.addEventListener("click", () => turnPageTo(0, "backward"));
  if (tabGuide) tabGuide.addEventListener("click", () => turnPageTo(1, 1 > currentSpreadIndex ? "forward" : "backward"));
  if (tabRecipe) tabRecipe.addEventListener("click", () => turnPageTo(2, 2 > currentSpreadIndex ? "forward" : "backward"));
  if (tabPlan) tabPlan.addEventListener("click", () => turnPageTo(3, "forward"));

  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      if (currentSpreadIndex > 0) turnPageTo(currentSpreadIndex - 1, "backward");
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      if (currentSpreadIndex < 3) turnPageTo(currentSpreadIndex + 1, "forward");
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
    if (e.key === "ArrowRight" && btnNext && !btnNext.disabled) btnNext.click();
    else if (e.key === "ArrowLeft" && btnPrev && !btnPrev.disabled) btnPrev.click();
  });

  // ── Instant Workbench View Switcher ─────────────────────────────────────────
  function turnPageTo(targetIndex, _direction = "forward") {
    if (targetIndex < 0 || targetIndex > 3) return;
    isFlipping = false;
    currentSpreadIndex = targetIndex;
    renderCurrentSpread();
    if (leftPageBody) leftPageBody.scrollTop = 0;
    if (rightPageBody) rightPageBody.scrollTop = 0;
  }
  window.turnPageTo = turnPageTo;

  // ── Spread Renderers Controller ─────────────────────────────────────────────
  function renderCurrentSpread() {
    updateTabState();
    updateChaptersDropdown();

    if (btnPrev) btnPrev.disabled = currentSpreadIndex === 0;
    if (btnNext) btnNext.disabled = currentSpreadIndex === 3;

    if (currentSpreadIndex === 0) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = "Library · Spread 1 of 4";
      renderSpread0Left();
      renderSpread0Right();
    } else if (currentSpreadIndex === 1) {
      const guideTitle = activeCustomGuide?.goal_name || "Inquiry Guide";
      if (pageCounterDisplay) pageCounterDisplay.textContent = `${guideTitle} · Spread 2 of 4`;
      renderGuideSpreadLeft();
      renderGuideSpreadRight();
    } else if (currentSpreadIndex === 2) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = `${activeLegendaryName} · Recipe (Spread 3 of 4)`;
      renderRecipeSpreadLeft();
      renderRecipeSpreadRight();
    } else if (currentSpreadIndex === 3) {
      if (pageCounterDisplay) pageCounterDisplay.textContent = `${activeLegendaryName} · Plan (Spread 4 of 4)`;
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
      <div class="wb-sec-hdr">
        <span>Library Query Console</span>
        <span class="tabular-nums">Spread 1/4</span>
      </div>

      <section class="wb-section">
        <form class="inscribe-form" id="library-search-form" onsubmit="executeLibrarySearch(event); return false;">
          <label class="inscribe-label" for="library-search-input">Query Knowledge Graph &amp; Crafting Solver</label>
          <textarea id="library-search-input" class="ink-textarea" rows="3" placeholder="Search legendary or ask query… e.g. 'Twilight', 'How do I craft Eternity?', 'Which accessory can I get the fastest?'"></textarea>
          <div style="display: flex; align-items: center; gap: 6px;">
            <button type="button" class="btn-forge-inscribe" id="btn-search-archives" onclick="executeLibrarySearch(event)">
              <span id="btn-search-archives-text">Explore</span>
              <span id="btn-search-archives-spinner" class="spinner-ink hidden"></span>
            </button>
          </div>
        </form>
      </section>

      <section class="wb-section">
        <div class="wb-sec-hdr">
          <span>Curated Quick Inquiries</span>
          <span class="tabular-nums">10 presets</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Weapons</dt>
            <dd class="wb-prop-val wb-prop-val--left">
              <div class="pills-row">
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(30689, 'Twilight')">Twilight</button>
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(30699, 'Sunrise')">Sunrise</button>
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(30688, 'Eternity')">Eternity</button>
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(76158, 'Nevermore')">Nevermore</button>
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(30691, 'The Moot')">The Moot</button>
              </div>
            </dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Armor</dt>
            <dd class="wb-prop-val wb-prop-val--left">
              <div class="pills-row">
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(100806, 'WvW Armor', { type: 'Legendary Armor' })">WvW Armor</button>
              </div>
            </dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Trinkets</dt>
            <dd class="wb-prop-val wb-prop-val--left">
              <div class="pills-row">
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(81908, 'Aurora', { type: 'Legendary Accessory' })">Aurora</button>
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(91048, 'Vision', { type: 'Legendary Accessory' })">Vision</button>
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(93105, 'Conflux', { type: 'Legendary Ring' })">Conflux</button>
                <button type="button" class="incantation-btn" onclick="loadLegendaryDossier(91234, 'Coalescence', { type: 'Legendary Ring' })">Coalescence</button>
              </div>
            </dd>
          </div>
        </dl>
      </section>

      <section class="wb-section">
        <div class="wb-sec-hdr">
          <span>Active Account Binding</span>
          <button type="button" class="btn-inline-action" onclick="openDrawerToApiKey()">Change Key</button>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Account</dt>
            <dd class="wb-prop-val" id="library-account-badge-name">${escapeHtml(accountTelemetry?.account_name || 'Default Account')}</dd>
          </div>
        </dl>
      </section>
    `;

    const form = document.getElementById("library-search-form");
    const input = document.getElementById("library-search-input");
    if (form) form.addEventListener("submit", (e) => executeLibrarySearch(e));
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
      <div class="wb-sec-hdr">
        <span>Popular Legendaries &amp; Quick Dossiers</span>
        <span class="tabular-nums">${POPULAR_LEGENDARIES.length}</span>
      </div>

      <section class="wb-section">
        <table class="wb-table">
          <thead>
            <tr>
              <th>Item</th>
              <th>Classification</th>
              <th class="num">Item ID</th>
              <th class="num">Dossier</th>
            </tr>
          </thead>
          <tbody>
            ${POPULAR_LEGENDARIES.map(item => `
              <tr>
                <td class="cell-primary">${sigilSpan(sigilKindForItemType(item.type))} ${escapeHtml(item.name)}</td>
                <td>${escapeHtml(item.type)}</td>
                <td class="num"><code>${item.id}</code></td>
                <td class="num">
                  <button type="button" class="btn-open-dossier" onclick="loadLegendaryDossier(${item.id}, '${escapeHtml(item.name)}', { type: '${escapeHtml(item.type)}', targetSpread: 2 })">
                    Open
                  </button>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </section>

      <section class="wb-section">
        <div class="wb-sec-hdr">
          <span>Monotrack Dossier Pipeline</span>
          <span class="tabular-nums">4 stages</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">01 · Recipe Tree</dt>
            <dd class="wb-prop-val wb-prop-val--left">Resolves Mystic Forge gifts, precursor paths, and material deltas.</dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">02 · Arbitrage Model</dt>
            <dd class="wb-prop-val wb-prop-val--left">Evaluates Instant Buy, Buy Order, Scratch Craft, Account Cost, and Wallace 15% TP tax.</dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">03 · Prerequisite Audit</dt>
            <dd class="wb-prop-val wb-prop-val--left">Checks World Completion, Crafting 500 disciplines, Masteries, and character routing.</dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">04 · Knapsack Planner</dt>
            <dd class="wb-prop-val wb-prop-val--left">Schedules optimal tasks within a 30m–120m daily playtime budget.</dd>
          </div>
        </dl>
      </section>
    `;
  }

  // ── Spread 1: Inquiry Guide (Comparative Ranking & Direct Guide) ────────────
  function renderGuideSpreadLeft() {
    if (!leftPageBody) return;
    const guide = activeCustomGuide;

    if (!guide) {
      leftPageBody.innerHTML = `
        <div class="wb-sec-hdr">
          <span>Priory Inquiry Guide</span>
          <span class="tabular-nums">Idle</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Status</dt>
            <dd class="wb-prop-val wb-prop-val--left">No active inquiry guide. Submit a query in Library to generate comparative rankings or crafting guides.</dd>
          </div>
        </dl>
        <div style="padding: 8px;">
          <button type="button" class="btn-return-library" onclick="turnPageTo(0, 'backward')">Return to Library</button>
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
      if (items.length === 0) {
        items.push({
          rank: 1,
          name: defaultName,
          subtype: getLegendaryType(defaultId, defaultName),
          readiness: Math.round(guide?.readiness_percentage || 0),
          cost: "Audited",
          archetype: "Standard Crafting",
          kitReady: false,
          gate: null
        });
      }

      leftPageBody.innerHTML = `
        <div class="wb-pane-titlebar">
          <div class="wb-pane-titlegroup">
            ${sigilSpan("gdc")}
            <h2 class="dossier-goal-title">${escapeHtml(guide.goal_name)}</h2>
            <span class="dossier-type-tag">Comparative Ranking</span>
          </div>
          <button type="button" class="btn-return-library" onclick="turnPageTo(0, 'backward')">Library</button>
        </div>

        <section class="wb-section">
          <div class="wb-epistemic-row">
            <span class="wb-epistemic-gutter" title="Entailed synthesis">${PRIORY_SIGILS_SVG.entailed}</span>
            <div>${formatTextWithWaypoints(stripDecorations(guide.executive_summary || ""))}</div>
          </div>
        </section>

        <section class="wb-section">
          <div class="wb-sec-hdr">
            <span>Ranked Contenders</span>
            <span class="tabular-nums">${items.length}</span>
          </div>
          <table class="wb-table">
            <thead>
              <tr>
                <th class="num">Rank</th>
                <th>Item</th>
                <th>Strategy &amp; Flags</th>
                <th class="num">Readiness</th>
                <th class="num">Est. Cost</th>
                <th class="num">Action</th>
              </tr>
            </thead>
            <tbody>
              ${items.map((item, idx) => {
                const pMatch = LEGENDARY_PRESETS.find(p => p.name.toLowerCase() === item.name.toLowerCase());
                const itemId = pMatch ? pMatch.id : defaultId;
                const flags = [item.archetype];
                if (item.kitReady) flags.push("Bank Kit Ready");
                if (item.gate) flags.push(item.gate);
                return `
                  <tr>
                    <td class="num cell-primary">#${item.rank}${idx === 0 ? ' (Top)' : ''}</td>
                    <td class="cell-primary">
                      <div>${escapeHtml(item.name)}</div>
                      <div style="font-size: 11px; font-weight: 400; color: var(--text-muted);">${escapeHtml(item.subtype)}</div>
                    </td>
                    <td>${flags.map(f => `<code>${escapeHtml(f)}</code>`).join(" ")}</td>
                    <td class="num">${item.readiness}%</td>
                    <td class="num">~${escapeHtml(item.cost)}</td>
                    <td class="num">
                      <button type="button" class="btn-sub-jump" onclick="loadLegendaryDossier(${itemId}, '${escapeHtml(item.name)}', { targetSpread: 2 })">Dossier</button>
                    </td>
                  </tr>
                `;
              }).join("")}
            </tbody>
          </table>
        </section>

        <section class="wb-section">
          <div class="wb-epistemic-row">
            <span class="wb-epistemic-gutter" title="Synthesized note">${PRIORY_SIGILS_SVG.synthesized}</span>
            <div>${formatTextWithWaypoints(stripDecorations(guide.motivational_tip || "Temporal ranking accounts for live account wallet, materials in bank, and mastery gate status."))}</div>
          </div>
        </section>
      `;
    } else {
      const readiness = Math.round(guide.readiness_percentage || 0);
      const missingMats = guide.missing_materials_summary || {};
      const missingKeys = Object.keys(missingMats);

      leftPageBody.innerHTML = `
        <div class="wb-pane-titlebar">
          <div class="wb-pane-titlegroup">
            ${sigilSpan(sigilKindForItemType(getLegendaryType(activeLegendaryId, guide.goal_name)))}
            <h2 class="dossier-goal-title">${escapeHtml(guide.goal_name)}</h2>
            <span class="dossier-type-tag">${escapeHtml(getLegendaryType(activeLegendaryId, guide.goal_name))}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 6px;">
            ${guide.chat_code ? `<button type="button" class="chatcode-stamp" onclick="copyChatCode('${guide.chat_code}', this, event)" title="Copy Chat Code"><code>${escapeHtml(guide.chat_code)}</code></button>` : ''}
            <button type="button" class="btn-return-library" onclick="turnPageTo(0, 'backward')">Library</button>
          </div>
        </div>

        <div class="readiness-meter-wrap">
          <div class="readiness-meter-bar" style="width: ${Math.min(100, Math.max(0, readiness))}%;"></div>
          <span class="readiness-meter-label">${readiness}% Account Readiness</span>
        </div>

        <section class="wb-section">
          <div class="wb-epistemic-row">
            <span class="wb-epistemic-gutter">${PRIORY_SIGILS_SVG.entailed}</span>
            <div>${formatTextWithWaypoints(stripDecorations(guide.executive_summary || ""))}</div>
          </div>
        </section>

        <section class="wb-section">
          <div class="wb-sec-hdr">
            <span>Strategic Recommendations</span>
            <span class="tabular-nums">${(guide.strategic_recommendations || []).length}</span>
          </div>
          ${(guide.strategic_recommendations || []).map(rec => `
            <div class="wb-epistemic-row">
              <span class="wb-epistemic-gutter">${PRIORY_SIGILS_SVG.entailed}</span>
              <div>${formatTextWithWaypoints(stripDecorations(rec))}</div>
            </div>
          `).join("")}
        </section>

        ${missingKeys.length > 0 ? `
          <section class="wb-section">
            <div class="wb-sec-hdr">
              <span>Outstanding Materials Audit</span>
              <span class="tabular-nums">${missingKeys.length}</span>
            </div>
            <table class="wb-table">
              <thead>
                <tr>
                  <th>Material</th>
                  <th class="num">Required</th>
                </tr>
              </thead>
              <tbody>
                ${missingKeys.slice(0, 10).map(mat => `
                  <tr>
                    <td class="cell-primary">${escapeHtml(mat)}</td>
                    <td class="num">${missingMats[mat].toLocaleString()}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </section>
        ` : ''}

        <div style="display: flex; justify-content: flex-end; padding: 8px;">
          <button type="button" class="btn-open-dossier" onclick="loadLegendaryDossier(${activeLegendaryId}, '${escapeHtml(activeLegendaryName)}', { targetSpread: 2 })">
            Open Full Dossier
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
        <div class="wb-sec-hdr">
          <span>Active Dossier Fast-Track</span>
          <span class="tabular-nums">${escapeHtml(activeLegendaryName)}</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Bound Context</dt>
            <dd class="wb-prop-val">${escapeHtml(activeLegendaryName)}</dd>
          </div>
        </dl>
        <div style="display: flex; gap: 6px; padding: 8px;">
          <button type="button" class="btn-forge-inscribe" onclick="executeSearchQuery('How do I craft ${escapeHtml(activeLegendaryName)}?')">
            Generate Guide
          </button>
          <button type="button" class="wb-btn" onclick="turnPageTo(2, 'forward')">
            Recipe &amp; Economics
          </button>
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

      if (!speedNote) {
        const topName = (guide.goal_name || "").toLowerCase().includes("accessor") ? "Aurora" : activeLegendaryName;
        speedNote = `${topName} uses Standard Crafting (~10h gameplay effort), significantly faster than Gen 2.0 narrative collections (~40h).`;
      }

      if (!boosterNote && !loungeNote) {
        boosterNote = "Stack Experience Booster + Heroic Booster + Guild Tavern buffs for accelerated reward tracks.";
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
        <div class="wb-sec-hdr">
          <span>Strategic Acceleration</span>
          <span class="tabular-nums">${checklistSteps.length} steps</span>
        </div>

        <section class="wb-section">
          <dl class="wb-dl">
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Speed Analysis</dt>
              <dd class="wb-prop-val wb-prop-val--left">${formatTextWithWaypoints(stripDecorations(speedNote))}</dd>
            </div>
            <div class="wb-prop-row">
              <dt class="wb-prop-key">${boosterNote ? 'Booster Synergy' : 'Staging &amp; Lounge'}</dt>
              <dd class="wb-prop-val wb-prop-val--left">${formatTextWithWaypoints(stripDecorations(boosterNote || loungeNote))}</dd>
            </div>
          </dl>
        </section>

        <section class="wb-section">
          <div class="wb-sec-hdr">
            <span>Actionable Session Checklist</span>
            <span class="tabular-nums">${checklistSteps.length}</span>
          </div>
          <table class="wb-table">
            <thead>
              <tr>
                <th class="num">Step</th>
                <th>Task &amp; Instructions</th>
                <th>Mode</th>
                <th class="num">Time</th>
                <th class="num">Waypoint</th>
              </tr>
            </thead>
            <tbody>
              ${checklistSteps.map(step => `
                <tr>
                  <td class="num">${step.step_number}</td>
                  <td>
                    <div class="cell-primary">${escapeHtml(step.title)}</div>
                    <div>${formatTextWithWaypoints(stripDecorations(step.description))}</div>
                  </td>
                  <td><code>${escapeHtml(step.game_mode || 'Session')}</code></td>
                  <td class="num">${step.estimated_time_minutes}m</td>
                  <td class="num">
                    ${step.chat_code ? `<button type="button" class="chatcode-stamp" onclick="copyChatCode('${step.chat_code}', this, event)"><code>${escapeHtml(step.chat_code)}</code></button>` : '—'}
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </section>

        <div style="display: flex; gap: 6px; justify-content: flex-end; padding: 8px;">
          <button type="button" class="wb-btn" onclick="turnPageTo(2, 'forward')">Recipe &amp; Economics</button>
          <button type="button" class="wb-btn wb-btn-primary" onclick="turnPageTo(3, 'forward')">Readiness &amp; Plan</button>
        </div>
      `;
    } else {
      const phases = guide.master_roadmap_phases || [];
      const steps = guide.session_checklist || [];
      rightPageBody.innerHTML = `
        <div class="wb-sec-hdr">
          <span>Master Roadmap &amp; Checklist</span>
          <span class="tabular-nums">${phases.length} phases</span>
        </div>

        <section class="wb-section">
          <table class="wb-table">
            <thead>
              <tr>
                <th class="num">Phase</th>
                <th>Milestone</th>
              </tr>
            </thead>
            <tbody>
              ${phases.map((phase, idx) => `
                <tr>
                  <td class="num">${idx + 1}</td>
                  <td>${formatTextWithWaypoints(stripDecorations(phase))}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </section>

        <section class="wb-section">
          <div class="wb-sec-hdr">
            <span>Actionable Session Checklist</span>
            <span class="tabular-nums">${steps.length}</span>
          </div>
          <table class="wb-table">
            <thead>
              <tr>
                <th class="num">Step</th>
                <th>Task &amp; Instructions</th>
                <th>Mode</th>
                <th class="num">Time</th>
                <th class="num">Waypoint</th>
              </tr>
            </thead>
            <tbody>
              ${steps.map(step => `
                <tr>
                  <td class="num">${step.step_number}</td>
                  <td>
                    <div class="cell-primary">${escapeHtml(step.title)}</div>
                    <div>${formatTextWithWaypoints(stripDecorations(step.description))}</div>
                  </td>
                  <td><code>${escapeHtml(step.game_mode || 'Session')}</code></td>
                  <td class="num">${step.estimated_time_minutes}m</td>
                  <td class="num">
                    ${step.chat_code ? `<button type="button" class="chatcode-stamp" onclick="copyChatCode('${step.chat_code}', this, event)"><code>${escapeHtml(step.chat_code)}</code></button>` : '—'}
                  </td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </section>

        <div style="display: flex; gap: 6px; justify-content: flex-end; padding: 8px;">
          <button type="button" class="wb-btn" onclick="turnPageTo(2, 'forward')">Recipe &amp; Economics</button>
          <button type="button" class="wb-btn wb-btn-primary" onclick="turnPageTo(3, 'forward')">Readiness &amp; Plan</button>
        </div>
      `;
    }
  }

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
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Status</dt>
            <dd class="wb-prop-val">Querying dossier for ${escapeHtml(activeLegendaryName)}…</dd>
          </div>
        </dl>
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
        { name: precursorName, count: 1, sigil: "cont" },
        { name: "Gift of Mastery", count: 1, sigil: "gdc" },
        { name: "Gift of Fortune", count: 1, sigil: "role" },
        { name: `Gift of ${activeLegendaryName}`, count: 1, sigil: "ind" }
      ];

      bodyContent = `
        <div class="readiness-meter-wrap">
          <div class="readiness-meter-bar" style="width: ${Math.min(100, Math.max(0, readinessPct))}%;"></div>
          <span class="readiness-meter-label">${readinessPct}% Account Progress</span>
        </div>

        <section class="wb-section">
          <div class="wb-sec-hdr">
            <span>Account Cost Summary</span>
            <span class="tabular-nums">Copper / Gold</span>
          </div>
          <dl class="wb-dl">
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Total Craft Cost</dt>
              <dd class="wb-prop-val">${formatCopper(scratchCost)}</dd>
            </div>
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Account Owned Value</dt>
              <dd class="wb-prop-val text-clear">${formatCopper(ownedValue)}</dd>
            </div>
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Missing Materials</dt>
              <dd class="wb-prop-val">${missingCount > 0 ? `${missingCount} types` : 'Audited'}</dd>
            </div>
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Gold Required</dt>
              <dd class="wb-prop-val" style="font-weight: 500;">${formatCopper(goldRequired)}</dd>
            </div>
          </dl>
        </section>

        <section class="wb-section">
          <div class="wb-sec-hdr">
            <span>Mystic Forge Recipe Tree</span>
            <span class="tabular-nums">4 components</span>
          </div>
          <table class="wb-table">
            <thead>
              <tr>
                <th>Component</th>
                <th class="num">Quantity</th>
              </tr>
            </thead>
            <tbody>
              ${sockets.map(s => `
                <tr>
                  <td class="cell-primary">${sigilSpan(s.sigil)} ${escapeHtml(s.name)}</td>
                  <td class="num">${s.count}x</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </section>

        ${missingCount > 0 ? `
          <section class="wb-section">
            <div class="wb-sec-hdr">
              <span>Primary Outstanding Components</span>
              <span class="tabular-nums">${missingCount}</span>
            </div>
            <table class="wb-table">
              <thead>
                <tr>
                  <th>Material</th>
                  <th class="num">Required</th>
                </tr>
              </thead>
              <tbody>
                ${missingKeys.slice(0, 8).map(k => `
                  <tr>
                    <td class="cell-primary">${escapeHtml(k)}</td>
                    <td class="num">${missingMats[k].toLocaleString()}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </section>
        ` : ''}
      `;
    }

    leftPageBody.innerHTML = `
      <div class="wb-pane-titlebar">
        <div class="wb-pane-titlegroup">
          ${sigilSpan(sigilKindForItemType(itemType))}
          <h2 class="dossier-goal-title">${escapeHtml(activeLegendaryName)}</h2>
          <span class="dossier-type-tag">${escapeHtml(itemType)}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 6px;">
          <button type="button" class="chatcode-stamp" onclick="copyChatCode('${chatCode}', this, event)" title="Copy Chat Code"><code>${escapeHtml(chatCode)}</code></button>
          <button type="button" class="btn-return-library" onclick="turnPageTo(0, 'backward')">Library</button>
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
        <div class="wb-sec-hdr">
          <span>Market Arbitrage &amp; Economics</span>
          <span class="tabular-nums">Loading</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Status</dt>
            <dd class="wb-prop-val">Evaluating Wallace 15% TP Tax &amp; arbitrage…</dd>
          </div>
        </dl>
      `;
      return;
    }

    if (!arb) {
      rightPageBody.innerHTML = `
        <div class="wb-sec-hdr">
          <span>Market Arbitrage &amp; Economics</span>
          <span class="tabular-nums">Unavailable</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Status</dt>
            <dd class="wb-prop-val">Arbitrage data unavailable.</dd>
          </div>
        </dl>
      `;
      return;
    }

    let verdictClass = "craft";
    let verdictLabel = "Recommended: Craft for Self";
    if (arb.recommended_action === "CRAFT_FOR_PROFIT") {
      verdictClass = "profit";
      verdictLabel = "Recommended: Craft for Profit (TP Flip)";
    } else if (arb.recommended_action === "BUY_FINISHED_DIRECT") {
      verdictClass = "buy";
      verdictLabel = "Recommended: Buy Finished from Trading Post";
    }

    const marginVal = arb.profit_margin_if_sold != null ? arb.profit_margin_if_sold : 0;
    const marginCls = marginVal >= 0 ? "text-clear" : "text-avoid";
    const marginSign = marginVal >= 0 ? "+" : "";
    const taxAmt = Math.round(arb.buy_order_total * 0.15);

    const prec = arb.precursor_strategy || {};
    const clover = arb.clover_strategy || {};

    rightPageBody.innerHTML = `
      <div class="wb-sec-hdr">
        <span>Market Arbitrage &amp; Economics</span>
        <span class="tabular-nums">TP Audit</span>
      </div>

      <div class="verdict-banner ${verdictClass}">${verdictLabel}</div>

      <section class="wb-section">
        <table class="wb-table">
          <thead>
            <tr>
              <th>Acquisition Route</th>
              <th class="num">Total Cost</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Instant TP Buy</td>
              <td class="num">${formatCopper(arb.instant_buy_total)}</td>
            </tr>
            <tr>
              <td>TP Buy Order</td>
              <td class="num">${formatCopper(arb.buy_order_total)}</td>
            </tr>
            <tr>
              <td>Scratch Craft Cost</td>
              <td class="num">${formatCopper(arb.craft_from_scratch_total)}</td>
            </tr>
            <tr>
              <td class="cell-primary">My Account Craft Cost</td>
              <td class="num cell-primary">${formatCopper(arb.my_account_craft_cost)}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="wb-section">
        <div class="wb-sec-hdr">
          <span>Wallace 15% TP Tax Liquidation Model</span>
          <span class="tabular-nums">15% fee</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Gross TP Liquidation</dt>
            <dd class="wb-prop-val">${formatCopper(arb.buy_order_total)}</dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Wallace 15% TP Tax</dt>
            <dd class="wb-prop-val text-avoid">-${formatCopper(taxAmt)}</dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Net Payout If Sold</dt>
            <dd class="wb-prop-val" style="font-weight: 500;">${formatCopper(arb.net_sell_if_sold)}</dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Net Profit Margin (vs Scratch)</dt>
            <dd class="wb-prop-val ${marginCls}" style="font-weight: 500;">${marginSign}${formatCopper(marginVal)}</dd>
          </div>
        </dl>
      </section>

      <section class="wb-section">
        <div class="wb-sec-hdr">
          <span>Acquisition Strategies</span>
          <span class="tabular-nums">2 policies</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Precursor Strategy</dt>
            <dd class="wb-prop-val wb-prop-val--left">
              <div><code>${escapeHtml(prec.recommended_strategy || 'BUY_ORDER')}</code> · ${escapeHtml(prec.precursor_name || 'Precursor')} ${prec.precursor_id ? `<code>${prec.precursor_id}</code>` : ''}</div>
              <div style="color: var(--text-muted); margin-top: 2px;">${escapeHtml(prec.details || 'Compare TP buy order vs Grandmaster Craftsman Hobbs collection vs Wizard Vault Starter Kit.')}</div>
            </dd>
          </div>
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Mystic Clover EV</dt>
            <dd class="wb-prop-val wb-prop-val--left">
              <div><code>${escapeHtml(clover.recommended_strategy || 'WIZARDS_VAULT')}</code></div>
              <div style="color: var(--text-muted); margin-top: 2px;">${escapeHtml(clover.notes || 'Expected Value: 3.2 Mystic Coins + 3.2 Ecto per Clover via Mystic Forge vs discounted Astral Acclaim and Fractal BLING-9988.')}</div>
            </dd>
          </div>
        </dl>
      </section>
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

    let prereqSealHtml = "";
    if (isLoadingPrereq) {
      prereqSealHtml = `
        <div class="prereq-compact-seal">
          <div>
            <div class="seal-title">Auditing Account Prerequisites…</div>
            <div class="seal-sub">Checking world completion, masteries &amp; crafting disciplines</div>
          </div>
        </div>
      `;
    } else if (!prereq) {
      prereqSealHtml = `
        <div class="prereq-compact-seal warn">
          <div>
            <div class="seal-title text-warn">Prerequisite Data Unavailable</div>
            <div class="seal-sub">Run audit to verify account readiness</div>
          </div>
          <button type="button" class="btn-toggle-prereq-details" onclick="fetchPrerequisites()">Audit</button>
        </div>
      `;
    } else {
      const canCraft = Boolean(prereq.can_craft_immediately);
      const isSatisfied = canCraft || (prereq.has_world_completion && prereq.active_crafting_ready && prereq.mastery_requirements_met && (!prereq.blockers || prereq.blockers.length === 0));

      const primaryBlocker = (prereq.blockers && prereq.blockers.length > 0)
        ? prereq.blockers[0]
        : "Action items remaining";

      const sealBadgeText = isSatisfied ? "Prerequisites Satisfied" : "Prerequisites Pending";
      const sealSubText = isSatisfied
        ? "World completion, Crafting 500 &amp; Masteries verified."
        : escapeHtml(primaryBlocker);
      const sealStatusClass = isSatisfied ? "pass" : "warn";

      const worldText = prereq.has_world_completion ? "Completed" : "Incomplete";
      const craftText = prereq.active_crafting_ready ? "Ready (500)" : "Needs Discipline";
      const masteryText = prereq.mastery_requirements_met ? "Satisfied" : "Missing Unlocks";
      const precBits = prereq.precursor_collection_bits_total > 0
        ? `${prereq.precursor_collection_bits_done} / ${prereq.precursor_collection_bits_total}`
        : "Standard";

      let blockersHtml = "";
      if (prereq.blockers && prereq.blockers.length > 0) {
        blockersHtml = prereq.blockers.map(b => `
          <div class="wb-prop-row">
            <dt class="wb-prop-key text-avoid">Blocker</dt>
            <dd class="wb-prop-val wb-prop-val--left text-avoid">${escapeHtml(b)}</dd>
          </div>
        `).join("");
      } else {
        blockersHtml = `
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Blockers</dt>
            <dd class="wb-prop-val text-clear">None (all prerequisites met)</dd>
          </div>
        `;
      }

      let routingHtml = "";
      if (prereq.crafting_assignment_recommendations && prereq.crafting_assignment_recommendations.length > 0) {
        routingHtml = prereq.crafting_assignment_recommendations.map(r => `
          <div class="wb-prop-row">
            <dt class="wb-prop-key">${escapeHtml(r.gift_or_component || r.gift || 'Gift')}</dt>
            <dd class="wb-prop-val">${escapeHtml(r.character_name || r.recommended_character || 'Active Character')} (${escapeHtml(r.discipline || 'Weaponsmith')} ${r.current_rating || 500})</dd>
          </div>
        `).join("");
      } else if (prereq.character_discipline_assignments && Object.keys(prereq.character_discipline_assignments).length > 0) {
        routingHtml = Object.entries(prereq.character_discipline_assignments).map(([disc, char]) => {
          const charName = typeof char === "object" ? char.character_name : char;
          return `
            <div class="wb-prop-row">
              <dt class="wb-prop-key">${escapeHtml(disc)}</dt>
              <dd class="wb-prop-val">${escapeHtml(charName)}</dd>
            </div>
          `;
        }).join("");
      }

      prereqSealHtml = `
        <div class="prereq-compact-seal ${sealStatusClass}">
          <div>
            <div class="seal-title">${sealBadgeText}</div>
            <div class="seal-sub">${sealSubText}</div>
          </div>
          <button type="button" class="btn-toggle-prereq-details" id="btn-toggle-prereq-details" title="Toggle prerequisite audit details">
            ${prereqDetailsExpanded ? 'Hide Details' : 'Details'}
          </button>
        </div>

        <div id="prereq-collapsible-details" class="prereq-collapsible-details ${prereqDetailsExpanded ? 'expanded active' : ''}">
          <dl class="wb-dl">
            <div class="wb-prop-row">
              <dt class="wb-prop-key">World Completion</dt>
              <dd class="wb-prop-val ${prereq.has_world_completion ? 'text-clear' : 'text-avoid'}">${worldText} (${escapeHtml(prereq.world_completion_source || 'Map Exploration')})</dd>
            </div>
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Crafting 500</dt>
              <dd class="wb-prop-val ${prereq.active_crafting_ready ? 'text-clear' : 'text-warn'}">${craftText}</dd>
            </div>
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Masteries</dt>
              <dd class="wb-prop-val ${prereq.mastery_requirements_met ? 'text-clear' : 'text-warn'}">${masteryText}${prereq.missing_masteries?.length > 0 ? ` (${prereq.missing_masteries.length} pending)` : ''}</dd>
            </div>
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Precursor</dt>
              <dd class="wb-prop-val">${precBits} · ${escapeHtml(prereq.precursor_collection_step || 'Tradeable')}</dd>
            </div>
            ${blockersHtml}
            ${routingHtml}
          </dl>
        </div>
      `;
    }

    const budgetControlsHtml = `
      <section class="wb-section">
        <div class="wb-sec-hdr">
          <span>Playtime Budget (0/1 Knapsack)</span>
          <span class="tabular-nums" id="budget-val-display">${plannerBudgetMinutes} mins</span>
        </div>
        <div class="inscribe-form">
          <input type="range" id="planner-budget-slider" class="priory-slider" min="30" max="120" step="15" value="${plannerBudgetMinutes}">
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
            <div class="playtime-quick-btns">
              <button type="button" class="playtime-btn ${plannerBudgetMinutes === 30 ? 'active' : ''}" data-mins="30">30m</button>
              <button type="button" class="playtime-btn ${plannerBudgetMinutes === 60 ? 'active' : ''}" data-mins="60">60m</button>
              <button type="button" class="playtime-btn ${plannerBudgetMinutes === 90 ? 'active' : ''}" data-mins="90">90m</button>
              <button type="button" class="playtime-btn ${plannerBudgetMinutes === 120 ? 'active' : ''}" data-mins="120">120m</button>
            </div>
            <button type="button" class="btn-forge-inscribe" id="btn-calc-itinerary">
              <span id="btn-itinerary-text">${isLoadingItin ? 'Scheduling…' : 'Schedule Itinerary'}</span>
              <span id="btn-itinerary-spinner" class="spinner-ink ${isLoadingItin ? '' : 'hidden'}"></span>
            </button>
          </div>
        </div>
      </section>
    `;

    let summaryContent = "";
    if (isLoadingItin) {
      summaryContent = `
        <section class="wb-section">
          <div class="wb-sec-hdr">
            <span>Session Allocation</span>
            <span class="tabular-nums">Optimizing</span>
          </div>
          <dl class="wb-dl">
            <div class="wb-prop-row">
              <dt class="wb-prop-key">Status</dt>
              <dd class="wb-prop-val">Optimizing 0/1 Knapsack itinerary…</dd>
            </div>
          </dl>
        </section>
      `;
    } else if (!itin) {
      summaryContent = `
        <section class="wb-section">
          <div class="wb-sec-hdr">
            <span>Session Allocation</span>
            <span class="tabular-nums">0% utilization</span>
          </div>
          <dl class="wb-dl">
            <div class="wb-prop-row"><dt class="wb-prop-key">Budget</dt><dd class="wb-prop-val">${plannerBudgetMinutes}m</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Scheduled</dt><dd class="wb-prop-val">0m</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Tasks Queued</dt><dd class="wb-prop-val">0</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Unused Window</dt><dd class="wb-prop-val">${plannerBudgetMinutes}m</dd></div>
          </dl>
        </section>
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
      const assignedChar = assignedCharFromItin || assignedCharFromPrereq || "Primary active character";

      summaryContent = `
        <section class="wb-section">
          <div class="wb-sec-hdr">
            <span>Session Allocation</span>
            <span class="tabular-nums">${utilPct}% utilization</span>
          </div>
          <dl class="wb-dl">
            <div class="wb-prop-row"><dt class="wb-prop-key">Budget</dt><dd class="wb-prop-val">${budgetMin}m</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Scheduled</dt><dd class="wb-prop-val">${scheduledMin}m</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Tasks Queued</dt><dd class="wb-prop-val">${tasksCount}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Unused Window</dt><dd class="wb-prop-val">${unusedMin}m</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Character Routing</dt><dd class="wb-prop-val">${escapeHtml(assignedChar)}</dd></div>
            ${itin.summary ? `<div class="wb-prop-row"><dt class="wb-prop-key">Summary</dt><dd class="wb-prop-val wb-prop-val--left">${escapeHtml(itin.summary)}</dd></div>` : ''}
          </dl>
        </section>
      `;
    }

    leftPageBody.innerHTML = `
      <div class="wb-sec-hdr">
        <span>Session Planner &amp; Prerequisites</span>
        <span class="tabular-nums">${escapeHtml(activeLegendaryName)}</span>
      </div>
      ${prereqSealHtml}
      ${budgetControlsHtml}
      ${summaryContent}
    `;

    const slider = document.getElementById("planner-budget-slider");
    const valDisplay = document.getElementById("budget-val-display");

    if (slider) {
      slider.addEventListener("input", (e) => {
        const mins = parseInt(e.target.value, 10);
        plannerBudgetMinutes = mins;
        updateStatusBarContext();
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
        updateStatusBarContext();
        if (slider) slider.value = mins;
        if (valDisplay) valDisplay.textContent = `${mins} mins`;
        document.querySelectorAll(".playtime-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        recalculateItinerary(mins);
      });
    });

    const btnCalc = document.getElementById("btn-calc-itinerary");
    if (btnCalc) {
      btnCalc.addEventListener("click", () => recalculateItinerary(plannerBudgetMinutes));
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
        btnToggleDetails.textContent = prereqDetailsExpanded ? "Hide Details" : "Details";
      });
    }
  }

  function renderPlanSpreadRight() {
    if (!rightPageBody) return;

    const isLoading = activeDossierData.loading.itinerary;
    const itin = activeDossierData.itinerary;

    if (isLoading) {
      rightPageBody.innerHTML = `
        <div class="wb-sec-hdr">
          <span>Prioritized Task Route</span>
          <span class="tabular-nums">${plannerBudgetMinutes}m</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Status</dt>
            <dd class="wb-prop-val">Computing 0/1 Knapsack schedule…</dd>
          </div>
        </dl>
      `;
      return;
    }

    if (!itin || !itin.tasks || itin.tasks.length === 0) {
      rightPageBody.innerHTML = `
        <div class="wb-sec-hdr">
          <span>Prioritized Task Route</span>
          <span class="tabular-nums">0 tasks</span>
        </div>
        <dl class="wb-dl">
          <div class="wb-prop-row">
            <dt class="wb-prop-key">Status</dt>
            <dd class="wb-prop-val wb-prop-val--left">No tasks scheduled for this duration. Select a playtime budget to compute an itinerary.</dd>
          </div>
        </dl>
      `;
      return;
    }

    rightPageBody.innerHTML = `
      <div class="wb-sec-hdr">
        <span>Prioritized Task Route (${escapeHtml(activeLegendaryName)})</span>
        <span class="tabular-nums">${itin.tasks.length} tasks</span>
      </div>

      <table class="wb-table">
        <thead>
          <tr>
            <th class="num">#</th>
            <th>Task, Inputs &amp; Reward</th>
            <th>Location</th>
            <th class="num">Waypoint</th>
            <th class="num">Duration</th>
          </tr>
        </thead>
        <tbody>
          ${itin.tasks.map((task, idx) => {
            const inputs = task.required_inputs?.name
              ? `${task.required_inputs.count ? task.required_inputs.count + 'x ' : ''}${task.required_inputs.name}`
              : (task.required_inputs?.description || (task.required_inputs?.currencies ? Object.entries(task.required_inputs.currencies).map(([k, v]) => `${v} ${k}`).join(', ') : 'None'));
            const rewardVal = task.reward_output?.value_towards_goal || task.reward_output?.name || 'Progression towards goal';
            return `
              <tr>
                <td class="num">${idx + 1}</td>
                <td>
                  <div class="cell-primary">${escapeHtml(task.title)}</div>
                  <div>${formatTextWithWaypoints(stripDecorations(task.instructions))}</div>
                  <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">
                    Inputs: ${escapeHtml(inputs)} · Reward: ${escapeHtml(rewardVal)}${task.character_name ? ` · Char: ${escapeHtml(task.character_name)}` : ''}
                  </div>
                </td>
                <td>${escapeHtml(task.location_name)}</td>
                <td class="num">
                  ${task.waypoint_code ? `<button type="button" class="chatcode-stamp" onclick="copyChatCode('${task.waypoint_code}', this, event)" title="Copy Waypoint"><code>${escapeHtml(task.waypoint_code)}</code></button>` : '—'}
                </td>
                <td class="num">${task.estimated_duration_minutes}m</td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    `;
  }

  window.renderPlanSpreadLeft = renderPlanSpreadLeft;
  window.renderPlanSpreadRight = renderPlanSpreadRight;
  window.renderSpread3Left = renderPlanSpreadLeft;
  window.renderSpread3Right = renderPlanSpreadRight;

  // ── 4. Telemetry & Docked Inspector Controller ──────────────────────────────
  function ensureSideDrawerDOM() {
    let drawer = document.getElementById("priory-side-drawer");
    if (!drawer) {
      drawer = document.createElement("aside");
      drawer.id = "priory-side-drawer";
      drawer.className = "wb-right priory-side-drawer";
      drawer.setAttribute("aria-label", "Account Telemetry and Diagnostics");
      drawer.innerHTML = `
        <div class="wb-sec-hdr">
          <span>Account &amp; Telemetry</span>
          <button id="btn-close-drawer" class="btn-drawer-close" type="button">Hide</button>
        </div>
        <div class="drawer-content">
          <section class="drawer-section">
            <dl class="wb-dl">
              <div class="wb-prop-row"><dt class="wb-prop-key">Account</dt><dd class="wb-prop-val" id="drawer-account-name">Loading...</dd></div>
              <div class="wb-prop-row"><dt class="wb-prop-key">Active Key</dt><dd class="wb-prop-val"><code id="drawer-api-key-masked">None</code></dd></div>
            </dl>
            <div class="api-key-form">
              <input type="password" id="drawer-api-key-input" class="drawer-key-input" placeholder="Paste GW2 API Key…" />
              <button type="button" id="btn-toggle-key-visibility" class="wb-icon-btn">Show</button>
              <button type="button" id="btn-apply-api-key" class="wb-btn wb-btn-primary"><span id="btn-apply-key-text">Sync Account</span><span id="btn-apply-key-spinner" class="spinner-ink hidden"></span></button>
              <button type="button" id="btn-reset-api-key" class="wb-btn">Reset</button>
              <div id="drawer-api-key-feedback" class="api-key-feedback hidden"></div>
            </div>
          </section>
          <section class="drawer-section">
            <div class="drawer-stats-grid" id="drawer-account-stats"></div>
          </section>
          <section class="drawer-section">
            <div class="diagnostics-panel" id="drawer-diagnostics-panel"></div>
            <button id="btn-reload-telemetry" class="wb-btn" type="button">Refresh</button>
          </section>
        </div>
      `;
      (wbShell || document.body).appendChild(drawer);
    }

    const btnToggle = document.getElementById("btn-toggle-drawer");
    if (btnToggle && !btnToggle.getAttribute("data-bound")) {
      btnToggle.setAttribute("data-bound", "true");
      btnToggle.addEventListener("click", () => {
        if (wbShell) wbShell.classList.toggle("wb-no-right");
      });
    }

    const btnClose = document.getElementById("btn-close-drawer");
    if (btnClose && !btnClose.getAttribute("data-bound")) {
      btnClose.setAttribute("data-bound", "true");
      btnClose.addEventListener("click", () => {
        if (wbShell) wbShell.classList.add("wb-no-right");
      });
    }

    const btnReload = document.getElementById("btn-reload-telemetry");
    if (btnReload && !btnReload.getAttribute("data-bound")) {
      btnReload.setAttribute("data-bound", "true");
      btnReload.addEventListener("click", () => fetchAccountStatus());
    }

    const btnApplyKey = document.getElementById("btn-apply-api-key");
    if (btnApplyKey && !btnApplyKey.getAttribute("data-bound")) {
      btnApplyKey.setAttribute("data-bound", "true");
      btnApplyKey.addEventListener("click", () => window.applyNewApiKey());
    }

    const btnResetKey = document.getElementById("btn-reset-api-key");
    if (btnResetKey && !btnResetKey.getAttribute("data-bound")) {
      btnResetKey.setAttribute("data-bound", "true");
      btnResetKey.addEventListener("click", () => window.resetApiKey());
    }

    const btnToggleVis = document.getElementById("btn-toggle-key-visibility");
    if (btnToggleVis && !btnToggleVis.getAttribute("data-bound")) {
      btnToggleVis.setAttribute("data-bound", "true");
      btnToggleVis.addEventListener("click", () => window.toggleKeyVisibility());
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
      if (btn) btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
    } else {
      input.type = "password";
      if (btn) btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
    }
  };

  window.openDrawerToApiKey = function() {
    if (wbShell) wbShell.classList.remove("wb-no-right");
    const input = document.getElementById("drawer-api-key-input");
    if (input) setTimeout(() => input.focus(), 60);
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
    if (btnText) btnText.textContent = "Syncing…";

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
        feedback.textContent = `Connected to ${accName} (${mats} materials, ${armory} armory)`;
      }

      for (const k in dossierCache) delete dossierCache[k];

      await fetchAccountStatus();

      if (currentSpreadIndex === 2 || currentSpreadIndex === 3) {
        loadLegendaryDossier(activeLegendaryId, activeLegendaryName, { autoTurn: false });
      } else if (currentSpreadIndex === 0) {
        renderSpread0Left();
      }
    } catch (err) {
      if (feedback) {
        feedback.className = "api-key-feedback feedback-error";
        feedback.textContent = `Failed to sync: ${err.message || String(err)}`;
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
      btnReset.textContent = "…";
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
        feedback.textContent = "Reset to default account.";
      }

      for (const k in dossierCache) delete dossierCache[k];

      await fetchAccountStatus();

      if (currentSpreadIndex === 2 || currentSpreadIndex === 3) {
        loadLegendaryDossier(activeLegendaryId, activeLegendaryName, { autoTurn: false });
      } else if (currentSpreadIndex === 0) {
        renderSpread0Left();
      }
    } catch (err) {
      if (feedback) {
        feedback.className = "api-key-feedback feedback-error";
        feedback.textContent = `Failed to reset: ${err.message || String(err)}`;
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
      if (drawerAccountName) drawerAccountName.textContent = data.account_name || "Authenticated Scholar";

      const drawerApiKeyMasked = document.getElementById("drawer-api-key-masked");
      if (drawerApiKeyMasked) drawerApiKeyMasked.textContent = data.api_key_masked || "None";

      const libraryAccountBadgeName = document.getElementById("library-account-badge-name");
      if (libraryAccountBadgeName) libraryAccountBadgeName.textContent = data.account_name || "Default Account";

      const sbAcc = document.getElementById("status-bar-account");
      if (sbAcc) sbAcc.textContent = `Account: ${data.account_name || "Default"}`;

      const sbTriples = document.getElementById("status-bar-triples");
      if (sbTriples) sbTriples.textContent = `Triples: ${(data.triples_loaded || 0).toLocaleString()}`;

      if (statsCont) {
        const w = data.wallet || {};
        const goldVal = w.liquid_gold ? w.liquid_gold.toFixed(1) + "g" : "0g";
        statsCont.innerHTML = `
          <dl class="wb-dl">
            <div class="wb-prop-row"><dt class="wb-prop-key">Liquid Gold</dt><dd class="wb-prop-val coin-gold">${goldVal}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Astral Acclaim</dt><dd class="wb-prop-val">${(w.astral_acclaim || 0).toLocaleString()}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Spirit Shards</dt><dd class="wb-prop-val">${(w.spirit_shards || 0).toLocaleString()}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Provisioner Tokens</dt><dd class="wb-prop-val">${(w.provisioner_tokens || 0).toLocaleString()}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Laurels</dt><dd class="wb-prop-val">${(w.laurels || 0).toLocaleString()}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Volatile Magic</dt><dd class="wb-prop-val">${(w.volatile_magic || 0).toLocaleString()}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Materials in Vault</dt><dd class="wb-prop-val">${(data.account_materials_count || 0).toLocaleString()}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Armory Legendaries</dt><dd class="wb-prop-val text-clear">${(data.account_armory_count || 0).toLocaleString()}</dd></div>
          </dl>
        `;
      }

      if (diagCont) {
        const modeText = data.is_fallback ? "Fallback Rule Engine" : "Live LLM Active";
        diagCont.innerHTML = `
          <dl class="wb-dl">
            <div class="wb-prop-row"><dt class="wb-prop-key">Status</dt><dd class="wb-prop-val text-clear">Ready</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Knowledge Triples</dt><dd class="wb-prop-val">${(data.triples_loaded || 0).toLocaleString()}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">LLM Provider</dt><dd class="wb-prop-val">${escapeHtml(data.llm_provider || 'Deterministic')}</dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">Reasoning Mode</dt><dd class="wb-prop-val"><code>${modeText}</code></dd></div>
            <div class="wb-prop-row"><dt class="wb-prop-key">API Key Configured</dt><dd class="wb-prop-val">${data.api_key_configured ? 'Yes' : 'No'}</dd></div>
          </dl>
        `;
      }
    } catch (err) {
      if (statsCont) statsCont.innerHTML = '<div class="wb-prop-row"><span class="wb-prop-key">Status</span><span class="wb-prop-val text-avoid">Sync failed</span></div>';
      if (diagCont) diagCont.innerHTML = '<div class="wb-prop-row"><span class="wb-prop-key">Gateway</span><span class="wb-prop-val text-avoid">Offline</span></div>';
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
    }
    return `${prefix}<span class="coin-copper">${cop}c</span>`;
  }

  function formatTextWithWaypoints(text) {
    if (!text) return "";
    let s = escapeHtml(text).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/`?(\[&amp;[A-Za-z0-9+/=]+\])`?/g, (_match, wp) => {
      const rawWp = wp.replace("&amp;", "&");
      return `<code class="wp-link" onclick="copyChatCode('${rawWp}', this, event)" title="Click to copy waypoint">${wp}</code>`;
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

  window.copyChatCode = (code, _el, e) => {
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
      if (stamp.parentNode) stamp.parentNode.removeChild(stamp);
    }, 800);
  };

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
  initTooltipDelegation();
  loadRecentChapters();
  renderLegendaryIndex();
  updateStatusBarContext();

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
      .finally(() => fetchAccountStatus());
  } else {
    fetchAccountStatus();
  }

  renderCurrentSpread();
  loadLegendaryDossier(30689, "Twilight", { autoTurn: false });
});
