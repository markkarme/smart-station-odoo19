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
            // Do not infer lang from the first path segment: "/my/..." would become
            // "/my/my/attendance/check_location". website=True + frontend_lang handle i18n.
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
                        submitBtn.disabled = false;
                        hideLocationsList();
                        setFeedback(data.message, "alert-success");
                        return;
                    }

                    submitBtn.disabled = true;
                    var message = data.message || "You are out of location range.";
                    if (data.nearest_location && data.nearest_distance_m !== false) {
                        message += " Nearest location: "
                            + data.nearest_location
                            + " ("
                            + data.nearest_distance_m
                            + " m away).";
                    }
                    setFeedback(message, "alert-danger");
                    showLocationsList(data.location_names || []);
                })
                .catch(function () {
                    submitBtn.disabled = true;
                    hideLocationsList();
                    setFeedback(
                        "Could not verify your location range. Please try again.",
                        "alert-danger"
                    );
                });
        };

        var detectLocation = function () {
            submitBtn.disabled = true;
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
        detectLocation();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupPortalAttendance);
    } else {
        setupPortalAttendance();
    }
})();
