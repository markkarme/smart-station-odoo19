/** @odoo-module **/

import { whenReady } from "@odoo/owl";

const CHECKED = "☑";
const UNCHECKED = "☐";

function setChecked(el, checked) {
    el.textContent = checked ? CHECKED : UNCHECKED;
    el.classList.toggle("ss-rating-checked", checked);
    // Keep a durable hint that survives sanitize better than aria attrs
    if (checked) {
        el.setAttribute("title", "محدد — اضغط لإلغاء التحديد");
    } else {
        el.setAttribute("title", "اضغط للاختيار");
    }
}

function isChecked(el) {
    return el.classList.contains("ss-rating-checked") || (el.textContent || "").includes(CHECKED);
}

function findCheck(target) {
    if (!(target instanceof Element)) {
        return null;
    }
    return (
        target.closest(".ss-rating-check") ||
        target.closest("td.ss-rating-cell")?.querySelector(".ss-rating-check")
    );
}

function inAppraisalEditor(el) {
    return Boolean(el.closest(".ss-appraisal-sheet, .o_appraisal_form, .o_field_html"));
}

function clearCaret() {
    const sel = window.getSelection?.();
    if (sel && sel.rangeCount) {
        sel.removeAllRanges();
    }
}

function notifyEditor(el) {
    const editable = el.closest(
        ".odoo-editor-editable, .o-contenteditable, [contenteditable='true'], .o_field_html"
    );
    if (!editable) {
        return;
    }
    editable.dispatchEvent(new InputEvent("input", { bubbles: true, cancelable: true }));
    editable.dispatchEvent(new Event("change", { bubbles: true }));
}

function onRatingPointerDown(ev) {
    // Avoid double-toggle: ignore mousedown when PointerEvent exists
    if (ev.type === "mousedown" && typeof window.PointerEvent !== "undefined") {
        return;
    }

    const el = findCheck(ev.target);
    if (!el || !inAppraisalEditor(el)) {
        return;
    }

    // Stop HTML editor caret / text editing on the rating glyph
    ev.preventDefault();
    ev.stopPropagation();
    if (typeof ev.stopImmediatePropagation === "function") {
        ev.stopImmediatePropagation();
    }

    const row = el.closest("tr");
    const wasChecked = isChecked(el);

    if (row) {
        row.querySelectorAll(".ss-rating-check").forEach((box) => setChecked(box, false));
    }
    if (!wasChecked) {
        setChecked(el, true);
    }

    clearCaret();
    notifyEditor(el);
}

function blockEditorInteraction(ev) {
    const el = findCheck(ev.target);
    if (!el || !inAppraisalEditor(el)) {
        return;
    }
    ev.preventDefault();
    ev.stopPropagation();
    if (typeof ev.stopImmediatePropagation === "function") {
        ev.stopImmediatePropagation();
    }
}

function ensureNonEditable(root = document) {
    root.querySelectorAll?.(".ss-rating-check").forEach((el) => {
        el.classList.add("o-contenteditable-false");
        el.setAttribute("contenteditable", "false");
    });
}

whenReady(() => {
    document.addEventListener("pointerdown", onRatingPointerDown, true);
    document.addEventListener("mousedown", onRatingPointerDown, true);
    document.addEventListener("click", blockEditorInteraction, true);
    document.addEventListener("mouseup", blockEditorInteraction, true);

    ensureNonEditable();
    // HTML fields remount; keep marks non-editable after editor normalize
    const mo = new MutationObserver((mutations) => {
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (node.nodeType === 1) {
                    if (node.matches?.(".ss-rating-check, .ss-appraisal-sheet, .o_field_html")) {
                        ensureNonEditable(node);
                    } else if (node.querySelector?.(".ss-rating-check")) {
                        ensureNonEditable(node);
                    }
                }
            }
        }
    });
    mo.observe(document.body, { childList: true, subtree: true });
});
