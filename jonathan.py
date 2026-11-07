"""Member 3: Terminal UI, menus, tables and read-only views.

Presents listed, available, reserved and taken items, due dates,
conflicts, loan history, fines and OOP explanations in the terminal.
"""
from __future__ import annotations

from datetime import datetime

from models import BorrowError, Student, cash, readable
from service import BorrowingSystem

def display_table(headers, rows, widths=None):
    """Display short readable tables without external dependencies."""
    rows = [[str(value) for value in row] for row in rows]
    if not rows:
        print("  (No records to display.)")
        return
    if widths is None:
        widths = [min(32, max(len(header), *(len(row[i]) for row in rows)))
                  for i, header in enumerate(headers)]
    def fit(value, width):
        return value if len(value) <= width else value[:width - 3] + "..."
    def line(values):
        return "  " + " | ".join(fit(str(text), width).ljust(width)
                                  for text, width in zip(values, widths))
    print(line(headers))
    print("  " + "-+-".join("-" * width for width in widths))
    for row in rows:
        print(line(row))
    print(f"  {len(rows)} record(s).")



class TerminalViews:
    """Shared terminal input, presentation and reporting behaviour."""

    def __init__(self, service: BorrowingSystem):
        self.service = service  # COMPOSITION: CLI contains and uses a service object.
        self.current_user_id = "S1" if "S1" in service.users else next(iter(service.users))

    @property
    def actor(self):
        return self.current_user_id

    @property
    def user(self):
        return self.service.users[self.actor]

    def ask(self, label, default=None, required=True):
        while True:
            hint = f" [{default}]" if default is not None else ""
            result = input(f"{label}{hint}: ").strip()
            if result:
                return result
            if default is not None:
                return str(default)
            if not required:
                return ""
            print("Please enter a value.")

    def ask_int(self, label, minimum=0, maximum=None, default=None):
        while True:
            raw = self.ask(label, default=default)
            try:
                value = int(raw)
            except ValueError:
                print("Enter a whole number.")
                continue
            if value < minimum or (maximum is not None and value > maximum):
                print(f"Enter a number from {minimum} to {maximum if maximum is not None else 'above'}.")
                continue
            return value

    def yes(self, label):
        return self.ask(f"{label} (yes/no)", default="no").lower() in ("y", "yes")

    def identity(self, user_id):
        return self.service.users[user_id].name

    def visible_item(self, item):
        if self.service.is_admin(self.actor):
            return True
        return self.service.student(item.owner_id).hostel_id == self.service.student(self.actor).hostel_id

    def visible_loan(self, loan):
        return (self.service.is_admin(self.actor)
                or loan.borrower_id == self.actor or loan.lender_id == self.actor
                or self.service.same_hostel(self.actor, self.service.items[loan.item_id]))

    def heading(self, text):
        print("\n" + "=" * 80)
        print("  " + text)
        print("=" * 80)

    def run_menu(self, title, entries, main=False):
        """One menu method supports multiple screens (code reuse)."""
        while True:
            self.heading(title)
            for number, label, _fn in entries:
                print(f"  {number:>2}. {label}")
            print("   0. " + ("Save and exit" if main else "Back"))
            choice = input("\nChoose an option: ").strip()
            if choice == "0":
                return
            selected = next((fn for number, _label, fn in entries if number == choice), None)
            if selected is None:
                print("Invalid option. Please choose a number shown in the menu.")
                continue
            try:
                selected()
            except (BorrowError, ValueError, KeyError, OSError, TypeError) as error:
                print(f"\n[NOT COMPLETED] {error}")

    def dashboard(self):
        self.heading(f"DASHBOARD — {self.user.name} ({self.user.role})")
        if isinstance(self.user, Student):
            hostel = self.service.hostels[self.user.hostel_id]
            print(f"Hostel: {hostel.name} | Area: {hostel.area}")
        else:
            print("Hostel: All hostels (administrator overview)")
        items = [item for item in self.service.items.values() if self.visible_item(item)]
        counts = {status: sum(self.service.item_state(item) == status for item in items)
                  for status in ("AVAILABLE", "TAKEN", "RESERVED", "PAUSED")}
        conflicts = sum(r.status == "CONFLICT" and self.visible_item(self.service.items[r.item_id])
                        for r in self.service.requests.values())
        print(f"Listed items: {len(items)} | Available: {counts['AVAILABLE']} | "
              f"Taken: {counts['TAKEN']} | Reserved: {counts['RESERVED']} | "
              f"Paused: {counts['PAUSED']} | Conflicts: {conflicts}")
        active = [loan for loan in self.service.loans.values()
                  if loan.status != "RETURNED" and self.visible_loan(loan)]
        print(f"\nActive loans: {len(active)}")
        display_table(["Loan", "Item", "Borrower", "Due", "Status", "Fine"], [
            (loan.id, self.service.items[loan.item_id].name,
             self.identity(loan.borrower_id), readable(loan.due),
             loan.display_status(), cash(loan.fine_total())) for loan in active],
             [12, 24, 16, 21, 16, 13])
        notices = [note for note in self.service.notifications if note.user_id == self.actor]
        if notices:
            print(f"\nLatest notification: {notices[-1].message}")

    def list_items(self, filter_status=None, mine=False):
        title = "MY LISTED ITEMS" if mine else (f"{filter_status} ITEMS" if filter_status else "ITEM MARKETPLACE")
        self.heading(title)
        query = "" if filter_status or mine else self.ask("Search name/category (Enter for all)", required=False).lower()
        rows = []
        for item in self.service.items.values():
            if not self.visible_item(item) or (mine and item.owner_id != self.actor):
                continue
            state = self.service.item_state(item)
            if filter_status and state != filter_status:
                continue
            if query and query not in f"{item.name} {item.category} {self.identity(item.owner_id)}".lower():
                continue
            owner = self.service.student(item.owner_id)
            rows.append((item.id, item.name, owner.name,
                         self.service.hostels[owner.hostel_id].name,
                         state, self.service.item_due(item)))
        display_table(["Item ID", "Item", "Owner", "Hostel", "Status", "Due back"],
                      rows, [12, 27, 16, 18, 12, 21])
        if rows:
            print("\nUse the Item ID to request, pause, or resume an item.")

    def show_requests(self, incoming=True):
        self.heading("INCOMING BORROW REQUESTS" if incoming else "OUTGOING BORROW REQUESTS")
        rows = []
        for req in self.service.requests.values():
            item = self.service.items[req.item_id]
            if not self.service.is_admin(self.actor):
                if incoming and item.owner_id != self.actor:
                    continue
                if not incoming and req.borrower_id != self.actor:
                    continue
            rows.append((req.id, item.name, self.identity(req.borrower_id),
                         self.identity(item.owner_id), f"{req.hours}h", req.status, req.reason))
        display_table(["Request", "Item", "Borrower", "Owner", "Duration", "Status", "Reason"],
                      rows, [12, 22, 14, 14, 9, 12, 35])

    def show_loans(self):
        self.heading("TAKEN ITEMS / ACTIVE LOANS / RETURN DEADLINES")
        rows = []
        for loan in self.service.loans.values():
            if loan.status == "RETURNED" or not self.visible_loan(loan):
                continue
            rows.append((loan.id, self.service.items[loan.item_id].name,
                         self.identity(loan.borrower_id), self.identity(loan.lender_id),
                         readable(loan.due), readable(loan.grace_deadline),
                         loan.display_status(), cash(loan.fine_total())))
        display_table(["Loan", "Item", "Borrower", "Lender", "Return due", "Grace ends", "Status", "Fine now"],
                      rows, [12, 21, 14, 14, 21, 21, 16, 13])
        if rows:
            print("\nTAKEN: out with a borrower; GRACE PERIOD: late but fine-free; OVERDUE: fine applies.")

    def show_conflicts(self):
        self.heading("BORROWING CONFLICTS AND DISPUTES")
        rows = []
        for req in self.service.requests.values():
            item = self.service.items[req.item_id]
            if req.status == "CONFLICT" and self.visible_item(item):
                rows.append((req.id, "CONFLICT", item.name,
                             self.identity(req.borrower_id), req.status, req.reason))
        for dispute in self.service.disputes.values():
            loan = self.service.loans[dispute.loan_id]
            if self.visible_loan(loan):
                rows.append((dispute.id, "DISPUTE", self.service.items[loan.item_id].name,
                             self.identity(dispute.reporter_id), dispute.status, dispute.reason))
        display_table(["ID", "Type", "Item", "Student", "Status", "Reason"],
                      rows, [12, 10, 24, 16, 12, 48])
        print("CONFLICT = competing request. DISPUTE = reported problem under administrator review.")

    def show_history(self):
        self.heading("BORROWING HISTORY AND FINES")
        rows = []
        for loan in self.service.loans.values():
            if not self.visible_loan(loan):
                continue
            rows.append((loan.id, self.service.items[loan.item_id].name,
                         self.identity(loan.borrower_id), loan.display_status(),
                         readable(datetime.fromisoformat(loan.returned_at)) if loan.returned_at else "Not returned",
                         cash(loan.fine_total()), cash(loan.fine_paid), cash(loan.outstanding())))
        display_table(["Loan", "Item", "Borrower", "Status", "Returned", "Fine", "Paid", "Outstanding"],
                      rows, [12, 22, 14, 16, 21, 13, 13, 13])

    def notifications(self):
        self.heading(f"NOTIFICATIONS FOR {self.user.name.upper()}")
        notes = [note for note in self.service.notifications if note.user_id == self.actor]
        if not notes:
            print("  No notifications yet.")
        for note in notes[-20:]:
            print(f"  [{readable(datetime.fromisoformat(note.created_at))}] {note.message}")

    def oop_concepts(self):
        self.heading("OOP PRINCIPLES USED BY BORROWPLUG")
        print("  ABSTRACTION:   User and FinePolicy are abstract base classes (ABC).")
        print("  INHERITANCE:   Student and Administrator inherit from User.")
        print("                 HourlyFinePolicy and DailyFinePolicy inherit FinePolicy.")
        print("  POLYMORPHISM: Both fine policies implement calculate() differently.")
        print("  ENCAPSULATION: User and Item have private attributes and property access.")
        print("  COMPOSITION:  BorrowingSystem stores the user/item/request/loan objects.")
        print("  ASSOCIATION:  Loan and request objects reference users and items by ID.")
        print("  OVERRIDING:   Student/Administrator implement role and to_dict().")
        print("  EXCEPTIONS:   BorrowError is raised on invalid borrow/return operations.")
        print("  PERSISTENCE:  Data is stored in borrowplug_data.json automatically.")


