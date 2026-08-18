/**
 * The Priory Grimoire — Interactive 3D Tome Controller
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const queryForm = document.getElementById("query-form");
    const queryInput = document.getElementById("query-input");
    const btnSubmit = document.getElementById("btn-submit-query");
    const btnText = document.getElementById("btn-text");
    const btnSpinner = document.getElementById("btn-spinner");

    const pageRightContainer = document.getElementById("page-right-container");
    const pageFrontIdle = document.getElementById("page-front-idle");
    const pageRevealedGuide = document.getElementById("page-revealed-guide");
    const btnTurnBack = document.getElementById("btn-turn-back");

    // Status Badges
    const valTriples = document.getElementById("val-triples");
    const valLlm = document.getElementById("val-llm");
    const valAccount = document.getElementById("val-account");

    // Account Seals
    const statArmory = document.getElementById("stat-armory");
    const statMaterials = document.getElementById("stat-materials");
    const currAa = document.getElementById("curr-aa");
    const currVm = document.getElementById("curr-vm");
    const currSs = document.getElementById("curr-ss");
    const currLaurels = document.getElementById("curr-laurels");
    const btnRefreshAccount = document.getElementById("btn-refresh-account");

    // Manifestation / Guide Elements
    const goalTitle = document.getElementById("guide-goal-title");
    const executiveSummary = document.getElementById("guide-executive-summary");
    const readinessVal = document.getElementById("guide-readiness-val");
    const chatcodeText = document.getElementById("chatcode-text");
    const btnCopyChatcode = document.getElementById("btn-copy-chatcode");
    const recList = document.getElementById("rec-list");
    const roadmapTimeline = document.getElementById("roadmap-timeline");
    const checklistGrid = document.getElementById("checklist-grid");
    const materialsTags = document.getElementById("materials-tags");
    const tipText = document.getElementById("tip-text");

    // Fetch initial telemetry and account snapshot
    fetchStatus();

    // Query Inscription Submission
    queryForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query) return;
        await executeQuery(query);
    });

    // Quick Incantations (Sample Prompts)
    document.querySelectorAll(".incantation-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
            const query = chip.getAttribute("data-query");
            queryInput.value = query;
            executeQuery(query);
        });
    });

    // Refresh Account Essence
    btnRefreshAccount.addEventListener("click", () => {
        fetchStatus(true);
    });

    // Turn Back Button (Flip back to dormant mirror)
    if (btnTurnBack) {
        btnTurnBack.addEventListener("click", () => {
            flipPageToFront();
        });
    }

    // Copy Goal Chat Code
    if (btnCopyChatcode) {
        btnCopyChatcode.addEventListener("click", () => {
            const code = chatcodeText.innerText.trim();
            if (code) {
                navigator.clipboard.writeText(code);
                const original = chatcodeText.innerText;
                chatcodeText.innerText = "Copied!";
                setTimeout(() => {
                    chatcodeText.innerText = original;
                }, 1400);
            }
        });
    }

    /**
     * Fetches telemetry and live account status.
     */
    async function fetchStatus(isRefresh = false) {
        try {
            if (isRefresh) {
                btnRefreshAccount.classList.add("spinning");
            }
            const res = await fetch("/api/status");
            const data = await res.json();

            // Status Badges
            valTriples.innerText = `${data.triples_loaded.toLocaleString()} Triples`;
            valLlm.innerText = data.llm_provider || "Standard";
            valAccount.innerText = data.api_key_configured
                ? `Live (${data.api_key_masked})`
                : "Default Test Snapshot";

            // Account Metrics
            statArmory.innerText = data.account_armory_count || 0;
            statMaterials.innerText = data.account_materials_count || 0;

            // Currency Orbs
            currAa.innerText = (data.wallet.astral_acclaim || 0).toLocaleString();
            currVm.innerText = (data.wallet.volatile_magic || 0).toLocaleString();
            currSs.innerText = (data.wallet.spirit_shards || 0).toLocaleString();
            currLaurels.innerText = (data.wallet.laurels || 0).toLocaleString();
        } catch (err) {
            console.error("Failed to fetch system status:", err);
        } finally {
            if (isRefresh) {
                btnRefreshAccount.classList.remove("spinning");
            }
        }
    }

    /**
     * Executes query with 3D magical page turn animation.
     */
    async function executeQuery(query) {
        setLoading(true);

        // Start 3D Page Turn Animation
        pageRightContainer.classList.add("page-flipping");

        try {
            const res = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query }),
            });

            const data = await res.json();

            if (data.success && data.guide) {
                setTimeout(() => {
                    renderGuide(data.guide);
                    pageFrontIdle.classList.add("hidden");
                    pageRevealedGuide.classList.remove("hidden");
                }, 400); // Reveal mid-flip for natural effect
            } else {
                alert(`Oracle error: ${data.error || "Failed to process query."}`);
            }
        } catch (err) {
            alert(`Arcane connection interrupted: ${err.message}`);
        } finally {
            setTimeout(() => {
                pageRightContainer.classList.remove("page-flipping");
                setLoading(false);
            }, 850);
        }
    }

    /**
     * Flips page back to the dormant scrying mirror.
     */
    function flipPageToFront() {
        pageRightContainer.classList.add("page-flipping");
        setTimeout(() => {
            pageRevealedGuide.classList.add("hidden");
            pageFrontIdle.classList.remove("hidden");
        }, 400);
        setTimeout(() => {
            pageRightContainer.classList.remove("page-flipping");
        }, 850);
    }

    /**
     * Renders the synthesized progression guide.
     */
    function renderGuide(guide) {
        // Header
        const targetStr = guide.target_quantity > 1 ? `${guide.target_quantity}x ` : "";
        goalTitle.innerText = `${targetStr}${guide.goal_name}`;
        executiveSummary.innerText = guide.executive_summary;
        readinessVal.innerText = `${guide.readiness_percentage}%`;

        if (guide.chat_code) {
            chatcodeText.innerText = guide.chat_code;
            btnCopyChatcode.classList.remove("hidden");
        } else {
            btnCopyChatcode.classList.add("hidden");
        }

        // Strategic Recommendations
        recList.innerHTML = "";
        if (guide.strategic_recommendations && guide.strategic_recommendations.length > 0) {
            guide.strategic_recommendations.forEach((rec) => {
                const li = document.createElement("li");
                li.innerHTML = formatTextWithWaypoints(rec);
                recList.appendChild(li);
            });
            document.getElementById("recommendations-card").classList.remove("hidden");
        } else {
            document.getElementById("recommendations-card").classList.add("hidden");
        }

        // 5-Phase Master Roadmap
        roadmapTimeline.innerHTML = "";
        if (guide.master_roadmap_phases && guide.master_roadmap_phases.length > 0) {
            guide.master_roadmap_phases.forEach((phaseLine) => {
                const item = document.createElement("div");
                item.className = "roadmap-phase-item";
                item.innerHTML = formatTextWithWaypoints(phaseLine);
                roadmapTimeline.appendChild(item);
            });
            document.getElementById("roadmap-card").classList.remove("hidden");
        } else {
            document.getElementById("roadmap-card").classList.add("hidden");
        }

        // Actionable Checklist
        checklistGrid.innerHTML = "";
        if (guide.session_checklist && guide.session_checklist.length > 0) {
            guide.session_checklist.forEach((step) => {
                const card = document.createElement("div");
                card.className = "checklist-step-card";
                card.innerHTML = `
                    <div class="step-card-header">
                        <span class="step-number-badge">Step ${step.step_number}</span>
                        <span class="step-time-badge">~${step.estimated_time_minutes}m • ${step.game_mode}</span>
                    </div>
                    <div class="step-title">${escapeHtml(step.title)}</div>
                    <div class="step-desc">${formatTextWithWaypoints(step.description)}</div>
                `;
                checklistGrid.appendChild(card);
            });
            document.getElementById("checklist-card").classList.remove("hidden");
        } else {
            document.getElementById("checklist-card").classList.add("hidden");
        }

        // Materials Delta Tags
        materialsTags.innerHTML = "";
        if (guide.missing_materials_summary && Object.keys(guide.missing_materials_summary).length > 0) {
            Object.entries(guide.missing_materials_summary).forEach(([name, count]) => {
                const tag = document.createElement("div");
                tag.className = "material-tag";
                tag.innerHTML = `<span>${escapeHtml(name)}</span> <span class="mat-qty">${count.toLocaleString()} needed</span>`;
                materialsTags.appendChild(tag);
            });
            document.getElementById("materials-card").classList.remove("hidden");
        } else {
            document.getElementById("materials-card").classList.add("hidden");
        }

        // Motivational Tip
        tipText.innerHTML = formatTextWithWaypoints(guide.motivational_tip || "");
    }

    /**
     * Formats markdown and waypoint codes [&...] into copyable badges.
     */
    function formatTextWithWaypoints(text) {
        if (!text) return "";
        let formatted = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        formatted = formatted.replace(/`?(\[&[A-Za-z0-9+/=]+\])`?/g, (match, wp) => {
            return `<span class="wp-badge" onclick="copyWaypoint('${wp}', this)" title="Click to copy waypoint code">${wp}</span>`;
        });
        return formatted;
    }

    function setLoading(isLoading) {
        if (isLoading) {
            btnSubmit.disabled = true;
            btnText.classList.add("hidden");
            btnSpinner.classList.remove("hidden");
        } else {
            btnSubmit.disabled = false;
            btnText.classList.remove("hidden");
            btnSpinner.classList.add("hidden");
        }
    }

    function escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    window.copyWaypoint = (code, element) => {
        navigator.clipboard.writeText(code);
        const originalText = element.innerText;
        element.innerText = "Copied!";
        setTimeout(() => {
            element.innerText = originalText;
        }, 1200);
    };
});
