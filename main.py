import hashlib
import hmac
import json
import platform
import secrets
import socket
import tkinter as tk
import uuid
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

try:
    import psutil
except ImportError:
    psutil = None


# CART3R stores its settings beside this Python file.
BASE_DIR = Path(__file__).resolve().parent
AUTH_FILE = BASE_DIR / "cart3r_auth.json"
DEVICE_FILE = BASE_DIR / "cart3r_device.json"
ACTIVITY_FILE = BASE_DIR / "cart3r_activity.jsonl"
PBKDF2_ITERATIONS = 300_000

BG = "#101010"
PANEL = "#1b1b1b"
RED = "#d71920"
TEXT = "#f2f2f2"
MUTED = "#aaaaaa"


def now_text():
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def write_activity(event, details=""):
    """Append one local event. Never write passwords or other secrets here."""
    entry = {
        "time": now_text(),
        "event": str(event),
        "details": str(details),
    }
    try:
        with ACTIVITY_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        # Logging failure should not crash the dashboard.
        print(f"Could not write CART3R activity log: {exc}")


def read_activity(limit=250):
    entries = []
    if not ACTIVITY_FILE.exists():
        return entries

    try:
        with ACTIVITY_FILE.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        entries.append(item)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []

    return entries[-limit:][::-1]


def make_password_record(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    # Keep the same common salt/hash JSON format used by earlier CART3R builds.
    return {"salt": salt.hex(), "hash": digest.hex()}


def save_password(password):
    record = make_password_record(password)
    with AUTH_FILE.open("w", encoding="utf-8") as file:
        json.dump(record, file)


def verify_password(password):
    try:
        with AUTH_FILE.open("r", encoding="utf-8") as file:
            record = json.load(file)
        salt_value = record.get("salt")
        expected_value = record.get("hash") or record.get("password_hash")
        if not salt_value or not expected_value:
            return False
        salt = bytes.fromhex(salt_value)
        expected = bytes.fromhex(expected_value)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
        )
        return hmac.compare_digest(actual, expected)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def load_device():
    device = {}
    if DEVICE_FILE.exists():
        try:
            with DEVICE_FILE.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
                if isinstance(loaded, dict):
                    device = loaded
        except (OSError, json.JSONDecodeError):
            device = {}

    # Keep existing values when present, and fill in missing information.
    device.setdefault("device_id", str(uuid.uuid4()).upper())
    device.setdefault("computer_name", socket.gethostname())
    device.setdefault("operating_system", f"{platform.system()} {platform.release()}")
    device.setdefault("registered", False)
    return device


def save_device(device):
    with DEVICE_FILE.open("w", encoding="utf-8") as file:
        json.dump(device, file, indent=2)


class CART3RApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CART3R | System Monitor")
        self.root.geometry("900x650")
        self.root.minsize(760, 540)
        self.root.configure(bg=BG)
        self.device = load_device()
        self._closing = False
        self._build_style()
        self.show_auth_screen()
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab", background="#292929", foreground=TEXT,
            padding=(16, 9), font=("Segoe UI", 10, "bold")
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", RED)],
            foreground=[("selected", "white")],
        )
        style.configure(
            "Treeview", background=PANEL, fieldbackground=PANEL,
            foreground=TEXT, rowheight=28, borderwidth=0,
            font=("Segoe UI", 9)
        )
        style.configure(
            "Treeview.Heading", background="#292929", foreground=TEXT,
            font=("Segoe UI", 9, "bold"), relief="flat"
        )
        style.map("Treeview", background=[("selected", "#542024")])
        style.configure(
            "Horizontal.TProgressbar", troughcolor="#333333",
            background=RED, bordercolor="#333333", lightcolor=RED,
            darkcolor=RED
        )

    def make_button(self, parent, text, command, width=None):
        return tk.Button(
            parent, text=text, command=command, width=width,
            bg=RED, fg="white", activebackground="#a81319",
            activeforeground="white", relief="flat", bd=0,
            padx=13, pady=8, cursor="hand2",
            font=("Segoe UI", 10, "bold")
        )

    def make_label(self, parent, text, size=10, color=TEXT, bold=False):
        return tk.Label(
            parent, text=text, bg=parent.cget("bg"), fg=color,
            font=("Segoe UI", size, "bold" if bold else "normal")
        )

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_auth_screen(self):
        self.clear_window()
        first_setup = not AUTH_FILE.exists()

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(expand=True)
        tk.Label(
            outer, text="CART3R", bg=BG, fg=RED,
            font=("Segoe UI", 32, "bold")
        ).pack(pady=(0, 5))
        self.make_label(
            outer,
            "Create a local password" if first_setup else "Enter your password",
            12, MUTED
        ).pack(pady=(0, 20))

        password_var = tk.StringVar()
        entry = tk.Entry(
            outer, textvariable=password_var, show="•", width=30,
            bg="#252525", fg=TEXT, insertbackground=TEXT,
            relief="flat", font=("Segoe UI", 12)
        )
        entry.pack(ipady=9, pady=5)
        entry.focus_set()

        confirm_var = tk.StringVar()
        confirm_entry = None
        if first_setup:
            confirm_entry = tk.Entry(
                outer, textvariable=confirm_var, show="•", width=30,
                bg="#252525", fg=TEXT, insertbackground=TEXT,
                relief="flat", font=("Segoe UI", 12)
            )
            confirm_entry.pack(ipady=9, pady=5)
            confirm_entry.insert(0, "")
            confirm_entry.bind("<Return>", lambda _event: submit())
        else:
            entry.bind("<Return>", lambda _event: submit())

        def submit():
            password = password_var.get()
            if first_setup:
                if len(password) < 8:
                    messagebox.showwarning(
                        "Password too short",
                        "Choose a password with at least 8 characters.",
                        parent=self.root,
                    )
                    return
                if password != confirm_var.get():
                    messagebox.showerror(
                        "Passwords do not match",
                        "Type the same password in both boxes.",
                        parent=self.root,
                    )
                    return
                try:
                    save_password(password)
                except OSError as exc:
                    messagebox.showerror("Save error", str(exc), parent=self.root)
                    return
                write_activity("Password created", "Local CART3R password set up")
            else:
                if not verify_password(password):
                    messagebox.showerror(
                        "Incorrect password", "That password was not correct.",
                        parent=self.root,
                    )
                    return
                write_activity("Login successful", "Local login completed")

            password_var.set("")
            confirm_var.set("")
            write_activity("Application opened", "CART3R dashboard opened")
            self.show_dashboard()

        self.make_button(outer, "Continue", submit, width=22).pack(pady=18)
        self.make_label(
            outer, "This login protects this local CART3R app only.", 9, MUTED
        ).pack(pady=5)

    def show_dashboard(self):
        self.clear_window()
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=22, pady=(16, 10))
        tk.Label(
            header, text="CART3R", bg=BG, fg=RED,
            font=("Segoe UI", 23, "bold")
        ).pack(side="left")
        tk.Label(
            header, text="LOCAL SYSTEM MONITOR", bg=BG, fg=MUTED,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=14, pady=(8, 0))
        self.make_button(header, "Log out", self.logout).pack(side="right")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.dashboard_tab = tk.Frame(self.notebook, bg=BG)
        self.device_tab = tk.Frame(self.notebook, bg=BG)
        self.activity_tab = tk.Frame(self.notebook, bg=BG)
        self.security_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.device_tab, text="Device")
        self.notebook.add(self.activity_tab, text="Activity Log")
        self.notebook.add(self.security_tab, text="Security")

        self.build_dashboard_tab()
        self.build_device_tab()
        self.build_activity_tab()
        self.build_security_tab()
        self.update_stats()

    def build_dashboard_tab(self):
        tab = self.dashboard_tab
        self.make_label(tab, "System overview", 18, TEXT, True).pack(
            anchor="w", padx=22, pady=(22, 5)
        )
        self.make_label(
            tab, f"Computer: {socket.gethostname()}", 10, MUTED
        ).pack(anchor="w", padx=22, pady=(0, 18))

        self.stat_labels = {}
        for key, title in (("cpu", "CPU usage"), ("ram", "Memory usage"), ("disk", "Disk usage")):
            card = tk.Frame(tab, bg=PANEL, padx=18, pady=13)
            card.pack(fill="x", padx=22, pady=7)
            top = tk.Frame(card, bg=PANEL)
            top.pack(fill="x")
            tk.Label(
                top, text=title, bg=PANEL, fg=TEXT,
                font=("Segoe UI", 11, "bold")
            ).pack(side="left")
            value = tk.Label(
                top, text="Checking...", bg=PANEL, fg=RED,
                font=("Segoe UI", 11, "bold")
            )
            value.pack(side="right")
            bar = ttk.Progressbar(card, maximum=100, mode="determinate")
            bar.pack(fill="x", pady=(10, 0))
            self.stat_labels[key] = (value, bar)

        self.clock_label = self.make_label(tab, "", 10, MUTED)
        self.clock_label.pack(anchor="w", padx=22, pady=14)

    def update_stats(self):
        if (
            not self.root.winfo_exists()
            or not hasattr(self, "notebook")
            or not self.notebook.winfo_exists()
            or not hasattr(self, "stat_labels")
        ):
            return
        if psutil is None:
            for key in self.stat_labels:
                self.stat_labels[key][0].configure(text="psutil not installed")
                self.stat_labels[key][1]["value"] = 0
        else:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage(str(BASE_DIR.anchor)).percent
                for key, value in (("cpu", cpu), ("ram", ram), ("disk", disk)):
                    label, bar = self.stat_labels[key]
                    label.configure(text=f"{value:.1f}%")
                    bar["value"] = value
            except Exception as exc:
                print(f"Could not read system statistics: {exc}")
        self.clock_label.configure(text=f"Updated: {now_text()}")
        self.root.after(1500, self.update_stats)

    def build_device_tab(self):
        tab = self.device_tab
        self.make_label(tab, "This computer", 18, TEXT, True).pack(
            anchor="w", padx=22, pady=(22, 14)
        )
        panel = tk.Frame(tab, bg=PANEL, padx=18, pady=18)
        panel.pack(fill="x", padx=22, pady=5)

        self.device_status = tk.Label(
            panel, text="", bg=PANEL, fg=RED,
            font=("Segoe UI", 12, "bold")
        )
        self.device_status.pack(anchor="w", pady=(0, 12))
        for title, value in (
            ("Computer name", self.device.get("computer_name", "Unknown")),
            ("Operating system", self.device.get("operating_system", "Unknown")),
            ("Device ID", self.device.get("device_id", "Unknown")),
        ):
            tk.Label(
                panel, text=f"{title}: {value}", bg=PANEL, fg=TEXT,
                justify="left", wraplength=760, font=("Segoe UI", 9)
            ).pack(anchor="w", pady=4)

        self.device_action_button = self.make_button(
            tab, "", self.toggle_registration
        )
        self.device_action_button.pack(anchor="w", padx=22, pady=18)
        self.make_label(
            tab,
            "Registration here is local device bookkeeping only; it does not connect to another computer.",
            9, MUTED
        ).pack(anchor="w", padx=22)
        self.refresh_device_status()

    def refresh_device_status(self):
        is_registered = bool(self.device.get("registered", False))
        self.device_status.configure(
            text="REGISTERED ON THIS APP" if is_registered else "NOT REGISTERED",
            fg="#52d273" if is_registered else RED,
        )
        self.device_action_button.configure(
            text="Revoke registration" if is_registered else "Register this computer"
        )

    def toggle_registration(self):
        if self.device.get("registered", False):
            approved = messagebox.askyesno(
                "Revoke registration",
                "Remove this computer's local registration from CART3R?",
                parent=self.root,
            )
            if not approved:
                return
            self.device["registered"] = False
            event = "Device registration revoked"
            details = "Local registration for this computer was revoked"
        else:
            self.device["registered"] = True
            event = "Device registered"
            details = "This computer was registered locally"

        try:
            save_device(self.device)
        except OSError as exc:
            messagebox.showerror("Save error", str(exc), parent=self.root)
            return
        write_activity(event, details)
        self.refresh_device_status()
        self.refresh_activity()

    def build_activity_tab(self):
        tab = self.activity_tab
        top = tk.Frame(tab, bg=BG)
        top.pack(fill="x", padx=18, pady=(18, 10))
        self.make_label(top, "Activity history", 18, TEXT, True).pack(side="left")
        self.make_button(top, "Refresh", self.refresh_activity).pack(side="right")

        self.make_label(
            tab,
            "Events are stored in cart3r_activity.jsonl beside main.py. Passwords are never recorded.",
            9, MUTED
        ).pack(anchor="w", padx=20, pady=(0, 10))

        table_frame = tk.Frame(tab, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        columns = ("time", "event", "details")
        self.activity_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=12
        )
        self.activity_tree.heading("time", text="Time")
        self.activity_tree.heading("event", text="Event")
        self.activity_tree.heading("details", text="Details")
        self.activity_tree.column("time", width=185, minwidth=150)
        self.activity_tree.column("event", width=180, minwidth=130)
        self.activity_tree.column("details", width=390, minwidth=180)
        scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.activity_tree.yview
        )
        self.activity_tree.configure(yscrollcommand=scroll.set)
        self.activity_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.refresh_activity()

    def refresh_activity(self):
        if not hasattr(self, "activity_tree"):
            return
        for row in self.activity_tree.get_children():
            self.activity_tree.delete(row)
        for item in read_activity():
            self.activity_tree.insert(
                "", "end",
                values=(item.get("time", ""), item.get("event", ""), item.get("details", ""))
            )

    def build_security_tab(self):
        tab = self.security_tab
        self.make_label(tab, "Security settings", 18, TEXT, True).pack(
            anchor="w", padx=22, pady=(22, 12)
        )
        panel = tk.Frame(tab, bg=PANEL, padx=18, pady=18)
        panel.pack(fill="x", padx=22, pady=5)
        tk.Label(
            panel,
            text="CART3R uses a password hash for its local app login. This is basic app-level protection, not a replacement for your Windows account security.",
            bg=PANEL, fg=TEXT, justify="left", wraplength=760,
            font=("Segoe UI", 10)
        ).pack(anchor="w")
        self.make_button(
            tab, "Change password", self.change_password
        ).pack(anchor="w", padx=22, pady=18)

    def change_password(self):
        current = simpledialog.askstring(
            "Current password", "Enter your current CART3R password:",
            show="•", parent=self.root
        )
        if current is None:
            return
        if not verify_password(current):
            messagebox.showerror(
                "Incorrect password", "The current password was not correct.",
                parent=self.root
            )
            return
        new_password = simpledialog.askstring(
            "New password", "Enter a new password (at least 8 characters):",
            show="•", parent=self.root
        )
        if new_password is None:
            return
        if len(new_password) < 8:
            messagebox.showwarning(
                "Password too short", "Use at least 8 characters.", parent=self.root
            )
            return
        confirm = simpledialog.askstring(
            "Confirm password", "Enter the new password again:",
            show="•", parent=self.root
        )
        if confirm is None:
            return
        if new_password != confirm:
            messagebox.showerror(
                "Passwords do not match", "The two new passwords were different.",
                parent=self.root
            )
            return
        try:
            save_password(new_password)
        except OSError as exc:
            messagebox.showerror("Save error", str(exc), parent=self.root)
            return
        write_activity("Password changed", "Local CART3R password updated")
        self.refresh_activity()
        messagebox.showinfo("Password changed", "Your CART3R password was changed.", parent=self.root)

    def logout(self):
        write_activity("Logged out", "User logged out of the local dashboard")
        self.show_auth_screen()

    def close_app(self):
        if self._closing:
            return
        self._closing = True
        # Only log a normal close if the authenticated dashboard is open.
        if hasattr(self, "notebook") and self.notebook.winfo_exists():
            write_activity("Application closed", "CART3R dashboard closed")
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CART3RApp(root)
    root.mainloop()
