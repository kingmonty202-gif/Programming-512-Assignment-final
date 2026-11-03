"""main.py - Tkinter GUI for the Smart Campus Resource Booking System.
Run with:  python main.py
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import database as db
import models


# ---------- colours (change these to restyle the whole system) ----------
BG_COLOR = "#ADD8E6"          # light blue window background
BUTTON_COLOR = "#2B6CB0"      # button background
BUTTON_HOVER = "#1E4E8C"      # button colour when the mouse is over it
ROLE_COLORS = {               # top bar colour for each user role
    "lecturer": "#1F6FB2",    # blue
    "admin": "#FFA500",       # orange
    "operator": "#ff0000",    # red
}


# ---------- small helper functions for tables ----------
def make_tree(parent, columns, widths):
    tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
    for col, width in zip(columns, widths):
        tree.heading(col, text=col)
        tree.column(col, width=width)
    tree.pack(fill="both", expand=True, padx=5, pady=5)
    return tree


def fill_tree(tree, rows):
    """First value of each row is the database id (used as the row id)."""
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert("", "end", iid=str(row[0]), values=row[1:])


def booking_rows(rows):
    """Change the raw status into Upcoming / Past / Cancelled and format times."""
    result = []
    for b in rows:
        state = models.booking_state(b[4], b[5], b[7])
        result.append((b[0], b[1], b[2], b[3], b[4], f"{b[5]:02d}:00", f"{b[6]} h", state))
    return result


BOOKING_COLS = ("Resource", "Campus", "Lecturer", "Date", "Start", "Duration", "Status")
BOOKING_WIDTHS = (160, 110, 100, 90, 60, 70, 90)


class App:
    def __init__(self, root):
        self.root = root
        root.title("Smart Campus Resource Booking System")
        root.geometry("900x600")
        root.configure(bg=BG_COLOR)
        self.style = ttk.Style()
        self.setup_colors()
        self.user = None
        self.campus = None          # (id, name) of the active campus
        self.refreshers = []        # functions that reload the tables
        self.show_login()

    def setup_colors(self, accent="#1F6FB2"):
        """Apply background and button colours to all ttk widgets."""
        st = self.style
        st.theme_use("clam")      # 'clam' lets us change colours on every platform
        st.configure("TFrame", background=BG_COLOR)
        st.configure("TLabel", background=BG_COLOR)
        st.configure("TNotebook", background=BG_COLOR)
        st.configure("TNotebook.Tab", padding=(12, 5))
        st.configure("TButton", background=BUTTON_COLOR, foreground="white", padding=5)
        st.map("TButton", background=[("active", BUTTON_HOVER)])
        st.configure("Treeview", rowheight=24)
        st.configure("Treeview.Heading", background=accent, foreground="white",
                     font=("Arial", 10, "bold"))
        # The top bar (campus / user info) uses the role colour
        st.configure("Top.TFrame", background=accent)
        st.configure("Top.TLabel", background=accent, foreground="white")

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.refreshers = []

    # ================= LOGIN / REGISTER =================
    def show_login(self):
        self.clear()
        self.user = None
        frame = ttk.Frame(self.root, padding=30)
        frame.pack(expand=True)
        ttk.Label(frame, text="Smart Campus Resource Booking System",
                  font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=15)
        ttk.Label(frame, text="Username:").grid(row=1, column=0, sticky="e", pady=5)
        ttk.Label(frame, text="Password:").grid(row=2, column=0, sticky="e", pady=5)
        self.username_entry = ttk.Entry(frame, width=25)
        self.password_entry = ttk.Entry(frame, width=25, show="*")
        self.username_entry.grid(row=1, column=1, pady=5)
        self.password_entry.grid(row=2, column=1, pady=5)
        ttk.Button(frame, text="Login", command=self.login).grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(frame, text="Register as Lecturer", command=self.register).grid(row=4, column=0, columnspan=2)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if username == "" or password == "":
            messagebox.showerror("Error", "Please enter username and password.")
            return
        row = db.check_login(username, password)
        if row is None:
            messagebox.showerror("Login failed", "Wrong username or password entered.")
            return
        self.user = models.create_user(row)
        self.show_campus_select()

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if len(username) < 3 or len(password) < 4:
            messagebox.showerror("Error", "Username needs 3+ characters and password 4+ characters.")
            return
        if db.add_user(username, password, "lecturer"):
            messagebox.showinfo("Success", "Account created. You can now log in.")
        else:
            messagebox.showerror("Error", "That username is already taken.")

    # ================= CAMPUS SELECTION =================
    def show_campus_select(self):
        self.clear()
        frame = ttk.Frame(self.root, padding=30)
        frame.pack(expand=True)
        ttk.Label(frame, text=f"Welcome, {self.user.username}", font=("Arial", 14, "bold")).pack(pady=10)
        ttk.Label(frame, text="Select a campus to work with:").pack()
        campuses = db.get_campuses()
        if self.user.role == "admin":      # admins can only use their own campus
            campuses = [c for c in campuses if c[0] == self.user.campus_id]
        self.campus_list = campuses
        self.campus_box = ttk.Combobox(frame, values=[c[1] for c in campuses], state="readonly")
        self.campus_box.current(0)
        self.campus_box.pack(pady=10)
        ttk.Button(frame, text="Continue", command=self.choose_campus).pack()

    def choose_campus(self):
        self.campus = self.campus_list[self.campus_box.current()]
        self.show_main()

    # ================= MAIN WINDOW =================
    def show_main(self):
        self.clear()
        self.setup_colors(ROLE_COLORS[self.user.role])
        top = ttk.Frame(self.root, padding=8, style="Top.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text=f"Active campus: {self.campus[1]}", style="Top.TLabel",
                  font=("Arial", 12, "bold")).pack(side="left")
        ttk.Label(top, text=f"     User: {self.user.username} ({self.user.role})",
                  style="Top.TLabel").pack(side="left")
        ttk.Button(top, text="Logout", command=self.show_login).pack(side="right")
        ttk.Button(top, text="Change campus", command=self.show_campus_select).pack(side="right", padx=5)
        rule = models.get_rule(self.campus[1])
        ttk.Label(self.root, text="Booking policy in effect: " + rule.describe(),
                  foreground="blue", wraplength=860).pack(anchor="w", padx=8)

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)
        self.tabs.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())

        if self.user.role == "lecturer":
            self.build_lecturer()
        elif self.user.role == "admin":
            self.build_admin()
        else:
            self.build_operator()
        self.refresh_all()

    def refresh_all(self):
        for func in self.refreshers:
            func()

    def new_tab(self, title):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text=title)
        return tab

    # ================= LECTURER =================
    def build_lecturer(self):
        # --- Tab 1: resources and availability ---
        tab = self.new_tab("Resources")
        self.res_tree = make_tree(tab, ("Code", "Name", "Availability"), (150, 300, 150))
        ttk.Button(tab, text="Refresh", command=self.refresh_all).pack(pady=3)
        self.refreshers.append(self.load_lecturer_resources)

        # --- Tab 2: make a booking ---
        tab = self.new_tab("Book a Resource")
        form = ttk.Frame(tab, padding=20)
        form.pack()
        ttk.Label(form, text="Resource:").grid(row=0, column=0, sticky="e", pady=5)
        self.res_box = ttk.Combobox(form, state="readonly", width=35)
        self.res_box.grid(row=0, column=1, pady=5)
        ttk.Label(form, text="Date (YYYY-MM-DD):").grid(row=1, column=0, sticky="e", pady=5)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(form, textvariable=self.date_var, width=20).grid(row=1, column=1, sticky="w", pady=5)
        ttk.Label(form, text="Start hour (0-23):").grid(row=2, column=0, sticky="e", pady=5)
        self.start_var = tk.StringVar(value="9")
        ttk.Spinbox(form, from_=0, to=23, textvariable=self.start_var, width=5).grid(row=2, column=1, sticky="w", pady=5)
        ttk.Label(form, text="Duration (hours):").grid(row=3, column=0, sticky="e", pady=5)
        self.dur_var = tk.StringVar(value="1")
        ttk.Spinbox(form, from_=1, to=8, textvariable=self.dur_var, width=5).grid(row=3, column=1, sticky="w", pady=5)
        ttk.Button(form, text="Book", command=self.make_booking).grid(row=4, column=0, columnspan=2, pady=10)

        # --- Tab 3: my bookings ---
        tab = self.new_tab("My Bookings")
        self.my_tree = make_tree(tab, BOOKING_COLS, BOOKING_WIDTHS)
        ttk.Button(tab, text="Cancel selected (future bookings only)",
                   command=self.cancel_selected).pack(pady=3)
        self.refreshers.append(self.load_my_bookings)

    def load_lecturer_resources(self):
        self.resources = db.get_resources(self.campus[0])
        rows = []
        for r in self.resources:
            status = "In use now" if db.is_in_use_now(r[0]) else "Available"
            rows.append((r[0], r[1], r[2], status))
        fill_tree(self.res_tree, rows)
        self.res_box["values"] = [f"{r[1]} - {r[2]}" for r in self.resources]

    def load_my_bookings(self):
        fill_tree(self.my_tree, booking_rows(db.get_bookings(lecturer_id=self.user.user_id)))

    def make_booking(self):
        index = self.res_box.current()
        if index < 0:
            messagebox.showerror("Error", "Please select a resource.")
            return
        try:
            start = int(self.start_var.get())
            duration = int(self.dur_var.get())
        except ValueError:
            messagebox.showerror("Error", "Start hour and duration must be whole numbers.")
            return
        date_text = self.date_var.get().strip()
        error = models.validate_booking(self.campus[1], date_text, start, duration)
        if error:
            messagebox.showerror("Booking rule", error)
            return
        resource_id = self.resources[index][0]
        if db.has_overlap(resource_id, date_text, start, duration):
            messagebox.showerror("Not available", "That resource is already booked at this time.")
            return
        db.add_booking(resource_id, self.user.user_id, self.campus[0], date_text, start, duration)
        messagebox.showinfo("Success", "Booking created.")
        self.refresh_all()

    def cancel_selected(self):
        selected = self.my_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a booking first.")
            return
        status = self.my_tree.item(selected[0], "values")[6]
        if status != "Upcoming":
            messagebox.showerror("Error", "Only upcoming bookings can be cancelled.")
            return
        if messagebox.askyesno("Confirm", "Cancel this booking?"):
            db.cancel_booking(int(selected[0]))
            self.refresh_all()

    # ================= CAMPUS ADMIN =================
    def build_admin(self):
        # --- Tab 1: manage resources ---
        tab = self.new_tab("Manage Resources")
        self.admin_tree = make_tree(tab, ("Code", "Name"), (200, 300))
        self.admin_tree.bind("<<TreeviewSelect>>", self.on_resource_select)
        form = ttk.Frame(tab)
        form.pack(pady=5)
        ttk.Label(form, text="Code:").grid(row=0, column=0)
        self.code_entry = ttk.Entry(form, width=15)
        self.code_entry.grid(row=0, column=1, padx=5)
        ttk.Label(form, text="Name:").grid(row=0, column=2)
        self.name_entry = ttk.Entry(form, width=25)
        self.name_entry.grid(row=0, column=3, padx=5)
        ttk.Button(form, text="Add", command=self.add_resource).grid(row=1, column=1, pady=5)
        ttk.Button(form, text="Update name", command=self.update_resource).grid(row=1, column=2)
        ttk.Button(form, text="Remove", command=self.remove_resource).grid(row=1, column=3)
        self.refreshers.append(self.load_admin_resources)

        # --- Tab 2: campus bookings ---
        tab = self.new_tab("Campus Bookings")
        self.campus_tree = make_tree(tab, BOOKING_COLS, BOOKING_WIDTHS)
        self.refreshers.append(self.load_campus_bookings)

        # --- Tab 3: report ---
        tab = self.new_tab("Campus Report")
        self.report_text = tk.Text(tab, height=20, state="disabled")
        self.report_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.refreshers.append(self.load_campus_report)

    def load_admin_resources(self):
        rows = [(r[0], r[1], r[2]) for r in db.get_resources(self.campus[0])]
        fill_tree(self.admin_tree, rows)

    def load_campus_bookings(self):
        fill_tree(self.campus_tree, booking_rows(db.get_bookings(campus_id=self.campus[0])))

    def load_campus_report(self):
        report = db.campus_report(self.campus[0])
        text = f"REPORT FOR {self.campus[1].upper()}\n\n"
        text += f"Total bookings: {report['total']}\n"
        text += f"Average booking duration: {report['average']:.1f} hours\n\n"
        text += "Most frequently used resources:\n"
        for name, count in report["top"]:
            text += f"   {name}: {count} booking(s)\n"
        if not report["top"]:
            text += "   (no bookings yet)\n"
        text += "\nUsage trend (bookings per month):\n"
        for month, count in report["months"]:
            text += f"   {month}: {count}\n"
        self.report_text.config(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", text)
        self.report_text.config(state="disabled")

    def on_resource_select(self, event):
        selected = self.admin_tree.selection()
        if selected:
            code, name = self.admin_tree.item(selected[0], "values")
            self.code_entry.delete(0, "end")
            self.code_entry.insert(0, code)
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, name)

    def add_resource(self):
        code = self.code_entry.get().strip().upper()
        name = self.name_entry.get().strip()
        if code == "" or name == "":
            messagebox.showerror("Error", "Enter both a code and a name.")
            return
        if db.add_resource(code, name, self.campus[0]):
            self.refresh_all()
        else:
            messagebox.showerror("Duplicate", "A resource with that code already exists.")

    def update_resource(self):
        selected = self.admin_tree.selection()
        name = self.name_entry.get().strip()
        if not selected or name == "":
            messagebox.showerror("Error", "Select a resource and type the new name.")
            return
        db.update_resource(int(selected[0]), name)
        self.refresh_all()

    def remove_resource(self):
        selected = self.admin_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a resource first.")
            return
        if db.has_future_bookings(int(selected[0])):
            messagebox.showerror("Error", "This resource still has active bookings.")
            return
        if messagebox.askyesno("Confirm", "Remove this resource?"):
            db.delete_resource(int(selected[0]))
            self.refresh_all()

    # ================= SYSTEM OPERATOR =================
    def build_operator(self):
        tab = self.new_tab("All Bookings")
        self.all_tree = make_tree(tab, BOOKING_COLS, BOOKING_WIDTHS)
        self.refreshers.append(lambda: fill_tree(self.all_tree, booking_rows(db.get_bookings())))

        tab = self.new_tab("All Resources")
        self.allres_tree = make_tree(tab, ("Campus", "Code", "Name"), (150, 150, 300))
        self.refreshers.append(lambda: fill_tree(self.allres_tree, db.get_all_resources()))

        tab = self.new_tab("Campus Comparison")
        self.compare_tree = make_tree(
            tab, ("Campus", "Total bookings", "Avg duration (h)", "Most used resource", "Max hours rule"),
            (120, 110, 120, 200, 110))
        self.refreshers.append(self.load_comparison)

    def load_comparison(self):
        rows = []
        for campus_id, name in db.get_campuses():
            report = db.campus_report(campus_id)
            top = report["top"][0][0] if report["top"] else "-"
            rows.append((campus_id, name, report["total"], f"{report['average']:.1f}",
                         top, models.get_rule(name).max_hours))
        fill_tree(self.compare_tree, rows)


if __name__ == "__main__":
    db.create_tables()
    db.seed_data()
    window = tk.Tk()
    App(window)
    window.mainloop()
