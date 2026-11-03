"""models.py - user classes (OOP) and campus booking rules."""
from datetime import datetime, timedelta


# ---------- Users: one base class + three child classes (inheritance) ----------
class User:
    def __init__(self, user_id, username, campus_id=None):
        # Underscore = "private" attributes (encapsulation); use the properties below
        self._user_id = user_id
        self._username = username
        self._campus_id = campus_id
        self.role = "user"
        self.permissions = []

    @property
    def user_id(self):
        return self._user_id

    @property
    def username(self):
        return self._username

    @property
    def campus_id(self):
        return self._campus_id

    def can(self, action):
        return action in self.permissions


class Lecturer(User):
    def __init__(self, user_id, username, campus_id=None):
        super().__init__(user_id, username, campus_id)
        self.role = "lecturer"
        self.permissions = ["book", "view_own", "cancel_own"]


class CampusAdmin(User):
    def __init__(self, user_id, username, campus_id=None):
        super().__init__(user_id, username, campus_id)
        self.role = "admin"
        self.permissions = ["manage_resources", "view_campus_bookings", "campus_report"]


class SystemOperator(User):
    def __init__(self, user_id, username, campus_id=None):
        super().__init__(user_id, username, campus_id)
        self.role = "operator"
        self.permissions = ["view_all", "compare_campuses"]


def create_user(row):
    """Turn a database row (id, username, role, campus_id) into the right class."""
    user_id, username, role, campus_id = row
    if role == "admin":
        return CampusAdmin(user_id, username, campus_id)
    if role == "operator":
        return SystemOperator(user_id, username, campus_id)
    return Lecturer(user_id, username, campus_id)


# ---------- Booking rules (kept separate from the GUI and database) ----------
class BookingRule:
    def __init__(self, max_hours, open_hour, close_hour, max_days_ahead):
        self.max_hours = max_hours
        self.open_hour = open_hour
        self.close_hour = close_hour
        self.max_days_ahead = max_days_ahead

    def describe(self):
        return (f"max {self.max_hours} hour(s) per booking, bookings between "
                f"{self.open_hour:02d}:00 and {self.close_hour:02d}:00, "
                f"up to {self.max_days_ahead} days ahead")

    def check(self, start, duration, days_ahead):
        """Return an error message, or '' if the booking follows the rules."""
        if duration > self.max_hours:
            return f"This campus allows a maximum of {self.max_hours} hour(s) per booking."
        if start < self.open_hour or start + duration > self.close_hour:
            return f"Bookings must be between {self.open_hour:02d}:00 and {self.close_hour:02d}:00."
        if days_ahead > self.max_days_ahead:
            return f"You can only book up to {self.max_days_ahead} days ahead."
        return ""


# To add a new campus rule, just add one more line to this dictionary.
RULES = {
    "Johannesburg": BookingRule(3, 8, 17, 30),
    "Durban": BookingRule(2, 9, 16, 14),
    "Cape Town": BookingRule(4, 7, 18, 60),
}
DEFAULT_RULE = BookingRule(2, 8, 17, 14)


def get_rule(campus_name):
    return RULES.get(campus_name, DEFAULT_RULE)


def validate_booking(campus_name, date_text, start, duration):
    """Check date format, not in the past, and the campus rules. Returns error text or ''."""
    try:
        booking_date = datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return "Date must be in the format YYYY-MM-DD."
    if duration < 1:
        return "Duration must be at least 1 hour."
    if start < 0 or start > 23:
        return "Start hour must be between 0 and 23."
    if booking_date + timedelta(hours=start) <= datetime.now():
        return "You cannot book a time in the past."
    days_ahead = (booking_date.date() - datetime.now().date()).days
    return get_rule(campus_name).check(start, duration, days_ahead)


def booking_state(date_text, start, status):
    """Label a booking as Cancelled, Upcoming or Past."""
    if status == "cancelled":
        return "Cancelled"
    when = datetime.strptime(date_text, "%Y-%m-%d") + timedelta(hours=start)
    return "Upcoming" if when > datetime.now() else "Past"
