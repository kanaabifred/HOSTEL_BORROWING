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


"""Handles item listings, requests, conflicts, deadlines, returns,
extensions, fines, disputes, notifications and demo data.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from models import (
    Administrator, BorrowError, BorrowRequest, BorrowTransaction, Dispute,
    Hostel, Item, Notification, Student, User, cash, readable, uid,
)

DATA_FILE = Path(__file__).with_name("borrowplug_data.json")

class BorrowingSystem:
    """COMPOSITION: manages users, hostels, items, requests and loans."""

    def __init__(self):
        self.hostels: dict[str, Hostel] = {}
        self.users: dict[str, User] = {}
        self.items: dict[str, Item] = {}
        self.requests: dict[str, BorrowRequest] = {}
        self.loans: dict[str, BorrowTransaction] = {}
        self.disputes: dict[str, Dispute] = {}
        self.notifications: list[Notification] = []

    @classmethod
    def load(cls):
        if not DATA_FILE.exists():
            app = cls()
            app.seed_demo()
            app.save()
            return app
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            app = cls()
            app.hostels = {d["id"]: Hostel(**d) for d in data.get("hostels", [])}
            for d in data.get("users", []):
                obj = Student(d["id"], d["name"], d["hostel_id"]) if d["role"] == "STUDENT" \
                    else Administrator(d["id"], d["name"])
                app.users[obj.id] = obj
            app.items = {d["id"]: Item(**{"item_id": d["id"],
                     **{key: value for key, value in d.items() if key != "id"}})
                         for d in data.get("items", [])}
            app.requests = {d["id"]: BorrowRequest(**d) for d in data.get("requests", [])}
            app.loans = {d["id"]: BorrowTransaction(**d) for d in data.get("loans", [])}
            app.disputes = {d["id"]: Dispute(**d) for d in data.get("disputes", [])}
            app.notifications = [Notification(**d) for d in data.get("notifications", [])]
            return app
        except (ValueError, TypeError, KeyError, OSError) as err:
            raise BorrowError(f"Cannot load {DATA_FILE.name}: {err}") from err

    def save(self):
        data = {
            "hostels": [asdict(o) for o in self.hostels.values()],
            "users": [o.to_dict() for o in self.users.values()],
            "items": [o.to_dict() for o in self.items.values()],
            "requests": [asdict(o) for o in self.requests.values()],
            "loans": [asdict(o) for o in self.loans.values()],
            "disputes": [asdict(o) for o in self.disputes.values()],
            "notifications": [asdict(o) for o in self.notifications[-150:]],
        }
        temp = DATA_FILE.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp.replace(DATA_FILE)

    def student(self, user_id):
        obj = self.users[user_id]
        if not isinstance(obj, Student):
            raise BorrowError("Select a student account to use this action.")
        return obj

    def is_admin(self, user_id) -> bool:
        return isinstance(self.users[user_id], Administrator)

    def same_hostel(self, user_id: str, item: Item) -> bool:
        return self.student(user_id).hostel_id == self.student(item.owner_id).hostel_id

    def notify(self, user_id: str, message: str):
        self.notifications.append(Notification(uid("N"), user_id, message, datetime.now().isoformat()))

    def active_loan(self, item_id: str) -> BorrowTransaction | None:
        return next((loan for loan in self.loans.values()
                     if loan.item_id == item_id and loan.status != "RETURNED"), None)

    def reserved_request(self, item_id: str) -> BorrowRequest | None:
        return next((req for req in self.requests.values()
                     if req.item_id == item_id and req.status == "APPROVED"), None)

    def item_state(self, item: Item) -> str:
        if self.active_loan(item.id):
            return "TAKEN"
        if self.reserved_request(item.id):
            return "RESERVED"
        return "AVAILABLE" if item.listed else "PAUSED"

    def item_due(self, item: Item) -> str:
        loan = self.active_loan(item.id)
        return readable(loan.due) if loan else "—"

    def add_item(self, owner_id, name, category, condition, max_hours,
                 grace_hours, policy, fine_rate, fine_cap):
        self.student(owner_id)
        item = Item(uid("I"), owner_id, name, category, condition, max_hours,
                    grace_hours, policy, fine_rate, fine_cap)
        self.items[item.id] = item
        self.save()
        return item

    def set_item_visibility(self, item_id, actor_id):
        item = self.items[item_id]
        if actor_id != item.owner_id:
            raise BorrowError("Only the owner can pause or resume this listing.")
        if self.active_loan(item_id) or self.reserved_request(item_id):
            raise BorrowError("Cannot pause an item that is reserved or taken.")
        item.set_listed(not item.listed)
        self.save()

    def request_item(self, borrower_id, item_id, hours):
        self.student(borrower_id)
        item = self.items[item_id]
        if borrower_id == item.owner_id:
            raise BorrowError("You cannot borrow your own item.")
        if not self.same_hostel(borrower_id, item):
            raise BorrowError("Borrowing is currently restricted to your hostel.")
        if hours < 1 or hours > item.max_hours:
            raise BorrowError(f"Borrowing duration must be 1–{item.max_hours} hours.")
        if not item.listed and self.item_state(item) == "PAUSED":
            raise BorrowError("This listing has been paused by its owner.")
        if any(r.borrower_id == borrower_id and r.item_id == item_id
               and r.status in ("PENDING", "APPROVED") for r in self.requests.values()):
            raise BorrowError("You already have an open request for this item.")
        state = self.item_state(item)
        req = BorrowRequest(uid("R"), item_id, borrower_id, hours, datetime.now().isoformat())
        if state != "AVAILABLE":
            req.flag_conflict(f"Item is already {state.lower()}; try another item or ask later.")
        self.requests[req.id] = req
        self.notify(item.owner_id, f"{self.users[borrower_id].name} requested {item.name} ({req.status}).")
        self.save()
        return req

    def approve_request(self, request_id, owner_id):
        req = self.requests[request_id]
        item = self.items[req.item_id]
        if item.owner_id != owner_id:
            raise BorrowError("Only the item owner can approve this request.")
        if self.item_state(item) != "AVAILABLE":
            raise BorrowError("Cannot approve: the item is already taken or reserved.")
        req.approve()
        for other in self.requests.values():
            if other.id != req.id and other.item_id == item.id:
                other.flag_conflict(f"Another borrower was approved ({req.id}).")
        self.notify(req.borrower_id, f"Approved: {item.name}. Confirm collection to start your loan.")
        self.save()

    def reject_request(self, request_id, owner_id):
        req = self.requests[request_id]
        item = self.items[req.item_id]
        if owner_id != item.owner_id:
            raise BorrowError("Only the owner can reject a request.")
        req.reject()
        self.notify(req.borrower_id, f"Your request for {item.name} was declined.")
        self.save()

    def collect_item(self, request_id, borrower_id):
        req = self.requests[request_id]
        item = self.items[req.item_id]
        if borrower_id != req.borrower_id:
            raise BorrowError("Only the approved borrower can confirm collection.")
        if req.status != "APPROVED" or self.active_loan(item.id):
            raise BorrowError("This request is not ready for item collection.")
        started = datetime.now()
        loan = BorrowTransaction(
            uid("L"), req.id, item.id, borrower_id, item.owner_id,
            started.isoformat(), (started + timedelta(hours=req.hours)).isoformat(),
            item.grace_hours, item.policy, item.fine_rate, item.fine_cap)
        self.loans[loan.id] = loan
        req.status = "FULFILLED"
        self.notify(item.owner_id, f"{self.users[borrower_id].name} collected {item.name}; due {readable(loan.due)}.")
        self.save()
        return loan

    def request_return(self, loan_id, borrower_id):
        loan = self.loans[loan_id]
        if loan.borrower_id != borrower_id:
            raise BorrowError("Only the borrower can request a return.")
        loan.request_return()
        item = self.items[loan.item_id]
        self.notify(loan.lender_id, f"Confirm the physical return of {item.name} from {self.users[borrower_id].name}.")
        self.save()

    def confirm_return(self, loan_id, owner_id, condition):
        loan = self.loans[loan_id]
        if loan.lender_id != owner_id:
            raise BorrowError("Only the lender can confirm receiving this item.")
        loan.confirm_return(condition)
        self.items[loan.item_id].update_condition(condition)
        self.notify(loan.borrower_id, f"Return confirmed. Fine: {cash(loan.fine_total())}.")
        self.save()

    def request_extension(self, loan_id, borrower_id, extra_hours):
        loan = self.loans[loan_id]
        if loan.borrower_id != borrower_id or loan.status != "ACTIVE":
            raise BorrowError("Only the active borrower can request an extension.")
        if loan.extension_hours_requested:
            raise BorrowError("An extension request is already pending.")
        if datetime.now() > loan.due:
            raise BorrowError("Extensions must be requested before the return deadline.")
        if extra_hours < 1 or extra_hours > 24:
            raise BorrowError("Extension must be between 1 and 24 hours.")
        loan.extension_hours_requested = extra_hours
        self.notify(loan.lender_id, f"Extension requested: +{extra_hours}h for {self.items[loan.item_id].name}.")
        self.save()

    def decide_extension(self, loan_id, lender_id, approve):
        loan = self.loans[loan_id]
        if loan.lender_id != lender_id or not loan.extension_hours_requested or loan.status != "ACTIVE":
            raise BorrowError("No extension request to review for this lender.")
        hrs = loan.extension_hours_requested
        if approve:
            loan.due_at = (loan.due + timedelta(hours=hrs)).isoformat()
            loan.extensions_granted += 1
        loan.extension_hours_requested = 0
        self.notify(loan.borrower_id, f"Extension {'approved' if approve else 'declined'} for {self.items[loan.item_id].name}.")
        self.save()

    def pay_fine(self, loan_id, actor_id):
        loan = self.loans[loan_id]
        if loan.borrower_id != actor_id:
            raise BorrowError("Only the borrower can settle this fine.")
        if loan.status != "RETURNED":
            raise BorrowError("Fines are finalised after the lender confirms the return.")
        owed = loan.outstanding()
        if owed <= 0:
            raise BorrowError("There is no outstanding fine.")
        loan.fine_paid += owed
        self.notify(loan.lender_id, f"Fine of {cash(owed)} recorded as paid for {self.items[loan.item_id].name}.")
        self.save()
        return owed

    def open_dispute(self, loan_id, reporter_id, reason):
        loan = self.loans[loan_id]
        if reporter_id not in (loan.borrower_id, loan.lender_id):
            raise BorrowError("Only the borrower or lender can report this loan.")
        if not reason.strip():
            raise BorrowError("Explain what went wrong.")
        if any(d.loan_id == loan_id and d.status == "OPEN" for d in self.disputes.values()):
            raise BorrowError("An unresolved dispute already exists for this loan.")
        dispute = Dispute(uid("D"), loan_id, reporter_id, reason.strip())
        self.disputes[dispute.id] = dispute
        self.save()
        return dispute

    def resolve_dispute(self, dispute_id, admin_id):
        if not self.is_admin(admin_id):
            raise BorrowError("Only an administrator can resolve disputes.")
        dispute = self.disputes[dispute_id]
        dispute.status = "RESOLVED"
        self.save()

    def register_student(self, name: str, hostel_id: str):
        if hostel_id not in self.hostels:
            raise BorrowError("Choose a registered hostel.")
        user = Student(uid("S"), name, hostel_id)
        self.users[user.id] = user
        self.save()
        return user

    def register_hostel(self, admin_id: str, name: str, area: str):
        if not self.is_admin(admin_id):
            raise BorrowError("Only the administrator may register a hostel.")
        if not name.strip() or not area.strip():
            raise BorrowError("Hostel name and area are required.")
        hostel = Hostel(uid("H"), name.strip(), area.strip())
        self.hostels[hostel.id] = hostel
        self.save()
        return hostel

    def seed_demo(self):
        """Small demo illustrating AVAILABLE, TAKEN, RESERVED, CONFLICT, OVERDUE."""
        self.hostels = {
            "H1": Hostel("H1", "Premium Hostel", "Mukono"),
            "H2": Hostel("H2", "Riverside Hostel", "Mukono"),
        }
        self.users = {
            "S1": Student("S1", "Fred", "H1"),
            "S2": Student("S2", "John", "H1"),
            "S3": Student("S3", "Sarah", "H1"),
            "S4": Student("S4", "Amina", "H2"),
            "A1": Administrator("A1", "Hostel Administrator"),
        }
        samples = [
            ("I1", "S1", "Electric Iron", "Appliances", "Good", 8, 1, "HOURLY", 1000, 10000),
            ("I2", "S2", "Scientific Calculator", "Electronics", "Excellent", 24, 2, "HOURLY", 500, 10000),
            ("I3", "S3", "Extension Cable", "Electronics", "Good", 6, 1, "HOURLY", 1000, 8000),
            ("I4", "S1", "Computer Networks Textbook", "Books", "Good", 72, 24, "DAILY", 2000, 12000),
            ("I5", "S2", "Wireless Mouse", "Electronics", "Very good", 6, 1, "HOURLY", 750, 7500),
            ("I6", "S4", "USB-C Charger", "Electronics", "Good", 12, 2, "HOURLY", 500, 5000),
        ]
        self.items = {row[0]: Item(*row) for row in samples}
        now = datetime.now()
        # An item already in someone else's hands; see its return time.
        self.requests["R1"] = BorrowRequest("R1", "I2", "S1", 2, now.isoformat(), "FULFILLED")
        self.loans["L1"] = BorrowTransaction("L1", "R1", "I2", "S1", "S2",
            (now - timedelta(hours=1)).isoformat(), (now + timedelta(hours=1)).isoformat(),
            2, "HOURLY", 500, 10000)
        # An overdue item with a real charge after grace period.
        self.requests["R2"] = BorrowRequest("R2", "I5", "S3", 2, now.isoformat(), "FULFILLED")
        self.loans["L2"] = BorrowTransaction("L2", "R2", "I5", "S3", "S2",
            (now - timedelta(hours=6)).isoformat(), (now - timedelta(hours=4)).isoformat(),
            1, "HOURLY", 750, 7500)
        # Reserved item and a competing request that has become a conflict.
        self.requests["R3"] = BorrowRequest("R3", "I3", "S2", 3, now.isoformat(), "APPROVED")
        self.requests["R4"] = BorrowRequest("R4", "I3", "S1", 2, now.isoformat(), "CONFLICT",
                                               "John was approved for this item first.")
        self.requests["R5"] = BorrowRequest("R5", "I4", "S2", 24, now.isoformat(), "PENDING")

