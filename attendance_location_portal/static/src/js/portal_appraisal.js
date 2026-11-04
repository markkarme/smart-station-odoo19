(function () {
    "use strict";

    function syncEditorToInput(editor, input) {
        if (!editor || !input) {
            return;
        }
        input.value = editor.innerHTML.trim();
    }

    function fillStars(starGroup, selectedIndex) {
        const icons = starGroup.querySelectorAll("i");
        icons.forEach(function (icon, index) {
            const filled = index <= selectedIndex;
            icon.classList.toggle("fa-star", filled);
            icon.classList.toggle("fa-star-o", !filled);
        });
    }

    function initStars(root) {
        root.addEventListener("click", function (event) {
            const icon = event.target.closest(".o_stars i");
            if (!icon) {
                return;
            }
            const editor = icon.closest("[contenteditable='true']");
            if (!editor || !root.contains(editor)) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            const group = icon.closest(".o_stars");
            const icons = Array.prototype.slice.call(group.querySelectorAll("i"));
            fillStars(group, icons.indexOf(icon));
        });
    }

    const RATING_CHECKED = "☑";
    const RATING_UNCHECKED = "☐";

    function setRatingChecked(el, checked) {
        el.textContent = checked ? RATING_CHECKED : RATING_UNCHECKED;
        el.classList.toggle("ss-rating-checked", checked);
        el.setAttribute(
            "title",
            checked ? "محدد — اضغط لإلغاء التحديد" : "اضغط للاختيار"
        );
    }

    function isRatingChecked(el) {
        return (
            el.classList.contains("ss-rating-checked") ||
            (el.textContent || "").indexOf(RATING_CHECKED) !== -1
        );
    }

    function findRatingCheck(target) {
        if (!(target instanceof Element)) {
            return null;
        }
        return (
            target.closest(".ss-rating-check") ||
            (target.closest("td.ss-rating-cell") &&
                target.closest("td.ss-rating-cell").querySelector(".ss-rating-check"))
        );
    }

    function ensureRatingNonEditable(root) {
        if (!root || !root.querySelectorAll) {
            return;
        }
        Array.prototype.forEach.call(root.querySelectorAll(".ss-rating-check"), function (el) {
            el.classList.add("o-contenteditable-false");
            el.setAttribute("contenteditable", "false");
        });
    }

    function clearSelectionCaret() {
        const sel = window.getSelection && window.getSelection();
        if (sel && sel.rangeCount) {
            sel.removeAllRanges();
        }
    }

    function initRatingChecks(root) {
        ensureRatingNonEditable(root);

        function onRatingDown(event) {
            if (event.type === "mousedown" && typeof window.PointerEvent !== "undefined") {
                return;
            }
            const el = findRatingCheck(event.target);
            if (!el || !root.contains(el)) {
                return;
            }
            // Only toggle inside editable feedback panes (or the whole sheet form)
            const editor = el.closest(
                ".portal-appraisal-feedback-editor, [contenteditable='true'], .ss-appraisal-sheet"
            );
            if (!editor) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }

            const row = el.closest("tr");
            const wasChecked = isRatingChecked(el);
            if (row) {
                Array.prototype.forEach.call(row.querySelectorAll(".ss-rating-check"), function (box) {
                    setRatingChecked(box, false);
                });
            }
            if (!wasChecked) {
                setRatingChecked(el, true);
            }
            clearSelectionCaret();

            // Keep hidden inputs in sync for next save without waiting for submit
            syncEditorToInput(
                document.getElementById("portal_appraisal_employee_editor"),
                document.getElementById("employee_feedback_input")
            );
            syncEditorToInput(
                document.getElementById("portal_appraisal_manager_editor"),
                document.getElementById("manager_feedback_input")
            );
        }

        function blockEditorCaret(event) {
            const el = findRatingCheck(event.target);
            if (!el || !root.contains(el)) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }
        }

        root.addEventListener("pointerdown", onRatingDown, true);
        root.addEventListener("mousedown", onRatingDown, true);
        root.addEventListener("click", blockEditorCaret, true);
        root.addEventListener("mouseup", blockEditorCaret, true);
    }

    function parseEmployeesJson() {
        const node = document.getElementById("portal_appraisal_employees_json");
        if (!node) {
            return [];
        }
        try {
            return JSON.parse(node.textContent || "[]");
        } catch (error) {
            return [];
        }
    }

    function selectedAppraiserIds(container) {
        return Array.prototype.map.call(
            container.querySelectorAll('input[name="manager_ids"]'),
            function (input) {
                return String(input.value);
            }
        );
    }

    function refreshAppraiserOptions(employeeId) {
        const addSelect = document.getElementById("portal_appraiser_add");
        const chips = document.getElementById("portal_appraiser_chips");
        if (!addSelect || !chips) {
            return;
        }
        const selected = selectedAppraiserIds(chips);
        Array.prototype.forEach.call(addSelect.options, function (option) {
            if (!option.value) {
                return;
            }
            option.disabled = option.value === String(employeeId) || selected.indexOf(option.value) !== -1;
        });
        addSelect.value = "";
    }

    function addAppraiserChip(id, name) {
        const chips = document.getElementById("portal_appraiser_chips");
        if (!chips || !id) {
            return;
        }
        if (selectedAppraiserIds(chips).indexOf(String(id)) !== -1) {
            return;
        }
        const chip = document.createElement("span");
        chip.className = "portal-appraisal-chip";
        chip.setAttribute("data-id", id);
        chip.innerHTML =
            '<span></span>' +
            '<button type="button" class="btn-close portal-appraiser-remove" aria-label="Remove"></button>' +
            '<input type="hidden" name="manager_ids" value=""/>';
        chip.querySelector("span").textContent = name;
        chip.querySelector("input").value = id;
        chips.appendChild(chip);
    }

    function setAppraisers(appraisers, employeeId) {
        const chips = document.getElementById("portal_appraiser_chips");
        if (!chips) {
            return;
        }
        chips.innerHTML = "";
        (appraisers || []).forEach(function (appraiser) {
            if (String(appraiser.id) !== String(employeeId)) {
                addAppraiserChip(appraiser.id, appraiser.name);
            }
        });
        refreshAppraiserOptions(employeeId);
    }

    function applyTemplateOptions(templates, selectedId) {
        const select = document.getElementById("appraisal_template_id");
        if (!select || !templates) {
            return;
        }
        select.innerHTML = "";
        templates.forEach(function (template) {
            const option = document.createElement("option");
            option.value = template.id;
            option.textContent = template.name;
            if (String(template.id) === String(selectedId)) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }

    function applyFeedback(data) {
        const employeeEditor = document.getElementById("portal_appraisal_employee_editor");
        const managerEditor = document.getElementById("portal_appraisal_manager_editor");
        const managerPreview = document.getElementById("portal_appraisal_manager_preview");
        if (employeeEditor && data.employee_feedback) {
            employeeEditor.innerHTML = data.employee_feedback;
            ensureRatingNonEditable(employeeEditor);
        }
        if (managerEditor && data.manager_feedback) {
            managerEditor.innerHTML = data.manager_feedback;
            ensureRatingNonEditable(managerEditor);
        } else if (managerPreview && data.manager_feedback) {
            managerPreview.innerHTML = data.manager_feedback;
            ensureRatingNonEditable(managerPreview);
        }
    }

    function initTemplateSwitch(employeeSelect) {
        const select = document.getElementById("appraisal_template_id");
        if (!select) {
            return;
        }
        select.addEventListener("change", function () {
            const templateId = select.value;
            if (!templateId) {
                return;
            }
            let url = "/my/appraisals/template/" + templateId;
            if (employeeSelect && employeeSelect.value) {
                url += "?employee_id=" + encodeURIComponent(employeeSelect.value);
            }
            fetch(url, {credentials: "same-origin"})
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error("Template request failed");
                    }
                    return response.json();
                })
                .then(applyFeedback)
                .catch(function () {
                    // Keep the current template content if the request fails.
                });
        });
    }

    function initEmployeeAndAppraisers() {
        const employeeSelect = document.getElementById("employee_id");
        const addSelect = document.getElementById("portal_appraiser_add");
        const chips = document.getElementById("portal_appraiser_chips");

        if (chips) {
            chips.addEventListener("click", function (event) {
                const remove = event.target.closest(".portal-appraiser-remove");
                if (!remove) {
                    return;
                }
                const chip = remove.closest(".portal-appraisal-chip");
                if (chip) {
                    chip.remove();
                }
                refreshAppraiserOptions(employeeSelect ? employeeSelect.value : "");
            });
        }

        if (addSelect) {
            addSelect.addEventListener("change", function () {
                const option = addSelect.options[addSelect.selectedIndex];
                if (!option || !option.value) {
                    return;
                }
                addAppraiserChip(option.value, option.getAttribute("data-name") || option.textContent.trim());
                refreshAppraiserOptions(employeeSelect ? employeeSelect.value : "");
            });
        }

        if (employeeSelect) {
            employeeSelect.addEventListener("change", function () {
                const employeeId = employeeSelect.value;
                if (!employeeId) {
                    return;
                }
                fetch("/my/appraisals/employee/" + employeeId + "/defaults", {credentials: "same-origin"})
                    .then(function (response) {
                        if (!response.ok) {
                            throw new Error("Employee defaults request failed");
                        }
                        return response.json();
                    })
                    .then(function (data) {
                        setAppraisers(data.manager_ids || [], data.id);
                        applyTemplateOptions(data.templates || [], data.default_template_id);
                        applyFeedback(data);
                    })
                    .catch(function () {
                        refreshAppraiserOptions(employeeId);
                    });
            });
            refreshAppraiserOptions(employeeSelect.value);
        } else if (addSelect) {
            refreshAppraiserOptions("");
        }

        return employeeSelect;
    }

    function initPortalAppraisalForm() {
        const form = document.getElementById("portal_appraisal_form");
        if (!form) {
            return;
        }

        initStars(form);
        initRatingChecks(form);
        const employeeSelect = initEmployeeAndAppraisers();
        initTemplateSwitch(employeeSelect);
        parseEmployeesJson();

        form.addEventListener("submit", function (event) {
            syncEditorToInput(
                document.getElementById("portal_appraisal_employee_editor"),
                document.getElementById("employee_feedback_input")
            );
            syncEditorToInput(
                document.getElementById("portal_appraisal_manager_editor"),
                document.getElementById("manager_feedback_input")
            );
            syncEditorToInput(
                document.getElementById("portal_appraisal_note_editor"),
                document.getElementById("private_note_input")
            );
            const chips = document.getElementById("portal_appraiser_chips");
            if (chips && !chips.querySelector('input[name="manager_ids"]')) {
                event.preventDefault();
                window.alert("Please select at least one appraiser.");
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initPortalAppraisalForm);
    } else {
        initPortalAppraisalForm();
    }
})();
