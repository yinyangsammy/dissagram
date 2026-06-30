/* =====================================================
   DATA FROM DJANGO
===================================================== */
const ARCHETYPES = window.DISSAGRAM_FORM_DATA.archetypes;
const ROAST_STYLES = window.DISSAGRAM_FORM_DATA.roastStyles;

const INIT_ARCHETYPE_ID = window.DISSAGRAM_FORM_DATA.initArchetypeId;
const INIT_ROAST_STYLE_ID = window.DISSAGRAM_FORM_DATA.initRoastStyleId;
const INIT_LINE_IDS = window.DISSAGRAM_FORM_DATA.initLineIds;
const MAX_LINE_SELECTIONS = window.DISSAGRAM_FORM_DATA.maxLineSelections;

/* =====================================================
   STATE
===================================================== */
let selectedArchetype = null;
const CARDS_VISIBLE = 3;

/* Split archetypes by gender for the two carousel rows */
const MALE_ARCHETYPES   = ARCHETYPES.filter(a => a.gender === 'M');
const FEMALE_ARCHETYPES = ARCHETYPES.filter(a => a.gender === 'F');

/* =====================================================
   SHARED ELEMENTS
===================================================== */
/* Two separate badges — one per carousel row */
const badgeM     = document.getElementById("selected-badge-m");
const badgeNameM = document.getElementById("selected-badge-name-m");
const badgeF     = document.getElementById("selected-badge-f");
const badgeNameF = document.getElementById("selected-badge-name-f");

const styleSelect = document.getElementById("roast-style-select");
const linesList   = document.getElementById("disslines-list");

const sectionStyle  = document.getElementById("section-style");
const sectionLines  = document.getElementById("section-lines");
const sectionFinish = document.getElementById("section-finish");

const step1 = document.getElementById("step-1");
const step2 = document.getElementById("step-2");
const step3 = document.getElementById("step-3");
const step4 = document.getElementById("step-4");

const sectionPremium  = document.getElementById("section-premium");
const premiumLinesList = document.getElementById("premium-lines-list");
const step5 = document.getElementById("step-5");

const hiddenArchetype = document.getElementById("id_target_archetype");
const hiddenStyle     = document.getElementById("id_roast_style");
const hiddenStatus    = document.getElementById("id_status");
const hiddenPublic    = document.getElementById("id_is_public");

/* =====================================================
   LOCK TOAST
===================================================== */
function showLockToast() {
    const existing = document.getElementById("lock-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.id = "lock-toast";
    toast.style.cssText = `
        position: fixed; bottom: 2rem; right: 2rem;
        background: #111; border: 1.5px solid #ffac2b;
        color: #f0f0f0; font-family: 'Bangers', cursive;
        font-size: 1rem; letter-spacing: 1.5px;
        padding: 14px 22px; border-radius: 10px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.5);
        z-index: 9999; display: flex; align-items: center;
        gap: 10px; animation: toastIn 0.35s ease forwards;
    `;
    toast.innerHTML = `🔒 Get a pack to unlock this!`;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "toastOut 0.3s ease forwards";
        setTimeout(() => toast.remove(), 350);
    }, 1700);
}

/* =====================================================
   CAROUSEL FACTORY
   Creates an independent carousel instance for any
   dataset + set of DOM elements.
===================================================== */
function createCarousel(data, trackId, dotsId, prevId, nextId) {
    const trackEl  = document.getElementById(trackId);
    const dotsWrap = document.getElementById(dotsId);
    const prevEl   = document.getElementById(prevId);
    const nextEl   = document.getElementById(nextId);
    let idx = 0;

    function getCardWidth() {
        const c = trackEl.querySelector(".arch-card");
        return c ? c.offsetWidth + 16 : 216;
    }

    function updateDots() {
        dotsWrap.innerHTML = "";
        data.forEach((_, i) => {
            const dot = document.createElement("div");
            dot.className = `c-dot${i === 0 ? " active" : ""}`;
            dot.addEventListener("click", () => moveTo(i));
            dotsWrap.appendChild(dot);
        });
    }

    function updateTrack() {
        const max = Math.max(0, data.length - CARDS_VISIBLE);
        idx = Math.max(0, Math.min(idx, max));
        trackEl.style.transform = `translateX(-${idx * getCardWidth()}px)`;
        prevEl.disabled = idx === 0;
        nextEl.disabled = idx >= max;
        dotsWrap.querySelectorAll(".c-dot").forEach((d, i) =>
            d.classList.toggle("active", i === idx)
        );
    }

    function moveTo(i) { idx = i; updateTrack(); }

    prevEl.addEventListener("click", () => { idx--; updateTrack(); });
    nextEl.addEventListener("click", () => { idx++; updateTrack(); });
    window.addEventListener("resize", updateTrack);

    function build() {
        trackEl.innerHTML = "";

        data.forEach(arch => {
            const isLocked = arch.locked;

            const avatarHtml = arch.avatar_url
                ? `<img src="${arch.avatar_url}"
                        alt="${arch.name}"
                        style="width:100%;height:300px;object-fit:cover;display:block;">`
                : `<div style="width:100%;height:300px;display:flex;
                               align-items:center;justify-content:center;
                               font-size:3.5rem;background:#0d0d0d;">
                       ${arch.emoji}
                   </div>`;

            const lockHtml = isLocked ? `
                <div class="lock-overlay">
                    <span class="lock-icon">🔒</span>
                    <span class="lock-label">Unlock with a Pack</span>
                </div>` : "";

            const card = document.createElement("div");
            card.className = `arch-card${isLocked ? " locked" : ""}`;
            card.dataset.archId = arch.id;
            if (isLocked) card.dataset.locked = "true";
            card.setAttribute("role", "button");
            card.setAttribute("tabindex", isLocked ? "-1" : "0");
            card.setAttribute("aria-label",
                isLocked ? `${arch.name} — locked` : `Select ${arch.name}`
            );

            card.innerHTML = `
                ${avatarHtml}
                ${lockHtml}
                <div class="arch-card-name">${arch.name}</div>
                ${arch.catchphrase
                    ? `<div class="arch-catchphrase">"${arch.catchphrase}"</div>`
                    : ""}
            `;

            card.addEventListener("click", () => {
                if (isLocked) {
                    showLockToast();
                    setTimeout(() => { window.location.href = "/orders/"; }, 4200);
                    return;
                }
                selectArchetype(arch, card);
            });

            card.addEventListener("keydown", e => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    if (isLocked) {
                        showLockToast();
                        setTimeout(() => { window.location.href = "/orders/"; }, 4200);
                        return;
                    }
                    selectArchetype(arch, card);
                }
            });

            trackEl.appendChild(card);
        });

        updateDots();
        updateTrack();
    }

    return { build, moveTo, trackEl };
}

/* Create one carousel per gender */
const maleCarousel   = createCarousel(
    MALE_ARCHETYPES,
    "carousel-track-m", "carousel-dots-m",
    "carousel-prev-m",  "carousel-next-m"
);
const femaleCarousel = createCarousel(
    FEMALE_ARCHETYPES,
    "carousel-track-f", "carousel-dots-f",
    "carousel-prev-f",  "carousel-next-f"
);

/* =====================================================
   SELECT ARCHETYPE
   Shows the badge under the carousel the archetype
   actually belongs to, and clears the other one so a
   stale badge never lingers under the wrong row.
===================================================== */
function selectArchetype(arch, card) {
    selectedArchetype = arch;

    /* Highlight selected card, clear all others (both carousels) */
    document.querySelectorAll(".arch-card").forEach(c =>
        c.classList.toggle("selected", c === card)
    );

    /* Route badge to the correct carousel row */
    if (arch.gender === 'F') {
        badgeNameF.textContent = arch.name;
        badgeF.classList.add("visible");
        badgeM.classList.remove("visible");
    } else {
        badgeNameM.textContent = arch.name;
        badgeM.classList.add("visible");
        badgeF.classList.remove("visible");
    }

    /* Hidden input */
    hiddenArchetype.value = arch.id;

    /* Steps */
    step1.classList.add("done");
    step1.classList.remove("active");
    step2.classList.add("active");

    /* Reveal style section, reset downstream */
    sectionStyle.classList.add("revealed");
    sectionLines.classList.remove("revealed");
    sectionFinish.classList.remove("revealed");

    styleSelect.value = "";
    linesList.innerHTML = `<div class="disslines-placeholder">Select a roast style above to load your arsenal</div>`;
    hiddenStyle.value = "";

    buildStyleSelect();

    setTimeout(() => sectionStyle.scrollIntoView({ behavior: "smooth", block: "nearest" }), 100);
}

/* Convenience wrapper for init/edit restore — searches across both carousels */
function pickArchetype(id) {
    const arch = ARCHETYPES.find(a => a.id === id);
    if (!arch || arch.locked) return;
    const card = document.querySelector(`[data-arch-id="${id}"]`);
    selectArchetype(arch, card);
}

/* =====================================================
   ROAST STYLE SELECT
===================================================== */
function buildStyleSelect() {
    const grid = document.getElementById("style-avatar-grid");
    grid.innerHTML = "";

    ROAST_STYLES.forEach(s => {
        const card = document.createElement("div");
        card.className = `style-avatar-card${s.locked ? " locked" : ""}`;
        card.dataset.styleId = s.id;

        const imgHtml = s.avatar_url
            ? `<img src="${s.avatar_url}" alt="${s.name}" class="style-avatar-img">`
            : `<div class="style-avatar-emoji">${s.emoji}</div>`;

        card.innerHTML = `
            ${imgHtml}
            <div class="style-avatar-name">${s.name}</div>
            ${s.locked ? `<div class="style-lock-icon">🔒</div>` : ""}
        `;

        card.addEventListener("click", () => {
            if (s.locked) {
                showLockToast();
                setTimeout(() => { window.location.href = "/orders/"; }, 1800);
                return;
            }
            grid.querySelectorAll(".style-avatar-card")
                .forEach(c => c.classList.remove("selected"));
            card.classList.add("selected");
            document.getElementById("roast-style-select").value = s.id;
            hiddenStyle.value = s.id;
            document.getElementById("selected-style-name").textContent = s.name;
            document.getElementById("selected-style-wrap").style.display = "block";
            pickRoastStyle(s.id);
        });

        grid.appendChild(card);
    });
}

function pickRoastStyle(sid) {
    sid = parseInt(sid);
    step2.classList.add("done");
    step2.classList.remove("active");
    step3.classList.add("active");

    if (!sid || !selectedArchetype) {
        linesList.innerHTML = `<div class="disslines-placeholder">Select a roast style above to load your arsenal</div>`;
        sectionLines.classList.remove("revealed");
        sectionPremium.classList.remove("revealed");
        sectionFinish.classList.remove("revealed");
        return;
    }

    const lines = selectedArchetype.diss_lines.filter(l =>
        !l.roast_style_id || l.roast_style_id === sid
    );

    const standardLines = lines.filter(l => !l.is_premium);
    const premiumLines  = lines.filter(l => l.is_premium);

    /* ── Standard lines → Step 3 ── */
    if (standardLines.length) {
        linesList.innerHTML = buildLineItems(standardLines);
    } else {
        linesList.innerHTML = `<div class="disslines-placeholder">
            No standard lines for this combination yet.
        </div>`;
    }
    sectionLines.classList.add("revealed");

    /* ── Premium lines → Step 4 (only if they exist) ── */
    if (premiumLines.length) {
        premiumLinesList.innerHTML = buildLineItems(premiumLines);
        sectionPremium.classList.add("revealed");
        step3.classList.add("done");
        step3.classList.remove("active");
        step4.classList.add("active");
    } else {
        sectionPremium.classList.remove("revealed");
        step3.classList.add("done");
        step3.classList.remove("active");
        step4.classList.add("active");
    }

    /* ── Final Touches → Step 5 ── */
    sectionFinish.classList.add("revealed");
    step4.classList.add("done");
    step4.classList.remove("active");
    step5.classList.add("active");

    /* Re-run limit enforcement across both lists */
    enforceDissLineLimit();

    setTimeout(() => sectionLines.scrollIntoView({ behavior: "smooth", block: "nearest" }), 100);
}

/* =====================================================
   DISS LINES
   Grouped into "Diss Lines" (standard/free) and
   "Premium Diss Categories" (LinkedIn Endorsement,
   Internal Monologue, etc.) using the is_premium flag
   from the backend (driven by RoastCategory.is_free).
===================================================== */
function renderDissLines(lines) {
    if (!lines.length) {
        linesList.innerHTML = `<div class="disslines-placeholder">
            No approved lines for this combination yet — add some via the admin panel.
        </div>`;
        return;
    }

    const standardLines = lines.filter(l => !l.is_premium);
    const premiumLines  = lines.filter(l => l.is_premium);

    let html = "";

    if (standardLines.length) {
        /* Only show the "Diss Lines" header when there's a Premium
           section too — keeps the view clean for free-tier users */
        if (premiumLines.length) {
            html += `
                <div class="dissline-section-label">
                    <i class="fas fa-fire"></i> Diss Lines
                </div>`;
        }
        html += buildLineItems(standardLines);
    }

    if (premiumLines.length) {
        html += `
            <div class="dissline-section-label premium">
                <i class="fas fa-gem"></i> Premium Diss Categories
            </div>`;
        html += buildLineItems(premiumLines);
    }

    linesList.innerHTML = html;
    enforceDissLineLimit();
}

function buildLineItems(lines) {
    return lines.map(line => {
        /*
           CSS classes use dots, not spaces — e.g. "LinkedIn Endorsement"
           becomes "type-LinkedIn.Endorsement" to match the stylesheet.
        */
        const typeClass = line.type.replace(/\s+/g, ".");

        return `
        <label class="dissline-item">
            <input type="checkbox"
                   name="selected_lines"
                   value="${line.id}"
                   ${INIT_LINE_IDS.includes(line.id) ? "checked" : ""}>

            <div class="dissline-content">
                <span class="dissline-type-badge type-${typeClass}">
                    ${line.type}
                </span>

                <div class="dissline-quote-bubble">
                    <div class="dissline-text">${line.content}</div>
                </div>
            </div>
        </label>`;
    }).join("");
}

function enforceDissLineLimit() {
    /* Watch all checkboxes across both standard + premium lists */
    const allCheckboxes = document.querySelectorAll("#disslines-list input[name='selected_lines'], #premium-lines-list input[name='selected_lines']");

    const existing = document.getElementById("line-limit-badge");
    if (existing) existing.remove();

    const limitBadge = document.createElement("div");
    limitBadge.id = "line-limit-badge";
    limitBadge.style.cssText = `
        font-family: 'Bangers', cursive;
        font-size: 0.82rem; letter-spacing: 1px;
        color: #555; margin-bottom: 8px;
    `;

    const countChecked = () =>
    document.querySelectorAll("#disslines-list input[name='selected_lines']:checked, #premium-lines-list input[name='selected_lines']:checked").length;

    const updateBadge = () => {
        const checked = countChecked();
        limitBadge.textContent = `${checked} / ${MAX_LINE_SELECTIONS} lines selected`;
        limitBadge.style.color = checked >= MAX_LINE_SELECTIONS ? "#ffac2b" : "#555";
    };

    linesList.insertAdjacentElement("beforebegin", limitBadge);
    updateBadge();

    allCheckboxes.forEach(cb => {
        cb.addEventListener("change", () => {
            if (countChecked() > MAX_LINE_SELECTIONS) {
                cb.checked = false;
                showLimitToast();
            }
            updateBadge();
        });
    });
}


function showLimitToast() {
    const existing = document.getElementById("limit-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.id = "limit-toast";
    toast.style.cssText = `
        position: fixed; bottom: 2rem; right: 2rem;
        background: #111; border: 1.5px solid #e8621a;
        color: #f0f0f0; font-family: 'Bangers', cursive;
        font-size: 1rem; letter-spacing: 1.5px;
        padding: 14px 22px; border-radius: 10px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.5);
        z-index: 9999; display: flex; align-items: center;
        gap: 10px; animation: toastIn 0.35s ease forwards;
    `;
    toast.innerHTML = `
        🔥 Limit reached! Uncheck one to swap —
        or <a href="/orders/" style="color:#ffac2b; margin-left:4px;">upgrade for more</a>
    `;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "toastOut 0.3s ease forwards";
        setTimeout(() => toast.remove(), 350);
    }, 4200);
}

function showEmptyLinesToast() {
    const existing = document.getElementById("empty-lines-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.id = "empty-lines-toast";
    toast.style.cssText = `
        position: fixed; bottom: 2rem; right: 2rem;
        background: #111; border: 1.5px solid #ffac2b;
        color: #f0f0f0; font-family: 'Bangers', cursive;
        font-size: 1rem; letter-spacing: 1.5px;
        padding: 14px 22px; border-radius: 10px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.5);
        z-index: 9999; display: flex; align-items: center;
        gap: 10px; animation: toastIn 0.35s ease forwards;
        max-width: 420px;
        line-height: 1.35;
    `;

    toast.innerHTML = `
        💌 So, you want to fire a diss with no diss lines?
        Bold strategy. Maybe buy a Hallmark card.
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "toastOut 0.3s ease forwards";
        setTimeout(() => toast.remove(), 350);
    }, 2800);
}

/* =====================================================
   VISIBILITY TOGGLE
===================================================== */
function setVisibility(status, isPublic) {
    hiddenStatus.value = status;
    hiddenPublic.value = isPublic ? "true" : "false";
    document.getElementById("vis-draft").classList.toggle("chosen", status === "draft");
    document.getElementById("vis-published").classList.toggle("chosen", status === "published");
}

window.setVisibility = setVisibility;

/* =====================================================
   FORM SUBMIT GUARD
===================================================== */
document.getElementById("diss-form").addEventListener("submit", function(e) {
    if (!hiddenArchetype.value) {
        e.preventDefault();
        alert("Please select a target archetype first!");
        return;
    }

    if (!hiddenStyle.value) {
        e.preventDefault();

        const grid = document.getElementById("style-avatar-grid");
        grid.style.outline = "1.5px solid #c0392b";

        setTimeout(() => {
            grid.style.outline = "";
        }, 1500);

        return;
    }

    const checked = document.querySelectorAll("input[name='selected_lines']:checked");

    if (!checked.length) {
        e.preventDefault();

        showEmptyLinesToast();

        linesList.style.outline = "1.5px solid #ffac2b";

        if (premiumLinesList) {
            premiumLinesList.style.outline = "1.5px solid #ffac2b";
        }

        setTimeout(() => {
            linesList.style.outline = "";

            if (premiumLinesList) {
                premiumLinesList.style.outline = "";
            }
        }, 6800);

        sectionLines.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

        return;
    }
});

/* =====================================================
   INIT — build both carousels, restore on edit
===================================================== */
maleCarousel.build();
femaleCarousel.build();

if (INIT_ARCHETYPE_ID) {
    pickArchetype(INIT_ARCHETYPE_ID);
    /* Scroll the correct carousel to show the pre-selected card */
    const initArch = ARCHETYPES.find(a => a.id === INIT_ARCHETYPE_ID);
    if (initArch) {
        const isFemale = initArch.gender === 'F';
        const data     = isFemale ? FEMALE_ARCHETYPES : MALE_ARCHETYPES;
        const carousel = isFemale ? femaleCarousel    : maleCarousel;
        const i        = data.findIndex(a => a.id === INIT_ARCHETYPE_ID);
        if (i >= 0) carousel.moveTo(Math.max(0, i - 1));
    }
}

if (INIT_ROAST_STYLE_ID) {
    setTimeout(() => {
        styleSelect.value = INIT_ROAST_STYLE_ID;
        styleSelect.dispatchEvent(new Event("change"));
    }, 50);
}