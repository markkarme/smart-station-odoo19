import { ActivityMenu } from "@mail/core/web/activity_menu";
import { patch } from "@web/core/utils/patch";

const ACTIVITY_MODEL_ACTIONS = {
    "hr.attendance": "attendance_location_portal.action_hr_attendance_my_activities",
    "hr.attendance.adjustment.request":
        "attendance_location_portal.action_hr_attendance_adjustment_my_activities",
    "hr.general.request": "attendance_location_portal.action_hr_general_request_my_activities",
};

const APPROVAL_MODELS = new Set([
    "hr.attendance.adjustment.request",
    "hr.general.request",
]);

patch(ActivityMenu.prototype, {
    availableViews(group) {
        if (ACTIVITY_MODEL_ACTIONS[group.model]) {
            return [
                [false, "list"],
                [false, "form"],
                [false, "activity"],
            ];
        }
        return super.availableViews(...arguments);
    },

    openActivityGroup(group, filter = "all", newWindow) {
        const actionXmlId = ACTIVITY_MODEL_ACTIONS[group.model];
        if (!actionXmlId) {
            return super.openActivityGroup(...arguments);
        }

        this.dropdown.close();
        const context = {
            force_search_count: 1,
            search_default_filter_activities_my: 1,
        };
        if (APPROVAL_MODELS.has(group.model)) {
            context.search_default_filter_confirm = 1;
        }
        if (filter === "all") {
            context.search_default_activities_overdue = 1;
            context.search_default_activities_today = 1;
        } else if (filter === "overdue") {
            context.search_default_activities_overdue = 1;
        } else if (filter === "today") {
            context.search_default_activities_today = 1;
        } else if (filter === "upcoming_all") {
            context.search_default_activities_upcoming_all = 1;
        }

        this.action.loadAction(actionXmlId).then((action) => {
            this.action.doAction(action, {
                newWindow,
                additionalContext: context,
                clearBreadcrumbs: true,
            });
        });
    },
});
