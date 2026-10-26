/** @odoo-module **/

(function () {
    "use strict";

    var STORAGE_KEY = "portal_school_mold_expanded";
    var bound = false;

    function setExpanded(expanded) {
        document.body.classList.toggle("o_portal_mold_expanded", !!expanded);
        try {
            sessionStorage.setItem(STORAGE_KEY, expanded ? "1" : "0");
        } catch (_error) {
            // Ignore storage errors.
        }
        document.querySelectorAll(".o_portal_mold_expand_btn").forEach(function (button) {
            button.setAttribute("aria-pressed", expanded ? "true" : "false");
            var icon = button.querySelector("i.fa");
            if (icon) {
                icon.classList.toggle("fa-expand", !expanded);
                icon.classList.toggle("fa-compress", !!expanded);
            }
        });
    }

    function toggleExpanded() {
        setExpanded(!document.body.classList.contains("o_portal_mold_expanded"));
    }

    function setupPortalSchoolMold() {
        if (!document.querySelector(".o_portal_mold_sheet")) {
            return;
        }
        if (!bound) {
            bound = true;
            document.addEventListener("click", function (event) {
                var button = event.target.closest(".o_portal_mold_expand_btn");
                if (!button) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                toggleExpanded();
            });
            document.addEventListener("keydown", function (event) {
                if (
                    event.key === "Escape" &&
                    document.body.classList.contains("o_portal_mold_expanded")
                ) {
                    setExpanded(false);
                }
            });
        }
        var preferExpanded = false;
        try {
            preferExpanded = sessionStorage.getItem(STORAGE_KEY) === "1";
        } catch (_error) {
            preferExpanded = false;
        }
        if (preferExpanded) {
            setExpanded(true);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupPortalSchoolMold);
    } else {
        setupPortalSchoolMold();
    }
})();
