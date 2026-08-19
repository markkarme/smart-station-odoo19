import math
import re
from urllib.request import Request, urlopen

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AttendanceLocation(models.Model):
    _name = "attendance.location"
    _description = "Attendance Location"
    _order = "name"

    name = fields.Char(required=True)
    google_maps_url = fields.Char(string="Google Maps URL")
    latitude = fields.Float(digits=(10, 7), required=True)
    longitude = fields.Float(digits=(10, 7), required=True)
    allowed_range_m = fields.Float(
        string="Allowed Range (m)",
        default=1000.0,
        required=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    employee_ids = fields.Many2many(
        "hr.employee",
        "attendance_location_employee_rel",
        "location_id",
        "employee_id",
        string="Allowed Employees",
        help="If empty, this location is valid for all employees.",
    )

    _sql_constraints = [
        (
            "attendance_location_range_positive",
            "CHECK(allowed_range_m > 0)",
            "Allowed attendance range must be greater than 0 m.",
        ),
    ]

    @api.constrains("latitude", "longitude")
    def _check_coordinates(self):
        for rec in self:
            if rec.latitude < -90 or rec.latitude > 90:
                raise ValidationError(_("Latitude must be between -90 and 90."))
            if rec.longitude < -180 or rec.longitude > 180:
                raise ValidationError(_("Longitude must be between -180 and 180."))

    @api.onchange("google_maps_url")
    def _onchange_google_maps_url(self):
        for rec in self:
            if rec.google_maps_url:
                lat_lon = rec._extract_lat_lon_from_url(rec.google_maps_url)
                if not lat_lon:
                    lat_lon = rec._extract_lat_lon_from_url(rec._expand_google_maps_url(rec.google_maps_url))
                if lat_lon:
                    rec.latitude, rec.longitude = lat_lon

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._fill_coordinates_from_google_url(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = self._fill_coordinates_from_google_url(vals)
        return super().write(vals)

    @api.model
    def _fill_coordinates_from_google_url(self, vals):
        url = vals.get("google_maps_url")
        if not url:
            return vals
        lat_lon = self._extract_lat_lon_from_url(url)
        if not lat_lon:
            expanded_url = self._expand_google_maps_url(url)
            lat_lon = self._extract_lat_lon_from_url(expanded_url)
        if lat_lon:
            vals["latitude"], vals["longitude"] = lat_lon
        return vals

    @api.model
    def _expand_google_maps_url(self, url):
        if not url:
            return url
        try:
            request = Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urlopen(request, timeout=8) as response:
                return response.geturl() or url
        except Exception:
            return url

    @api.model
    def _extract_lat_lon_from_url(self, url):
        patterns = [
            r"@(-?\d+\.\d+),(-?\d+\.\d+)",
            r"[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)",
            r"[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)",
            r"/search/(-?\d+\.\d+),(-?\d+\.\d+)",
            r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return float(match.group(1)), float(match.group(2))
        return False

    @api.model
    def _haversine_distance_m(self, lat1, lon1, lat2, lon2):
        # Great-circle distance on Earth's surface, in meters.
        radius_m = 6371000.0
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius_m * c

    @api.model
    def _candidate_domain(self, employee):
        domain = [
            ("active", "=", True),
            ("company_id", "=", employee.company_id.id),
        ]
        if employee.attendance_location_ids:
            domain.append(("id", "in", employee.attendance_location_ids.ids))
        else:
            domain.extend(
                [
                    "|",
                    ("employee_ids", "=", False),
                    ("employee_ids", "in", employee.id),
                ]
            )
        return domain

    @api.model
    def find_allowed_location(self, employee, latitude, longitude):
        candidates = self.search(self._candidate_domain(employee))
        allowed = self.browse()
        nearest = self.browse()
        nearest_distance = None
        for location in candidates:
            distance = self._haversine_distance_m(
                latitude,
                longitude,
                location.latitude,
                location.longitude,
            )
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest = location
            if distance <= location.allowed_range_m:
                allowed = location
                break
        return allowed, nearest, nearest_distance

    @api.model
    def check_location_for_employee(self, employee, latitude, longitude):
        candidates = self.search(self._candidate_domain(employee))
        location_names = candidates.mapped("name")
        if not candidates:
            return {
                "allowed": False,
                "message": _("No attendance location is configured for you."),
                "location_names": [],
            }

        allowed, nearest, nearest_distance = self.find_allowed_location(
            employee, latitude, longitude
        )
        if allowed:
            distance = self._haversine_distance_m(
                latitude,
                longitude,
                allowed.latitude,
                allowed.longitude,
            )
            return {
                "allowed": True,
                "message": _(
                    "You are within range of %(location)s. You can submit attendance now."
                )
                % {"location": allowed.name},
                "location_name": allowed.name,
                "distance_m": round(distance, 2),
                "location_names": location_names,
            }

        return {
            "allowed": False,
            "message": _("You are out of location range."),
            "location_names": location_names,
            "nearest_location": nearest.name if nearest else False,
            "nearest_distance_m": round(nearest_distance, 2) if nearest_distance else False,
        }
