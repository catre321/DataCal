import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext


class VariableGenerator:
    """Third screen – create variables, expression builder, mean, compute & export."""

    def __init__(self, root, model, *, on_compute, on_export):
        self.root = root
        self.model = model
        self.on_compute = on_compute
        self.on_export = on_export

        self._build_ui()

    # ── Main layout ──────────────────────────────────────────

    def _build_ui(self):
        tk.Label(
            self.root,
            text="Generate - Create a new variable",
            font=("Arial", 12),
        ).pack(pady=10)

        frame_main = ttk.Frame(self.root)
        frame_main.pack(pady=10, padx=20)

        # Type & name
        tk.Label(frame_main, text="Variable type:").grid(row=0, column=0, sticky='e', pady=5)
        self.combo_type = ttk.Combobox(
            frame_main,
            values=["float", "double", "long", "int", "byte", "str"],
        )
        self.combo_type.set("double")
        self.combo_type.grid(row=0, column=1, sticky='w')

        tk.Label(frame_main, text="Variable name:").grid(row=0, column=2, sticky='e', padx=10)
        self.entry_name = ttk.Entry(frame_main, width=35)
        self.entry_name.grid(row=0, column=3, sticky='w')

        # Expression
        tk.Label(
            frame_main,
            text="Expression (Excel-like or row-by-row with Column(x) syntax):",
        ).grid(row=1, column=0, columnspan=4, pady=5, sticky='w')

        self.entry_expression = scrolledtext.ScrolledText(
            frame_main, height=5, width=80, wrap=tk.WORD,
        )
        self.entry_expression.grid(row=2, column=0, columnspan=4, pady=5)

        ttk.Button(
            frame_main,
            text="Expression Builder...",
            command=self._open_expression_builder,
        ).grid(row=2, column=4, padx=10, sticky='nw')

        # Syntax hints
        tk.Label(frame_main, text="Example formulas:").grid(
            row=3, column=0, columnspan=4, sticky='w', pady=3,
        )
        tk.Label(frame_main, text="• Regular: Revenue - COGS", fg="gray").grid(
            row=4, column=0, columnspan=4, sticky='w', padx=20,
        )
        tk.Label(frame_main, text="• Row-by-row: IF(A(x+1) == A(x), B(x), 0)  [A(x) = current row]", fg="gray").grid(
            row=5, column=0, columnspan=4, sticky='w', padx=20,
        )
        tk.Label(frame_main, text="• Math: log(Revenue(x)) ** 2, sqrt(Cost(x)), exp(Rate(x))", fg="gray").grid(
            row=6, column=0, columnspan=4, sticky='w', padx=20,
        )
        tk.Label(frame_main, text="• Functions: abs(), round(), sin(), cos(), log(), log10(), log2()", fg="gray").grid(
            row=7, column=0, columnspan=4, sticky='w', padx=20,
        )
        # Mean checkbox
        self.var_mean = tk.BooleanVar(value=False)
        tk.Checkbutton(
            frame_main,
            text="Tính trung bình theo nhóm (Mean)",
            variable=self.var_mean,
            command=self._toggle_mean,
        ).grid(row=8, column=0, columnspan=4, pady=10, sticky='w')

        # Add variable button
        ttk.Button(self.root, text="Thêm biến", command=self._add_variable).pack(pady=15)

        # Formula list
        tk.Label(self.root, text="Danh sách biến đã thêm:").pack()
        self.formula_list = tk.Listbox(self.root, height=12, width=100)
        self.formula_list.pack(pady=10, padx=10)

        # Edit and Remove buttons for formula list
        list_btn_frame = ttk.Frame(self.root)
        list_btn_frame.pack(pady=5)
        ttk.Button(list_btn_frame, text="Sửa biến", command=self._edit_variable).pack(side='left', padx=10)
        ttk.Button(list_btn_frame, text="Xóa biến", command=self._remove_variable).pack(side='left', padx=10)

        # Bottom buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Thực hiện tính toán", command=self.on_compute).pack(side='left', padx=30)
        ttk.Button(btn_frame, text="Xuất file Excel", command=self.on_export).pack(side='left', padx=30)

    # ── Add variable ─────────────────────────────────────────

    def _add_variable(self):
        name = self.entry_name.get().strip()
        expr = self.entry_expression.get("1.0", tk.END).strip()

        if not name or not expr:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên biến và công thức.")
            return

        self.model.formulas.append({'name': name, 'expression': expr})
        self.formula_list.insert(tk.END, f"{name} = {expr}")

        self.entry_name.delete(0, tk.END)
        self.entry_expression.delete("1.0", tk.END)

    def _edit_variable(self):
        """Edit selected variable from list."""
        try:
            idx = self.formula_list.curselection()[0]
        except IndexError:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn biến để sửa.")
            return

        formula = self.model.formulas[idx]
        
        # Load formula into input fields
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, formula['name'])
        
        self.entry_expression.delete("1.0", tk.END)
        self.entry_expression.insert("1.0", formula['expression'])
        
        # Remove from list and model (will be re-added with "Thêm biến" button)
        self.formula_list.delete(idx)
        self.model.formulas.pop(idx)
        
        messagebox.showinfo("Thông tin", "Công thức đã tải vào trường nhập liệu. Chỉnh sửa và nhấn 'Thêm biến' để cập nhật.")

    def _remove_variable(self):
        """Remove selected variable from list."""
        try:
            idx = self.formula_list.curselection()[0]
        except IndexError:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn biến để xóa.")
            return

        # Confirm deletion
        formula_name = self.model.formulas[idx]['name']
        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa biến '{formula_name}'?"
        )
        
        if confirm:
            self.formula_list.delete(idx)
            self.model.formulas.pop(idx)
            messagebox.showinfo("Thành công", f"Đã xóa biến '{formula_name}'.")

    # ── Mean ─────────────────────────────────────────────────

    def _toggle_mean(self):
        if self.var_mean.get():
            self._open_mean_window()

    def _open_mean_window(self):
        win = tk.Toplevel(self.root)
        win.title("Tính trung bình theo nhóm")
        win.geometry("600x500")

        tk.Label(win, text="Chọn biến cần tính trung bình:").pack(pady=5)
        mean_var_list = tk.Listbox(win, height=8, width=60)
        for col in sorted(self.model.available_vars):
            mean_var_list.insert(tk.END, col)
        mean_var_list.pack(pady=5)

        tk.Label(win, text="Chọn cột nhóm (nếu không chọn sẽ dùng ID chính):").pack(pady=5)
        mean_group_list = tk.Listbox(win, selectmode="multiple", height=10, width=60)
        for col in sorted(self.model.available_vars):
            mean_group_list.insert(tk.END, col)
        mean_group_list.pack(pady=5)

        ttk.Button(
            win,
            text="Xác nhận thêm mean",
            command=lambda: self._add_mean(win, mean_var_list, mean_group_list),
        ).pack(pady=15)

    def _add_mean(self, window, mean_var_list, mean_group_list):
        try:
            idx = mean_var_list.curselection()[0]
            mean_var = mean_var_list.get(idx)
        except IndexError:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn 1 biến cần tính trung bình.")
            return

        mean_groups = [mean_group_list.get(i) for i in mean_group_list.curselection()]

        if not mean_groups:
            if not self.model.id_col:
                messagebox.showwarning(
                    "Cảnh báo",
                    "Chưa có ID chính để dùng mặc định. Hãy chọn nhóm hoặc quay lại chọn ID.",
                )
                return
            mean_groups = [self.model.id_col]

        name = f"{mean_var}_mean"
        expr = f"mean({mean_var}) by {', '.join(mean_groups)}"

        self.model.formulas.append({
            'name': name,
            'expression': expr,
            'type': 'mean',
            'mean_var': mean_var,
            'mean_groups': mean_groups,
        })
        self.formula_list.insert(tk.END, f"{name} = {expr}")
        window.destroy()

    # ── Expression Builder ───────────────────────────────────

    def _open_expression_builder(self):
        builder = tk.Toplevel(self.root)
        builder.title("Expression Builder")
        builder.geometry("700x500")

        tk.Label(builder, text="Expression:").pack(pady=5)
        builder_entry = ttk.Entry(builder, width=80)
        builder_entry.pack(pady=5)

        tk.Label(builder, text="Lọc biến theo file:").pack()
        combo_filter = ttk.Combobox(builder, values=["All", "BS", "IS", "CF"])
        combo_filter.set("All")
        combo_filter.pack()

        frame_vars = ttk.Frame(builder)
        frame_vars.pack(side='left', padx=10, pady=10, fill='y')

        tk.Label(frame_vars, text="Variables:").pack()
        list_vars = tk.Listbox(frame_vars, height=20, width=30)
        list_vars.pack()

        def update_var_list(_event=None):
            filter_val = combo_filter.get()
            list_vars.delete(0, tk.END)
            for col in sorted(self.model.available_vars):
                source = self.model.column_sources.get(col, 'Unknown')
                if filter_val == "All" or filter_val in source.split('/'):
                    list_vars.insert(tk.END, col)

        update_var_list()
        combo_filter.bind("<<ComboboxSelected>>", update_var_list)

        def insert_var(_event):
            sel = list_vars.curselection()
            if sel:
                builder_entry.insert(tk.END, list_vars.get(sel[0]) + " ")

        list_vars.bind("<<ListboxSelect>>", insert_var)

        # Keypad
        frame_keypad = ttk.Frame(builder)
        frame_keypad.pack(side='right', padx=10)

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
            self.entry_expression.delete("1.0", tk.END)
            self.entry_expression.insert("1.0", expr)
            builder.destroy()

        ttk.Button(builder, text="OK", command=apply).pack(pady=10)
