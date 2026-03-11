/**
 * Dashboard Tour — powered by Driver.js
 * Auto-detects page and shows a context-aware guided tour.
 * Loads Driver.js from CDN at runtime to avoid bundling.
 */

(function () {
    "use strict";

    // ─── 1. Load Driver.js CSS + JS from CDN ───
    var DRIVER_CSS = "https://cdn.jsdelivr.net/npm/driver.js@1.3.1/dist/driver.css";
    var DRIVER_JS  = "https://cdn.jsdelivr.net/npm/driver.js@1.3.1/dist/driver.js.iife.js";

    function loadCSS(href) {
        if (document.querySelector('link[href="' + href + '"]')) return;
        var link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = href;
        document.head.appendChild(link);
    }

    function loadScript(src, cb) {
        if (window.driver) { cb(); return; }
        var s = document.createElement("script");
        s.src = src;
        s.onload = cb;
        document.head.appendChild(s);
    }

    loadCSS(DRIVER_CSS);

    // ─── 2. Per-page tour step definitions ───
    // Each page returns an array of { element, popover } objects.
    // `element` is a CSS selector; missing elements are auto-skipped.

    var TOURS = {

        "/": function () {
            return [
                { element: "#page-title-display",      popover: { title: "Welcome! 👋", description: "This is the <b>Overview</b> page — your starting point. Upload your VTU result file here to begin.", side: "bottom" }},
                { element: "#upload-data",              popover: { title: "Upload Results 📂", description: "Click or drag-and-drop your VTU result Excel/CSV file here. The dashboard parses it automatically.", side: "bottom" }},
                { element: "#btn-sample-format",        popover: { title: "View Sample Format", description: "Not sure about the file format? Click here to see an example of the expected structure.", side: "bottom" }},
                { element: "#scheme-selector",          popover: { title: "Select Scheme 📋", description: "Choose the VTU scheme year (e.g. 2022 or 2025). This is used for SGPA credit mapping.", side: "bottom" }},
                { element: "#semester-selector",        popover: { title: "Select Semester", description: "Pick the semester of the uploaded result. Credits are auto-loaded from the database based on this.", side: "bottom" }},
                { element: "#submit-scheme-btn",        popover: { title: "Apply Scheme", description: "After selecting scheme & semester, click here to apply. This enables SGPA calculations on the Ranking page.", side: "left" }},
                { element: "#subject-selector",         popover: { title: "Filter Subjects 🔍", description: "Select or deselect subjects to customize which ones appear in the analysis. Use Select All / Remove All for quick changes.", side: "bottom" }},
                { element: "#config-mode-selector",     popover: { title: "Section Configuration", description: "Choose <b>Manual</b> to define section ranges by USN, or <b>Upload</b> to upload a section-mapping file.", side: "bottom" }},
                { element: "#data-preview",             popover: { title: "Data Preview Table 📊", description: "Your uploaded result data appears here with all computed metrics — Total Marks, Pass/Fail, Percentage, etc.", side: "top" }},
                { element: "#universal-download-btn",   popover: { title: "Download Data ⬇️", description: "Export the current table view as an Excel file for offline use or sharing.", side: "left" }},
                { element: "#open-legend-overview",     popover: { title: "Rules & Guidelines 📖", description: "Click to see detailed rules — how pass/fail is determined, how percentage is calculated, and more.", side: "left" }},
                { popover: { title: "You're all set! 🎉", description: "Upload a result file and explore the data. Navigate to other pages using the top navbar. Click the <b>🎓 Tour</b> button anytime to replay this guide." }}
            ];
        },

        "/ranking": function () {
            return [
                { element: "#page-title-display",             popover: { title: "Ranking Page 🏆", description: "This page ranks students by <b>Total Marks</b> or <b>SGPA</b>. Make sure you've uploaded data on the Overview page first.", side: "bottom" }},
                { element: "#filter-dropdown",                popover: { title: "Filter by Result", description: "Show <b>All</b>, <b>Passed</b>, <b>Failed</b>, or <b>Absent</b> students. The entire page updates based on this filter.", side: "bottom" }},
                { element: "#section-dropdown",               popover: { title: "Filter by Section", description: "Narrow down to a specific section or view all sections together.", side: "bottom" }},
                { element: "#search-input",                   popover: { title: "Search Student 🔍", description: "Type a USN or Name to instantly find a specific student in the ranking table.", side: "bottom" }},
                { element: "#open-legend",                    popover: { title: "Rules & Guidelines", description: "Comprehensive guide explaining ranking logic, pass/fail criteria, SGPA formula, and VTU categories.", side: "left" }},
                { element: "#ranking-type",                   popover: { title: "Marks vs SGPA Mode", description: "Switch between <b>Marks Based</b> (raw total) and <b>SGPA Based</b> (credit-weighted grade points). SGPA mode opens a credit configuration panel.", side: "top" }},
                { element: "#marks-metric-selector",          popover: { title: "Metric Selector", description: "In Marks mode, choose to rank by <b>Total</b>, <b>Internal</b>, or <b>External</b> marks.", side: "top" }},
                { element: "#theme-toggle",                   popover: { title: "Dark Mode 🌙", description: "Toggle between light and dark themes for comfortable viewing.", side: "right" }},
                { element: "#kpi-cards",                      popover: { title: "Performance KPIs 📈", description: "Quick overview — Total students, Passed, Failed, Absent, Pass %, and VTU categories (FCD, FC, SC). <b>Click any card</b> to see the detailed student list.", side: "bottom" }},
                { element: "#export-all-kpis",                popover: { title: "Download KPI Report", description: "Export a consolidated Excel with separate sheets for each KPI category (FCD, FC, Failed, etc.).", side: "left" }},
                { element: "#category-breakdown-container",   popover: { title: "VTU Category Breakdown", description: "Section-wise breakdown showing how many students fall into each VTU category. Expandable accordions with student lists.", side: "top" }},
                { element: "#overall-top5",                   popover: { title: "Top 5 Overall 🥇", description: "The 5 highest-scoring students across all sections.", side: "right" }},
                { element: "#section-toppers",                popover: { title: "Section Toppers 🏆", description: "The top scorer from each section with their class rank.", side: "bottom" }},
                { element: "#bottom-five",                    popover: { title: "Bottom 5 ⬇️", description: "The 5 lowest-scoring students. Useful for identifying students who need support.", side: "left" }},
                { element: "#ranking-table",                  popover: { title: "Detailed Ranking Table", description: "Full sortable table with ranks, marks, and results. <b>Click any row</b> to open the student's detailed profile modal.", side: "top" }},
                { element: "#export-xlsx",                    popover: { title: "Download Excel", description: "Export the entire ranking table as a styled Excel file.", side: "left" }},
                { popover: { title: "Ranking Tour Complete! 🎉", description: "Explore the data, click KPI cards for drill-downs, and switch to SGPA mode for credit-based ranking." }}
            ];
        },

        "/subject_analysis": function () {
            return [
                { element: "#page-title-display",        popover: { title: "Subject Analysis 📚", description: "Analyze subject-wise performance — pass rates, average marks, and trends across subjects.", side: "bottom" }},
                { element: "#sa-subject-checklist",      popover: { title: "Select Subjects", description: "Check/uncheck subjects to include in the analysis. The charts and tables update instantly.", side: "right" }},
                { element: "#sa-section-filter",         popover: { title: "Section Filter", description: "Filter analysis to a specific section or view all sections.", side: "bottom" }},
                { element: "#sa-result-filter",          popover: { title: "Result Filter", description: "Focus on All, Passed, or Failed students to understand performance patterns.", side: "bottom" }},
                { element: "#sa-kpi-cards",              popover: { title: "Subject KPIs 📊", description: "Key metrics — total students, average marks, pass %, and more. <b>Click any card</b> for detailed student lists.", side: "bottom" }},
                { element: "#sa-chart-tabs",             popover: { title: "Visualization Charts", description: "Switch between Pie, Bar, and other chart types to explore subject performance visually.", side: "top" }},
                { element: "#sa-subject-table",          popover: { title: "Subject-wise Table", description: "Detailed per-subject breakdown with pass/fail counts and percentages.", side: "top" }},
                { element: "#sa-summary-table",          popover: { title: "Summary Table", description: "Consolidated summary across all selected subjects.", side: "top" }},
                { element: "#sa-export-xlsx",            popover: { title: "Export Data", description: "Download subject analysis data as Excel for offline use.", side: "left" }},
                { element: "#sa-open-legend",            popover: { title: "Rules & Guidelines", description: "Detailed explanation of how subject analysis metrics are computed.", side: "left" }},
                { popover: { title: "Subject Analysis Complete! 🎉", description: "Select subjects, explore charts, and export reports." }}
            ];
        },

        "/student_detail": function () {
            return [
                { element: "#page-title-display",         popover: { title: "Student Detail 🎓", description: "Deep dive into an individual student's performance — search by USN to view their complete result profile.", side: "bottom" }},
                { element: "#student-search",             popover: { title: "Search by USN 🔍", description: "Enter a student's USN (University Seat Number) to look up their detailed results.", side: "bottom" }},
                { element: "#student-subject-dropdown",   popover: { title: "Subject Filter", description: "Optionally filter to view specific subjects only.", side: "bottom" }},
                { element: "#search-btn",                 popover: { title: "Search Button", description: "Click to fetch the student's data and display their performance analysis.", side: "right" }},
                { element: "#analysis-type-radio",        popover: { title: "Marks vs SGPA", description: "Toggle between viewing raw marks or SGPA-based analysis for the student.", side: "bottom" }},
                { element: "#student-detail-content",     popover: { title: "Results Display", description: "The student's complete subject-wise breakdown appears here — Internal, External, Total, Result, and overall statistics.", side: "top" }},
                { element: "#sd-open-legend",             popover: { title: "Rules & Guidelines", description: "How student metrics are calculated — percentage, SGPA, pass/fail criteria.", side: "left" }},
                { popover: { title: "Student Detail Complete! 🎉", description: "Search for any student by USN to view their complete performance profile." }}
            ];
        },

        "/branch-analysis": function () {
            return [
                { element: "#page-title-display",         popover: { title: "Branch Analysis 🏫", description: "Compare performance across multiple branches/departments. Upload result files for each branch.", side: "bottom" }},
                { element: "#ba-open-legend",             popover: { title: "Rules & Guidelines", description: "Detailed guide on how branch comparison metrics are calculated.", side: "left" }},
                { element: "#ba-branch-count",            popover: { title: "Number of Branches", description: "Enter how many branches you want to compare (e.g. 3 for CSE, ISE, ECE).", side: "bottom" }},
                { element: "#ba-generate-btn",            popover: { title: "Generate Inputs", description: "Click to generate name + file upload fields for each branch.", side: "right" }},
                { element: "#ba-input-container",         popover: { title: "Branch Inputs", description: "Enter branch names and upload their respective result files here.", side: "bottom" }},
                { element: "#ba-analyze-container",       popover: { title: "Analyze Button", description: "After uploading all files, click <b>Analyze & Generate</b> to build the comparison dashboard.", side: "top" }},
                { element: "#ba-dashboard-view",          popover: { title: "Dashboard Output", description: "The comparative analysis appears here — KPIs, charts, subject-wise comparison, and branch rankings.", side: "top" }},
                { element: "#ba-download-excel-btn",      popover: { title: "Export Reports", description: "Download the branch comparison as Excel, CSV, or PDF for sharing.", side: "left" }},
                { popover: { title: "Branch Analysis Complete! 🎉", description: "Upload multiple branch files to compare performance across departments." }}
            ];
        }
    };

    // ─── 3. Tour engine ───

    function getPage() {
        return window.location.pathname.replace(/\/+$/, "") || "/";
    }

    function filterSteps(steps) {
        // Remove steps whose target element doesn't exist on the page
        return steps.filter(function (s) {
            if (!s.element) return true;  // summary step (no element)
            return document.querySelector(s.element) !== null;
        });
    }

    // ─── 3a. Universal skip flag ───
    // Stored on window so it survives even if this IIFE re-runs
    window.__tourSkippedAll = window.__tourSkippedAll || !!sessionStorage.getItem("tour_skipped_all");

    function isSkipped() {
        return window.__tourSkippedAll || sessionStorage.getItem("tour_skipped_all") === "1";
    }

    function markSkipped() {
        window.__tourSkippedAll = true;
        sessionStorage.setItem("tour_skipped_all", "1");
    }

    // ─── 3b. Active driver ref ───
    var _activeDriver = null;

    function killTour() {
        if (_activeDriver) {
            var d = _activeDriver;
            _activeDriver = null;
            try { d.destroy(); } catch (e) {}
            // Belt-and-suspenders: force-remove any leftover overlay
            document.querySelectorAll(".driver-popover, .driver-overlay").forEach(function (el) {
                el.remove();
            });
        }
        var sb = document.getElementById("tour-skip-floating");
        if (sb) sb.style.display = "none";
    }

    // ─── 3c. Floating Skip button (OUTSIDE Driver.js DOM) ───
    var _skipBtn = document.getElementById("tour-skip-floating");
    if (!_skipBtn) {
        _skipBtn = document.createElement("button");
        _skipBtn.textContent = "Skip Tour ✕";
        _skipBtn.id = "tour-skip-floating";
        _skipBtn.style.cssText =
            "display:none; position:fixed; bottom:24px; left:24px; z-index:1100000;" +
            "padding:8px 18px; font-size:14px; font-weight:600; border-radius:8px;" +
            "background:#fff; color:#ef4444; border:2px solid #fca5a5; cursor:pointer;" +
            "box-shadow:0 4px 16px rgba(0,0,0,0.25); transition:all 0.2s ease;";
        _skipBtn.onmouseenter = function () { _skipBtn.style.background = "#fef2f2"; _skipBtn.style.borderColor = "#ef4444"; };
        _skipBtn.onmouseleave = function () { _skipBtn.style.background = "#fff"; _skipBtn.style.borderColor = "#fca5a5"; };
        document.body.appendChild(_skipBtn);

        _skipBtn.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            markSkipped();
            killTour();
        });
    }

    // ─── 3d. Launch driver ───
    function _launchDriver(manual) {
        // Block auto-triggered tours if skipped
        if (!manual && isSkipped()) return;

        loadScript(DRIVER_JS, function () {
            // Re-check after async script load
            if (!manual && isSkipped()) return;

            var page = getPage();
            var stepsFn = TOURS[page];
            if (!stepsFn) {
                stepsFn = function () {
                    return [{ popover: { title: "Welcome! 👋", description: "Navigate to a page and click the Tour button to get a guided walkthrough." }}];
                };
            }

            var rawSteps = stepsFn();
            var steps = filterSteps(rawSteps);

            if (steps.length === 0) {
                steps = [{ popover: { title: "No Tour Available", description: "Upload data first — the tour highlights elements that appear after data is loaded." }}];
            }

            var driverObj = window.driver.js.driver({
                showProgress: true,
                showButtons: ["next", "previous", "close"],
                allowClose: true,
                animate: true,
                overlayColor: "rgba(0, 0, 0, 0.6)",
                stagePadding: 8,
                stageRadius: 10,
                popoverClass: "dashboard-tour-popover",
                nextBtnText: "Next →",
                prevBtnText: "← Back",
                doneBtnText: "Done ✓",
                progressText: "{{current}} of {{total}}",
                steps: steps
            });

            _activeDriver = driverObj;
            _skipBtn.style.display = "block";
            driverObj.drive();
        });
    }

    // Expose globally — FAB button = manual (always works, even after skip)
    window.__startDashboardTour = function () { _launchDriver(true); };

    // ─── 4. Auto-show tour on first visit (per page) ───
    function autoShowOnce() {
        if (isSkipped()) return;

        var page = getPage();
        var key = "tour_seen_" + page.replace(/\//g, "_");
        if (sessionStorage.getItem(key)) return;

        sessionStorage.setItem(key, "1");  // mark seen immediately to prevent double-fire
        setTimeout(function () {
            if (isSkipped()) return;
            _launchDriver(false);
        }, 1500);
    }

    // Wait for DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", autoShowOnce);
    } else {
        setTimeout(autoShowOnce, 1500);
    }

    // Listen for Dash SPA navigation (URL changes)
    var _lastPath = getPage();
    setInterval(function () {
        var cur = getPage();
        if (cur !== _lastPath) {
            _lastPath = cur;
            // Kill any active tour from previous page
            killTour();
            autoShowOnce();
        }
    }, 500);

})();
