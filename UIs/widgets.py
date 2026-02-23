import tkinter as tk
from tkinter import ttk
from difflib import SequenceMatcher


class FuzzyListbox(ttk.LabelFrame):
    """
    A labeled frame with a real-time fuzzy search bar and a Listbox.

    Shared across dialogs (ExpressionBuilderDialog, MeanVariableDialog) to
    avoid duplicating search/filter logic.

    Args:
        parent: Parent widget.
        title: LabelFrame title text.
        items: Initial list of item strings to display.
        selectmode: Tkinter selectmode ('single' or 'multiple').
        height: Listbox height in rows.
        listbox_bg: Optional background colour for the listbox.
        debounce_ms: Milliseconds to wait after keystroke before filtering.

    Example:
        lb = FuzzyListbox(frame, title="Columns", items=col_list, selectmode='multiple')
        lb.pack(fill='both', expand=True)
        selected = lb.get_selection()  # ['ICB1', 'Year']
    """

    def __init__(self, parent, *, title, items, selectmode='single',
                 height=12, listbox_bg=None, debounce_ms=300):
        super().__init__(parent, text=title, padding=5)
        self._all_items = list(items)
        self._debounce_ms = debounce_ms
        self._timer = [None]
        self._extra_filter = None

        # Search bar
        search_frame = ttk.Frame(self)
        search_frame.pack(fill='x', pady=(0, 4))
        tk.Label(search_frame, text="Search:").pack(side='left')
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self._search_var)
        search_entry.pack(side='left', fill='x', expand=True, padx=(4, 0))
        search_entry.bind('<KeyRelease>', self._on_key)

        # Listbox + scrollbar
        lb_frame = ttk.Frame(self)
        lb_frame.pack(fill='both', expand=True)
        lb_kwargs = {'height': height, 'selectmode': selectmode, 'exportselection': False}
        if listbox_bg:
            lb_kwargs['bg'] = listbox_bg
        self._listbox = tk.Listbox(lb_frame, **lb_kwargs)
        scrollbar = ttk.Scrollbar(lb_frame, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self._listbox.pack(fill='both', expand=True)

        self._refresh()

    # ── Public API ────────────────────────────────────────────

    def set_items(self, items):
        """Replace the full item list and refresh display."""
        self._all_items = list(items)
        self._refresh()

    def set_extra_filter(self, fn):
        """
        Set an additional filter callable(item) -> bool applied on top of the search.
        Pass None to remove.
        """
        self._extra_filter = fn
        self._refresh()

    def get_selection(self) -> list:
        """Return list of selected item name strings."""
        return [self._listbox.get(i) for i in self._listbox.curselection()]

    def set_selection(self, names):
        """Pre-select items by name. Scrolls to the first match."""
        self._listbox.selection_clear(0, tk.END)
        names_set = set(names)
        first = None
        for i in range(self._listbox.size()):
            if self._listbox.get(i) in names_set:
                self._listbox.selection_set(i)
                if first is None:
                    first = i
        if first is not None:
            self._listbox.see(first)

    def bind_select(self, callback):
        """Bind a callback to the <<ListboxSelect>> event."""
        self._listbox.bind('<<ListboxSelect>>', callback)

    # ── Internals ─────────────────────────────────────────────

    @staticmethod
    def _fuzzy_match(query, text):
        q, t = query.lower(), text.lower()
        if q in t:
            return True
        return SequenceMatcher(None, q, t).ratio() > 0.6

    def _on_key(self, _event=None):
        if self._timer[0] is not None:
            self.after_cancel(self._timer[0])
        self._timer[0] = self.after(self._debounce_ms, self._refresh)

    def _refresh(self):
        query = self._search_var.get().strip()
        selected = set(self.get_selection())  # save before clearing
        self._listbox.delete(0, tk.END)
        for item in self._all_items:
            if query and not self._fuzzy_match(query, item):
                continue
            if self._extra_filter and not self._extra_filter(item):
                continue
            self._listbox.insert(tk.END, item)
        if selected:
            self.set_selection(selected)
