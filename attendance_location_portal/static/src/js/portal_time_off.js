(function () {
    "use strict";

    function toggleLeaveTypeFields() {
        const select = document.getElementById("holiday_status_id");
        if (!select) {
            return;
        }

        const option = select.options[select.selectedIndex];
        const requestUnit = option && option.value ? option.dataset.requestUnit || "day" : "day";
        const supportDocument = option ? option.dataset.supportDocument === "1" : false;
        const requiresAllocation = option ? option.dataset.requiresAllocation === "1" : false;
        const remaining = option ? option.dataset.remaining : "";

        const halfDayFields = document.getElementById("half_day_fields");
        const hourFields = document.getElementById("hour_fields");
        const dateToWrapper = document.getElementById("request_date_to_wrapper");
        const dateSeparator = document.getElementById("date_range_separator");
        const halfDayToPeriod = document.getElementById("half_day_to_period_wrapper");
        const balance = document.getElementById("leave_type_balance");
        const attachmentHint = document.getElementById("attachment_required_hint");
        const dateToInput = document.getElementById("request_date_to");
        const attachmentsInput = document.getElementById("attachments");

        if (halfDayFields) {
            halfDayFields.classList.toggle("d-none", requestUnit !== "half_day");
        }
        if (hourFields) {
            hourFields.classList.toggle("d-none", requestUnit !== "hour");
        }

        const isHourRequest = requestUnit === "hour";
        if (dateToWrapper) {
            dateToWrapper.classList.toggle("d-none", isHourRequest);
        }
        if (dateSeparator) {
            dateSeparator.classList.toggle("d-none", isHourRequest);
        }
        if (dateToInput) {
            dateToInput.required = !isHourRequest;
        }

        if (halfDayToPeriod) {
            halfDayToPeriod.classList.toggle("d-none", requestUnit !== "half_day");
        }

        if (attachmentHint) {
            attachmentHint.classList.toggle("d-none", !supportDocument);
        }
        if (attachmentsInput) {
            attachmentsInput.required = supportDocument;
        }

        if (balance) {
            if (requiresAllocation && remaining) {
                balance.textContent = `${remaining} day(s) available for this type.`;
                balance.classList.remove("d-none");
            } else {
                balance.textContent = "";
                balance.classList.add("d-none");
            }
        }
    }

    function syncEndDateWithStartDate() {
        const select = document.getElementById("holiday_status_id");
        const dateFrom = document.getElementById("request_date_from");
        const dateTo = document.getElementById("request_date_to");
        if (!select || !dateFrom || !dateTo) {
            return;
        }
        const option = select.options[select.selectedIndex];
        const requestUnit = option && option.value ? option.dataset.requestUnit || "day" : "day";
        if (requestUnit === "hour" || !dateFrom.value) {
            return;
        }
        if (!dateTo.value || dateTo.value < dateFrom.value) {
            dateTo.value = dateFrom.value;
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        const select = document.getElementById("holiday_status_id");
        const dateFrom = document.getElementById("request_date_from");
        if (select) {
            select.addEventListener("change", function () {
                toggleLeaveTypeFields();
                syncEndDateWithStartDate();
            });
            toggleLeaveTypeFields();
        }
        if (dateFrom) {
            dateFrom.addEventListener("change", syncEndDateWithStartDate);
        }

        const form = document.getElementById("portal_time_off_form");
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
