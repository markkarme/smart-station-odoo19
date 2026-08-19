(function () {
    "use strict";

    function toggleAllocationTypeFields() {
        const select = document.getElementById("holiday_status_id");
        const unitLabel = document.getElementById("allocation_unit_label");
        if (!select || !unitLabel) {
            return;
        }

        const option = select.options[select.selectedIndex];
        const requestUnit = option && option.value ? option.dataset.requestUnit || "day" : "day";
        unitLabel.textContent = requestUnit === "hour" ? "Hours" : "Days";
    }

    document.addEventListener("DOMContentLoaded", function () {
        const select = document.getElementById("holiday_status_id");
        const form = document.getElementById("portal_allocation_form");

        if (select) {
            select.addEventListener("change", toggleAllocationTypeFields);
            toggleAllocationTypeFields();
        }
        if (form) {
            form.addEventListener("submit", function () {
                const submitButton = form.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.textContent = "Submitting...";
                }
            });
        }
    });
})();
