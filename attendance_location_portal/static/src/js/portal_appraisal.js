(function () {
    "use strict";
    function initPortalAppraisalFeedback() {
        const form = document.getElementById("portal_appraisal_feedback_form");
        if (!form) {
            return;
        }
        const editor = document.getElementById("portal_appraisal_feedback_editor");
        const input = document.getElementById("employee_feedback_input");
        if (!editor || !input) {
            return;
        }
        form.addEventListener("submit", function () {
            input.value = editor.innerHTML.trim();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initPortalAppraisalFeedback);
    } else {
        initPortalAppraisalFeedback();
    }
})();
