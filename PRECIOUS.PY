"""Member 4: Terminal actions, user workflows and application entry point.

Starts the terminal app and connects menus/actions to Member 2's
BorrowingSystem, using Member 3's TerminalViews for displays.
Run from the repository directory: python terminal_app.py
"""
from __future__ import annotations

from models import BorrowError, Student, cash, readable
from service import BorrowingSystem
from terminal_views import TerminalViews, display_table


class BorrowPlugTerminal(TerminalViews):
    """Handles user actions and menu navigation through inheritance."""

    def switch_user(self):
        self.heading("SWITCH USER / SIMULATE LOGIN (DEMO MODE)")
        display_table(["User ID", "Name", "Role", "Hostel"], [
            (user.id, user.name, user.role,
             self.service.hostels[user.hostel_id].name if isinstance(user, Student) else "All")
            for user in self.service.users.values()], [12, 23, 10, 22])
        new_user = self.ask("Enter user ID").upper()
        if new_user not in self.service.users:
            raise BorrowError("That user ID does not exist.")
        self.current_user_id = new_user
        print(f"Now viewing as {self.user.name} ({self.user.role}).")

    def add_item(self):
        self.service.student(self.actor)
        self.heading("LIST AN ITEM")
        name = self.ask("Item name")
        category = self.ask("Category")
        condition = self.ask("Condition", default="Good")
        max_hours = self.ask_int("Maximum borrowing hours", minimum=1, maximum=8760, default=8)
        grace = self.ask_int("Grace period after due date (hours)", minimum=0, maximum=168, default=1)
        policy = self.ask("Fine policy (HOURLY or DAILY)", default="HOURLY").upper()
        rate = self.ask_int("Fine rate in UGX per hour/day", default=1000)
        cap = self.ask_int("Maximum fine cap in UGX", default=10000)
        item = self.service.add_item(self.actor, name, category, condition,
                                     max_hours, grace, policy, rate, cap)
        print(f"SUCCESS: {item.name} listed. Item ID: {item.id}")

    def toggle_item(self):
        self.list_items(mine=True)
        item_id = self.ask("Item ID to pause/resume").upper()
        self.service.set_item_visibility(item_id, self.actor)
        print(f"Item is now {self.service.item_state(self.service.items[item_id])}.")

    def item_menu(self):
        self.run_menu("ITEMS & MARKETPLACE", [
            ("1", "Show all listed items", self.list_items),
            ("2", "Show available items", lambda: self.list_items("AVAILABLE")),
            ("3", "Show taken items and return deadlines", lambda: self.list_items("TAKEN")),
            ("4", "Show reserved items", lambda: self.list_items("RESERVED")),
            ("5", "Show my listed items", lambda: self.list_items(mine=True)),
            ("6", "Add a new item", self.add_item),
            ("7", "Pause / resume my item", self.toggle_item),
        ])

    def request_item(self):
        self.service.student(self.actor)
        self.list_items()
        item_id = self.ask("Enter Item ID to borrow").upper()
        item = self.service.items[item_id]
        hours = self.ask_int("Borrow for how many hours", minimum=1, maximum=item.max_hours)
        unit = "hour" if item.policy == "HOURLY" else "day"
        print(f"\nAGREEMENT: {item.name}, {hours}h, grace {item.grace_hours}h, "
              f"fine {cash(item.fine_rate)}/{unit} (cap {cash(item.fine_cap)}).")
        if not self.yes("Do you agree to these borrowing conditions and send the request?"):
            print("Request cancelled.")
            return
        req = self.service.request_item(self.actor, item_id, hours)
        print(f"SUCCESS: Request {req.id}, status {req.status}.")
        if req.reason:
            print(f"CONFLICT: {req.reason}")
        else:
            print("The owner must approve your request.")

    def approve_request(self):
        self.show_requests(incoming=True)
        req_id = self.ask("Request ID to approve").upper()
        self.service.approve_request(req_id, self.actor)
        print("Request approved. Borrower must confirm the physical collection.")

    def reject_request(self):
        self.show_requests(incoming=True)
        req_id = self.ask("Request ID to reject").upper()
        self.service.reject_request(req_id, self.actor)
        print("Request rejected.")

    def collect_item(self):
        self.show_requests(incoming=False)
        req_id = self.ask("Approved Request ID to collect").upper()
        if not self.yes("Have you physically received this item from the owner?"):
            print("Collection cancelled.")
            return
        loan = self.service.collect_item(req_id, self.actor)
        print(f"LOAN STARTED: {loan.id} | Due: {readable(loan.due)} | "
              f"Grace ends: {readable(loan.grace_deadline)}")

    def requests_menu(self):
        self.run_menu("BORROWING REQUESTS", [
            ("1", "Request an item", self.request_item),
            ("2", "View incoming requests (as lender)", lambda: self.show_requests(True)),
            ("3", "View outgoing requests (as borrower)", lambda: self.show_requests(False)),
            ("4", "Approve a request", self.approve_request),
            ("5", "Reject a request", self.reject_request),
            ("6", "Confirm physical item collection", self.collect_item),
        ])

    def request_return(self):
        self.show_loans()
        loan_id = self.ask("Loan ID you want to return").upper()
        if self.yes("Are you handing this item back now?"):
            self.service.request_return(loan_id, self.actor)
            print("Return requested. Owner must confirm receiving the item.")

    def confirm_return(self):
        self.show_loans()
        loan_id = self.ask("Loan ID whose return you received").upper()
        condition = self.ask("Item condition on return", default="Good")
        if self.yes("Do you confirm you physically received this item?"):
            self.service.confirm_return(loan_id, self.actor, condition)
            print(f"Return confirmed. Final fine: {cash(self.service.loans[loan_id].fine_total())}.")

    def request_extension(self):
        self.show_loans()
        loan_id = self.ask("Loan ID to extend").upper()
        hours = self.ask_int("Additional hours (1-24)", minimum=1, maximum=24)
        self.service.request_extension(loan_id, self.actor, hours)
        print("Extension requested. Owner must approve it.")

    def decide_extension(self):
        self.show_loans()
        loan_id = self.ask("Loan ID with an extension request").upper()
        approve = self.yes("Approve extension? (No means reject)")
        self.service.decide_extension(loan_id, self.actor, approve)
        print("Extension approved." if approve else "Extension rejected.")

    def loans_menu(self):
        self.run_menu("TAKEN ITEMS & RETURN MANAGEMENT", [
            ("1", "View taken items, deadlines and current fines", self.show_loans),
            ("2", "Borrower: request return", self.request_return),
            ("3", "Owner: confirm returned item", self.confirm_return),
            ("4", "Borrower: request extension", self.request_extension),
            ("5", "Owner: approve/reject extension", self.decide_extension),
        ])

    def report_issue(self):
        self.show_loans()
        loan_id = self.ask("Loan ID to report a problem with").upper()
        reason = self.ask("Describe the problem")
        dispute = self.service.open_dispute(loan_id, self.actor, reason)
        print(f"Dispute {dispute.id} created; status: {dispute.status}.")

    def resolve_dispute(self):
        self.show_conflicts()
        dispute_id = self.ask("Dispute ID to resolve (starts with D)").upper()
        self.service.resolve_dispute(dispute_id, self.actor)
        print(f"Dispute {dispute_id} resolved.")

    def conflicts_menu(self):
        self.run_menu("CONFLICTS & DISPUTES", [
            ("1", "Show conflicts and disputes", self.show_conflicts),
            ("2", "Report a borrowing problem", self.report_issue),
            ("3", "Administrator: mark dispute resolved", self.resolve_dispute),
        ])

    def pay_fine(self):
        self.show_history()
        loan_id = self.ask("Loan ID to pay fine for").upper()
        if not self.yes("Record this fine as paid? This is a DEMO payment (no actual money moves)"):
            print("Payment cancelled.")
            return
        paid = self.service.pay_fine(loan_id, self.actor)
        print(f"Demo payment recorded: {cash(paid)}.")

    def history_menu(self):
        self.run_menu("HISTORY & FINES", [
            ("1", "Show borrowing history, fines and balances", self.show_history),
            ("2", "Record a DEMO fine payment", self.pay_fine),
        ])

    def register_student(self):
        self.heading("REGISTER STUDENT")
        display_table(["Hostel ID", "Hostel", "Area"],
                      [(h.id, h.name, h.area) for h in self.service.hostels.values()],
                      [12, 28, 24])
        name = self.ask("Student name")
        hostel_id = self.ask("Hostel ID").upper()
        student = self.service.register_student(name, hostel_id)
        print(f"Student {student.name} registered successfully with ID: {student.id}.")

    def register_hostel(self):
        self.heading("REGISTER HOSTEL (ADMIN ONLY)")
        name = self.ask("Hostel name")
        area = self.ask("Area / neighbourhood")
        hostel = self.service.register_hostel(self.actor, name, area)
        print(f"Hostel {hostel.name} registered successfully with ID: {hostel.id}.")

    def run(self):
        self.heading("BORROWPLUG | HOSTEL BORROWING SYSTEM | PYTHON OOP")
        print("Terminal-only edition (no Tkinter, no HTML, no external packages).")
        print("Demo users: Fred, John, Sarah, Amina, Hostel Administrator.")
        print("All records are saved to borrowplug_data.json next to this file.")
        self.run_menu("MAIN MENU", [
            ("1", "Switch current user (demo)", self.switch_user),
            ("2", "Dashboard: available, taken, conflicts and due dates", self.dashboard),
            ("3", "Items: marketplace, available and listed items", self.item_menu),
            ("4", "Borrow requests: send, approve, reject, collect", self.requests_menu),
            ("5", "Taken items: due dates, returns and extensions", self.loans_menu),
            ("6", "Conflicts and disputes", self.conflicts_menu),
            ("7", "History and fines", self.history_menu),
            ("8", "Notifications", self.notifications),
            ("9", "Register student", self.register_student),
            ("10", "Register hostel (administrator)", self.register_hostel),
            ("11", "Explain OOP concepts implemented", self.oop_concepts),
        ], main=True)
        self.service.save()
        print("\nBorrowPlug has saved your work. Goodbye!")


def main():
    try:
        service = BorrowingSystem.load()
        BorrowPlugTerminal(service).run()
    except (KeyboardInterrupt, EOFError):
        print("\nTerminal closed. Previously completed changes were already saved.")
    except (BorrowError, OSError) as exc:
        print(f"\nStartup error: {exc}")
        print("If the JSON file is damaged, back it up before resetting it.")


if __name__ == "__main__":
    main()
