import tkinter as tk
from tkinter import ttk, messagebox
from UIs.widgets import FuzzyListbox


class StdevVariableDialog:
    """
    Dialog for creating a named STDEV.S (sample standard deviation) variable.

    Layout:
        - Editable variable name (auto-filled from selection)
        - Left panel : single-select list of columns to calculate stdev on
        - Right panel: multi-select list of category columns to group by (optional)
        - Live preview of the resulting formula
        - Add Variable / Cancel buttons

    Args:
        root: Parent Tk window.
        available_vars: All column names from loaded files.
        id_col: Default primary ID column (used as fallback group if needed).
        on_apply: callable(name, stdev_var, stdev_groups) called on confirm.
    """

    def __init__(self, root, available_vars, id_col, *, on_apply, initial_values=None):
        self._root = root
        self._available_vars = sorted(available_vars)
        self._id_col = id_col
        self._on_apply = on_apply
        self._initial_values = initial_values or {}
        self._build()

    def _build(self):
        win = tk.Toplevel(self._root)
        win.title("Add STDEV.S Variable")
        win.geometry("680x520")
        win.resizable(False, False)
        win.transient(self._root)
        win.grab_set()

        # ── Variable name ────────────────────────────────────
        name_frame = ttk.LabelFrame(win, text="Variable name", padding=8)
        name_frame.pack(fill='x', padx=15, pady=(12, 5))

        self._name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=self._name_var, width=50)
        name_entry.pack(side='left', padx=5)
        tk.Label(name_frame, text="(auto-filled, editable)", fg="gray").pack(side='left')

        # ── Two-column selector ──────────────────────────────
        panels = ttk.Frame(win)
        panels.pack(fill='both', expand=True, padx=15, pady=5)

        self._fuzzy_var = FuzzyListbox(
            panels,
            title="Variable to calculate  (numeric)",
            items=self._available_vars,
            selectmode='single',
            height=12,
        )
        self._fuzzy_var.pack(side='left', fill='both', expand=True, padx=(0, 8))

        self._fuzzy_groups = FuzzyListbox(
            panels,
            title="Group by  (multi-select — optional, leave empty for ungrouped)",
            items=self._available_vars,
            selectmode='multiple',
            height=12,
        )
        self._fuzzy_groups.pack(side='right', fill='both', expand=True, padx=(8, 0))

        # ── Live preview ─────────────────────────────────────
        preview_frame = ttk.LabelFrame(win, text="Formula preview", padding=6)
        preview_frame.pack(fill='x', padx=15, pady=5)

        self._preview_label = tk.Label(
            preview_frame, text="(select a variable above)",
            fg="gray", anchor='w', font=("Courier", 9),
        )
        self._preview_label.pack(fill='x')

        # ── Buttons ──────────────────────────────────────────
        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Cancel", command=win.destroy).pack(side='left', padx=20)
        ttk.Button(btn_frame, text="Add Variable", command=lambda: self._confirm(win)).pack(side='left', padx=20)

        # Wire up live preview updates
        self._fuzzy_var.bind_select(lambda _: self._update_preview())
        self._fuzzy_groups.bind_select(lambda _: self._update_preview())
        self._name_var.trace_add("write", lambda *_: None)  # keep name editable without overwrite

        # Pre-fill if editing an existing stdev variable
        if self._initial_values:
            self._name_var.set(self._initial_values.get('name', ''))
            pre_var = self._initial_values.get('stdev_var', '')
            pre_groups = self._initial_values.get('stdev_groups', [])
            if pre_var:
                self._fuzzy_var.set_selection([pre_var])
            if pre_groups:
                self._fuzzy_groups.set_selection(pre_groups)
            self._update_preview()

    # ── Helpers ──────────────────────────────────────────────

    def _get_selected_var(self):
        sel = self._fuzzy_var.get_selection()
        return sel[0] if sel else None

    def _get_selected_groups(self):
        return self._fuzzy_groups.get_selection()

    def _update_preview(self):
        """Refresh preview label and auto-fill name field."""
        stdev_var = self._get_selected_var()
        groups = self._get_selected_groups()

        if not stdev_var:
            self._preview_label.config(text="(select a variable above)", fg="gray")
            return

        if groups:
            groups_display = ", ".join(groups)
            preview = f"{stdev_var}_stdev = stdev({stdev_var})  grouped by [{groups_display}]"
        else:
            preview = f"{stdev_var}_stdev = stdev({stdev_var})  [ungrouped]"
        
        self._preview_label.config(text=preview, fg="black")

        # Auto-fill name only if user hasn't typed a custom one
        auto_name = f"{stdev_var}_stdev"
        current = self._name_var.get()
        # Overwrite only if it still looks auto-generated or is empty
        if not current or (current.endswith("_stdev") and current not in (
            f['name'] for f in [] # placeholder – name check happens at confirm
        )):
            self._name_var.set(auto_name)

    def _confirm(self, win):
        name = self._name_var.get().strip()
        stdev_var = self._get_selected_var()
        groups = self._get_selected_groups()

        if not name:
            messagebox.showwarning("Missing name", "Please enter a variable name.", parent=win)
            return
        if not stdev_var:
            messagebox.showwarning("Missing variable", "Please select a variable to calculate stdev on.", parent=win)
            return

        # Groups are optional for ungrouped calculation
        # If empty, pass empty list (will be handled as ungrouped in computation)
        self._on_apply(name, stdev_var, groups)
        win.destroy()
