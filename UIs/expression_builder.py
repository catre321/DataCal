import tkinter as tk
from tkinter import ttk
from UIs.widgets import FuzzyListbox


class ExpressionBuilderDialog:
    """
    Pop-up dialog for visually constructing formula expressions.

    Features:
        - Data Columns and Created Variables lists side by side
        - Real-time fuzzy search with 300 ms debounce across both lists
        - File-source filter (All / BS / IS / CF)
        - Numeric and operator keypad
        - Click-to-insert variable names into the expression field

    Args:
        root: Parent Tk window.
        available_vars: List of original column names from loaded files.
        column_sources: Dict mapping column name → file type string (e.g. "BS/IS").
        created_vars: List of already-created variable names (available for chaining).
        on_apply: callable(expr: str) called when the user confirms with OK.
    """

    def __init__(self, root, available_vars, column_sources, created_vars, *, on_apply):
        self._root = root
        self._all_data_vars = sorted(available_vars)
        self._column_sources = column_sources
        self._all_created_vars = list(created_vars)
        self._on_apply = on_apply
        self._build()

    def _build(self):
        builder = tk.Toplevel(self._root)
        builder.title("Expression Builder")
        builder.geometry("800x600")

        # Expression input
        tk.Label(builder, text="Expression:").pack(pady=5)
        builder_entry = ttk.Entry(builder, width=80)
        builder_entry.pack(pady=5)

        # File source filter
        tk.Label(builder, text="Lọc biến theo file:").pack()
        combo_filter = ttk.Combobox(builder, values=["All", "BS", "IS", "CF"])
        combo_filter.set("All")
        combo_filter.pack()

        # Two-column variable lists — each has a built-in fuzzy search bar
        frame_columns = ttk.Frame(builder)
        frame_columns.pack(padx=10, pady=5, fill='both', expand=True)

        fuzzy_data = FuzzyListbox(
            frame_columns,
            title="Data Columns",
            items=self._all_data_vars,
            selectmode='single',
            height=12,
        )
        fuzzy_data.pack(side='left', fill='both', expand=True, padx=5)

        fuzzy_created = FuzzyListbox(
            frame_columns,
            title="Created Variables",
            items=self._all_created_vars,
            selectmode='single',
            height=12,
            listbox_bg='#e8f5e9',
        )
        fuzzy_created.pack(side='left', fill='both', expand=True, padx=5)

        def on_filter_change(_event=None):
            fv = combo_filter.get()
            if fv == 'All':
                fuzzy_data.set_extra_filter(None)
            else:
                fuzzy_data.set_extra_filter(
                    lambda col: fv in self._column_sources.get(col, '').split('/')
                )

        combo_filter.bind("<<ComboboxSelected>>", on_filter_change)

        def insert_from_data(_event=None):
            sel = fuzzy_data.get_selection()
            if sel:
                builder_entry.insert(tk.END, sel[0] + ' ')

        def insert_from_created(_event=None):
            sel = fuzzy_created.get_selection()
            if sel:
                builder_entry.insert(tk.END, sel[0] + ' ')

        fuzzy_data.bind_select(insert_from_data)
        fuzzy_created.bind_select(insert_from_created)

        # Operator keypad
        frame_keypad = ttk.Frame(builder)
        frame_keypad.pack(side='right', padx=10, pady=10)

        buttons = [
            '7', '8', '9', '/', '==',
            '4', '5', '6', '*', '>',
            '1', '2', '3', '-', '<',
            '0', '.', '**', '+', '<=',
            '(', ')', '!=', '&', '|',
        ]
        for i in range(0, len(buttons), 5):
            row = ttk.Frame(frame_keypad)
            row.pack()
            for b in buttons[i:i + 5]:
                ttk.Button(
                    row, text=b, width=6,
                    command=lambda x=b: builder_entry.insert(tk.END, x),
                ).pack(side='left')

        def apply():
            expr = builder_entry.get().strip()
            self._on_apply(expr)
            builder.destroy()

        ttk.Button(builder, text="OK", command=apply).pack(pady=10)
