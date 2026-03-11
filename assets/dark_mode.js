/**
 * Dark Mode Engine — handles everything CSS alone can't:
 *  1. Inline styles on Dash containers (background, color)
 *  2. Plotly chart relayout (paper_bgcolor, font, axes, gridlines)
 *  3. DataTable conditional row color patching
 *
 * Works with data-theme="dark" on <html>, persisted via dcc.Store + localStorage.
 */
(function () {
    "use strict";

    /* ─── 0. APPLY SAVED THEME IMMEDIATELY (prevent FOUC) ─── */
    var saved = localStorage.getItem("theme-store");
    if (saved) {
        try {
            if (JSON.parse(saved) === "dark") {
                document.documentElement.setAttribute("data-theme", "dark");
            }
        } catch (e) { /* ignore */ }
    }

    /* ─── DARK / LIGHT color palettes ─── */
    var DARK = {
        mainBg:    "#0f172a",
        cardBg:    "#1e293b",
        titleBg:   "#1e293b",
        titleShadow: "0 4px 14px rgba(0,0,0,0.3)",
        footerBg:  "#1e293b",
        footerTxt: "#94a3b8",
        footerBdr: "#334155",
        /* Plotly */
        paperBg:   "#1e293b",
        plotBg:    "#1e293b",
        fontColor: "#e2e8f0",
        gridColor: "#334155",
        axisColor: "#94a3b8",
        titleColor:"#f1f5f9"
    };
    var LIGHT = {
        mainBg:    "#f3f4f6",
        cardBg:    "white",
        titleBg:   "white",
        titleShadow: "0 4px 14px rgba(0,0,0,0.06)",
        footerBg:  "#e9ecef",
        footerTxt: "#333",
        footerBdr: "#ced4da",
        /* Plotly */
        paperBg:   "white",
        plotBg:    "rgba(248,249,250,0.5)",
        fontColor: "#1f2937",
        gridColor: "#e0e0e0",
        axisColor: "#6b7280",
        titleColor:"#2c3e50"
    };

    function isDark() {
        return document.documentElement.getAttribute("data-theme") === "dark";
    }

    function pal() { return isDark() ? DARK : LIGHT; }

    /* ─── 1. PATCH INLINE STYLES (containers with hardcoded bg/color) ─── */
    function patchContainers() {
        var p = pal();

        // Main container (#main-container has inline bg)
        var main = document.getElementById("main-container");
        if (main) main.style.backgroundColor = p.mainBg;

        // Page title (inline bg: white)
        var title = document.getElementById("page-title-display");
        if (title) {
            title.style.background = p.titleBg;
            title.style.boxShadow = p.titleShadow;
        }

        // Page content wrapper (inline bg: white)
        var content = document.getElementById("page-content-wrapper");
        if (content) {
            content.style.background = isDark() ? p.mainBg : p.cardBg;
            content.style.boxShadow = p.titleShadow;
        }

        // Footer (inline bg/color/border)
        var footer = document.getElementById("footer-content");
        if (footer) {
            footer.style.backgroundColor = p.footerBg;
            footer.style.color = p.footerTxt;
            footer.style.borderColor = p.footerBdr;
        }
    }

    /* ─── 2. RELAYOUT ALL PLOTLY CHARTS ─── */
    function relayoutPlotly() {
        var p = pal();
        var plots = document.querySelectorAll(".js-plotly-plot");
        plots.forEach(function (el) {
            if (typeof Plotly !== "undefined" && el.data) {
                try {
                    Plotly.relayout(el, {
                        paper_bgcolor: p.paperBg,
                        plot_bgcolor:  p.plotBg,
                        font: { color: p.fontColor },
                        "title.font.color": p.titleColor,
                        "xaxis.color":     p.axisColor,
                        "xaxis.gridcolor": p.gridColor,
                        "xaxis.tickfont.color": p.axisColor,
                        "xaxis.title.font.color": p.axisColor,
                        "yaxis.color":     p.axisColor,
                        "yaxis.gridcolor": p.gridColor,
                        "yaxis.tickfont.color": p.axisColor,
                        "yaxis.title.font.color": p.axisColor,
                        "legend.font.color": p.fontColor
                    });
                } catch (e) { /* some charts might not have axes */ }
            }
        });
    }

    /* ─── 3. PATCH DATATABLE CONDITIONAL ROWS ─── */
    function patchDataTableRows() {
        if (!isDark()) return; // Only override in dark mode; light mode uses original colors

        var cells = document.querySelectorAll(
            ".dash-table-container .dash-spreadsheet-inner td"
        );
        cells.forEach(function (td) {
            var bg = td.style.backgroundColor;
            if (!bg) return;
            // Map light conditional backgrounds → dark equivalents
            var map = {
                // Fail rows (light red)
                "rgb(255, 241, 242)": { bg: "#7f1d1d", c: "#fecaca" },
                "rgb(254, 242, 242)": { bg: "#7f1d1d", c: "#fecaca" },
                "rgb(254, 226, 226)": { bg: "#7f1d1d", c: "#fecaca" },
                // Pass rows (light green)
                "rgb(236, 253, 245)": { bg: "#064e3b", c: "#a7f3d0" },
                "rgb(240, 253, 244)": { bg: "#064e3b", c: "#a7f3d0" },
                // Absent rows (light amber)
                "rgb(255, 251, 235)": { bg: "#78350f", c: "#fde68a" },
                // Selected (light blue)
                "rgba(59, 130, 246, 0.1)": { bg: "rgba(59, 130, 246, 0.2)", c: "#e2e8f0" },
                // Pass badge cell (solid green)
                "rgb(34, 197, 94)":  { bg: "#16a34a", c: "#fff" },
                // Fail badge cell (solid red)
                "rgb(239, 68, 68)":  { bg: "#dc2626", c: "#fff" },
                // White / very light grays → dark card
                "rgb(255, 255, 255)": { bg: "#1e293b", c: "#e2e8f0" },
                "white":              { bg: "#1e293b", c: "#e2e8f0" },
                "rgb(243, 244, 246)": { bg: "#1a2535", c: "#e2e8f0" },
                "rgb(248, 250, 252)": { bg: "#1a2535", c: "#e2e8f0" },
                "rgb(248, 249, 250)": { bg: "#1a2535", c: "#e2e8f0" },
                // Odd row very light
                "rgba(0, 0, 0, 0.02)": { bg: "#1a2535", c: "#e2e8f0" }
            };
            var m = map[bg];
            if (m) {
                td.style.backgroundColor = m.bg;
                td.style.color = m.c;
            }
        });
    }

    /* ─── MASTER APPLY ─── */
    function applyAll() {
        patchContainers();
        // Plotly needs a short delay after page render
        setTimeout(relayoutPlotly, 200);
        setTimeout(patchDataTableRows, 300);
    }

    /* ─── OBSERVERS & EVENT HOOKS ─── */

    // Watch for data-theme attribute changes on <html>
    new MutationObserver(function (mutations) {
        mutations.forEach(function (m) {
            if (m.attributeName === "data-theme") applyAll();
        });
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    // Watch for NEW Plotly charts / DataTable re-renders
    var bodyObserver = new MutationObserver(function () {
        if (isDark()) {
            // Debounce: only relayout if charts exist
            clearTimeout(bodyObserver._timer);
            bodyObserver._timer = setTimeout(function () {
                relayoutPlotly();
                patchDataTableRows();
            }, 400);
        }
    });

    function startBodyObserver() {
        bodyObserver.observe(document.body, { childList: true, subtree: true });
    }

    // Initial apply
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            setTimeout(applyAll, 300);
            startBodyObserver();
        });
    } else {
        setTimeout(applyAll, 300);
        startBodyObserver();
    }

    // SPA navigation: re-apply on URL change
    var _lastHref = location.href;
    setInterval(function () {
        if (location.href !== _lastHref) {
            _lastHref = location.href;
            setTimeout(applyAll, 500);
        }
    }, 300);
})();
