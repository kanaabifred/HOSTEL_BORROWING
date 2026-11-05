""""
Encapsulation: private User and Item attributes.
Inheritance: Student and Administrator extend User.
Abstraction/polymorphism: FinePolicy with hourly/daily implementations.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

TIME_FORMAT = "%d %b %Y, %I:%M %p"

def uid(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def readable(value: datetime | None) -> str:
    return value.strftime(TIME_FORMAT) if value else "—"


def cash(value: int) -> str:
    return f"UGX {value:,}"


class BorrowError(Exception):
    """Friendly business-rule error to display in the terminal."""


# ----------------------------- DOMAIN OBJECTS -----------------------------
class User(ABC):
    """ABSTRACTION: common interface for each type of user."""

    def __init__(self, user_id: str, name: str):
        if not name.strip():
            raise BorrowError("A user must have a name.")
        self.__id = user_id
        self.__name = name.strip()

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        return self.__name

    @property
    @abstractmethod
    def role(self) -> str:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass


class Student(User):  # INHERITANCE
    def __init__(self, user_id: str, name: str, hostel_id: str):
        super().__init__(user_id, name)
        self.__hostel_id = hostel_id

    @property
    def hostel_id(self):
        return self.__hostel_id

    @property
    def role(self):
        return "STUDENT"

    def to_dict(self):
        return {"role": self.role, "id": self.id, "name": self.name,
                "hostel_id": self.hostel_id}


class Administrator(User):  # INHERITANCE
    @property
    def role(self):
        return "ADMIN"

    def to_dict(self):
        return {"role": self.role, "id": self.id, "name": self.name}


@dataclass
class Hostel:
    id: str
    name: str
    area: str


class FinePolicy(ABC):  # ABSTRACTION
    @abstractmethod
    def calculate(self, overdue_seconds: float, rate: int) -> int:
        """Calculate integer UGX after grace, rounding up part-units."""
        pass


class HourlyFinePolicy(FinePolicy):  # INHERITANCE + POLYMORPHISM
    def calculate(self, overdue_seconds: float, rate: int) -> int:
        return math.ceil(overdue_seconds / 3600) * rate if overdue_seconds > 0 else 0


class DailyFinePolicy(FinePolicy):  # INHERITANCE + POLYMORPHISM
    def calculate(self, overdue_seconds: float, rate: int) -> int:
        return math.ceil(overdue_seconds / 86400) * rate if overdue_seconds > 0 else 0


FINE_POLICIES: dict[str, FinePolicy] = {
    "HOURLY": HourlyFinePolicy(),
    "DAILY": DailyFinePolicy(),
}


class Item:
    """ENCAPSULATION: item data is private and state changes use methods."""

    def __init__(self, item_id: str, owner_id: str, name: str, category: str,
                 condition: str, max_hours: int, grace_hours: int,
                 policy: str, fine_rate: int, fine_cap: int, listed: bool = True):
        if not name.strip() or not category.strip():
            raise BorrowError("Item name and category are required.")
        if max_hours < 1 or grace_hours < 0 or fine_rate < 0 or fine_cap < 0:
            raise BorrowError("Borrowing hours must be positive; fines/grace cannot be negative.")
        if policy not in FINE_POLICIES:
            raise BorrowError("Unknown fine policy.")
        self.__id = item_id
        self.__owner_id = owner_id
        self.__name = name.strip()
        self.__category = category.strip()
        self.__condition = condition.strip() or "Good"
        self.__max_hours = int(max_hours)
        self.__grace_hours = int(grace_hours)
        self.__policy = policy
        self.__fine_rate = int(fine_rate)
        self.__fine_cap = int(fine_cap)
        self.__listed = bool(listed)

    @property
    def id(self): return self.__id
    @property
    def owner_id(self): return self.__owner_id
    @property
    def name(self): return self.__name
    @property
    def category(self): return self.__category
    @property
    def condition(self): return self.__condition
    @property
    def max_hours(self): return self.__max_hours
    @property
    def grace_hours(self): return self.__grace_hours
    @property
    def policy(self): return self.__policy
    @property
    def fine_rate(self): return self.__fine_rate
    @property
    def fine_cap(self): return self.__fine_cap
    @property
    def listed(self): return self.__listed

    def set_listed(self, listed: bool):
        self.__listed = bool(listed)

    def update_condition(self, condition: str):
        if condition.strip():
            self.__condition = condition.strip()

    def to_dict(self):
        return {"id": self.id, "owner_id": self.owner_id, "name": self.name,
                "category": self.category, "condition": self.condition,
                "max_hours": self.max_hours, "grace_hours": self.grace_hours,
                "policy": self.policy, "fine_rate": self.fine_rate,
                "fine_cap": self.fine_cap, "listed": self.listed}


@dataclass
class BorrowRequest:
    id: str
    item_id: str
    borrower_id: str
    hours: int
    created_at: str
    status: str = "PENDING"
    reason: str = ""

    def approve(self):
        if self.status != "PENDING":
            raise BorrowError("Only pending requests can be approved.")
        self.status = "APPROVED"

    def reject(self):
        if self.status not in ("PENDING", "APPROVED"):
            raise BorrowError("This request can no longer be rejected.")
        self.status = "REJECTED"

    def flag_conflict(self, reason: str):
        if self.status == "PENDING":
            self.status, self.reason = "CONFLICT", reason


@dataclass
class BorrowTransaction:
    id: str
    request_id: str
    item_id: str
    borrower_id: str
    lender_id: str
    handed_over_at: str
    due_at: str
    grace_hours: int
    fine_policy: str
    fine_rate: int
    fine_cap: int
    status: str = "ACTIVE"
    return_requested_at: str = ""
    returned_at: str = ""
    fine_paid: int = 0
    extension_hours_requested: int = 0
    extensions_granted: int = 0
    returned_condition: str = ""

    @property
    def due(self) -> datetime:
        return datetime.fromisoformat(self.due_at)

    @property
    def grace_deadline(self) -> datetime:
        return self.due + timedelta(hours=self.grace_hours)

    def display_status(self, now: datetime | None = None) -> str:
        if self.status == "RETURNED":
            return "RETURNED"
        if self.status == "DISPUTED":
            return "DISPUTED"
        if self.status == "RETURN_PENDING":
            return "RETURN PENDING"
        now = now or datetime.now()
        if now > self.grace_deadline:
            return "OVERDUE"
        if now > self.due:
            return "GRACE PERIOD"
        if self.due - now <= timedelta(hours=1):
            return "DUE SOON"
        return "TAKEN"

    def fine_total(self, now: datetime | None = None) -> int:
        """POLYMORPHISM: hourly/daily policies share calculate()."""
        # Stop fine growth when the borrower initiates a return; lender confirms it.
        stop_time = self.returned_at or self.return_requested_at
        end = datetime.fromisoformat(stop_time) if stop_time else (now or datetime.now())
        late_seconds = (end - self.grace_deadline).total_seconds()
        amount = FINE_POLICIES[self.fine_policy].calculate(late_seconds, self.fine_rate)
        return min(amount, self.fine_cap)

    def outstanding(self) -> int:
        return max(0, self.fine_total() - self.fine_paid)

    def request_return(self):
        if self.status != "ACTIVE":
            raise BorrowError("This item is already awaiting return or is closed.")
        self.status = "RETURN_PENDING"
        self.return_requested_at = datetime.now().isoformat()

    def confirm_return(self, condition: str):
        if self.status != "RETURN_PENDING":
            raise BorrowError("The borrower must request a return first.")
        # The owner verifies the physical handover. Use the borrower's
        # reported handover time so slow confirmation does not inflate a fine.
        self.returned_at = self.return_requested_at or datetime.now().isoformat()
        self.returned_condition = condition or "Good"
        self.status = "RETURNED"


@dataclass
class Dispute:
    id: str
    loan_id: str
    reporter_id: str
    reason: str
    status: str = "OPEN"


@dataclass
class Notification:
    id: str
    user_id: str
    message: str
    created_at: str


