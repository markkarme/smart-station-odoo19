/** @odoo-module **/

(function () {
    "use strict";

    function setupPortalAttendance() {
        var form = document.getElementById("portal_attendance_form");
        if (!form) {
            return;
        }

        var feedback = document.getElementById("geo_feedback");
        var outOfRangeBlock = document.getElementById("geo_out_of_range_block");
        var locationsList = document.getElementById("geo_allowed_locations");
        var latitudeInput = document.getElementById("attendance_latitude");
        var longitudeInput = document.getElementById("attendance_longitude");
        var submitBtn = document.getElementById("submit_attendance_btn");
        var refreshBtn = document.getElementById("refresh_geo_btn");
        var actionInputs = form.querySelectorAll('input[name="attendance_action"]');
        var locationAllowed = false;
        var buttonTextByAction = {
            check_in: "تسجيل الحضور",
            check_out: "تسجيل انصراف",
        };
        var defaultButtonText = "تسجيل";

        var hasSelectedAction = function () {
            return !!form.querySelector('input[name="attendance_action"]:checked');
        };

        var getSelectedAction = function () {
            var selectedInput = form.querySelector('input[name="attendance_action"]:checked');
            return selectedInput ? selectedInput.value : null;
        };

        var updateSubmitText = function () {
            var selectedAction = getSelectedAction();
            submitBtn.textContent = buttonTextByAction[selectedAction] || defaultButtonText;
        };

        var updateSubmitState = function () {
            submitBtn.disabled = !(locationAllowed && hasSelectedAction());
        };

        var setFeedback = function (message, type) {
            feedback.textContent = message;
            feedback.className = "alert mb-3";
            feedback.classList.add(type || "alert-secondary");
        };

        var hideLocationsList = function () {
            if (outOfRangeBlock) {
                outOfRangeBlock.classList.add("d-none");
            }
            if (locationsList) {
                locationsList.innerHTML = "";
            }
        };

        var showLocationsList = function (locationNames) {
            if (!outOfRangeBlock || !locationsList || !locationNames || !locationNames.length) {
                return;
            }
            locationsList.innerHTML = "";
            locationNames.forEach(function (name) {
                var item = document.createElement("li");
                item.className = "list-group-item";
                item.textContent = name;
                locationsList.appendChild(item);
            });
            outOfRangeBlock.classList.remove("d-none");
        };

        var checkLocationRange = function (latitude, longitude) {
            var url = (form.getAttribute("data-check-url") || "/my/attendance/check_location")
                + "?latitude=" + encodeURIComponent(latitude)
                + "&longitude=" + encodeURIComponent(longitude);

            return fetch(url, { credentials: "same-origin" })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error("Location check failed");
                    }
                    return response.json();
                })
                .then(function (data) {
                    latitudeInput.value = latitude;
                    longitudeInput.value = longitude;

                    if (data.allowed) {
                        locationAllowed = true;
                        hideLocationsList();
                        setFeedback(data.message, "alert-success");
                        updateSubmitState();
                        return;
                    }

                    locationAllowed = false;
                    var message = data.message || "You are out of location range.";
                    if (data.nearest_location && data.nearest_distance_m !== false) {
                        message += " أقرب موقع مسموح: "
                            + data.nearest_location
                            + " ("
                            + data.nearest_distance_m
                            + " م).";
                    }
                    setFeedback(message, "alert-danger");
                    showLocationsList(data.location_names || []);
                    updateSubmitState();
                })
                .catch(function () {
                    locationAllowed = false;
                    hideLocationsList();
                    setFeedback(
                        "Could not verify your location range. Please try again.",
                        "alert-danger"
                    );
                    updateSubmitState();
                });
        };

        var detectLocation = function () {
            locationAllowed = false;
            updateSubmitState();
            hideLocationsList();
            setFeedback("Detecting your location...", "alert-secondary");
            if (!navigator.geolocation) {
                setFeedback("Geolocation is not supported by your browser.", "alert-danger");
                return;
            }

            navigator.geolocation.getCurrentPosition(
                function (position) {
                    setFeedback("Checking if you are within allowed location range...", "alert-secondary");
                    checkLocationRange(
                        position.coords.latitude,
                        position.coords.longitude
                    );
                },
                function (error) {
                    var message = "Could not get your location. Please allow GPS access.";
                    if (error && error.message) {
                        message = error.message;
                    }
                    setFeedback(message, "alert-danger");
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0,
                }
            );
        };

        refreshBtn.addEventListener("click", detectLocation);
        actionInputs.forEach(function (input) {
            input.addEventListener("change", function () {
                updateSubmitText();
                updateSubmitState();
            });
        });
        updateSubmitText();
        updateSubmitState();
        detectLocation();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupPortalAttendance);
    } else {
        setupPortalAttendance();
    }
})();
