import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from UIs.expression_builder import ExpressionBuilderDialog
from UIs.mean_variable_dialog import MeanVariableDialog
from UIs.stdev_variable_dialog import StdevVariableDialog


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
        tk.Label(frame_main, text="• Math: Ln(Revenue(x)) ** 2, sqrt(Cost(x)), exp(Rate(x))", fg="gray").grid(
            row=6, column=0, columnspan=4, sticky='w', padx=20,
        )
        tk.Label(frame_main, text="• Util: abs(), round() | Log: log() [natural log/ln], Ln(), log10(), log2() | Exp: exp()", fg="gray").grid(
            row=7, column=0, columnspan=4, sticky='w', padx=20,
        )
        tk.Label(frame_main, text="• Trig: sin(), cos(), tan(), pow(x,y) | Conditional: IF(cond, true, false)", fg="gray").grid(
            row=8, column=0, columnspan=4, sticky='w', padx=20,
        )
        # Action buttons row
        action_frame = ttk.Frame(self.root)
        action_frame.pack(pady=15)
        ttk.Button(action_frame, text="Thêm biến", command=self._add_variable).pack(side='left', padx=10)
        ttk.Button(action_frame, text="Add Mean Variable...", command=self._open_mean_dialog).pack(side='left', padx=10)
        ttk.Button(action_frame, text="Add STDEV.S Variable...", command=self._open_stdev_dialog).pack(side='left', padx=10)

        # Created variables section
        tk.Label(self.root, text="Các biến đã tạo (Available for chaining):", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        self.created_vars_text = tk.Label(self.root, text="(None yet)", fg="gray", wraplength=700)
        self.created_vars_text.pack(pady=5)

        # Formula list
        tk.Label(self.root, text="Danh sách biến đã thêm:").pack(pady=(10, 5))
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
        
        # Update created variables display
        self._update_created_vars_display()

        self.entry_name.delete(0, tk.END)
        self.entry_expression.delete("1.0", tk.END)

    def _update_created_vars_display(self):
        """Update the display of created variables."""
        created_names = [f['name'] for f in self.model.formulas]
        if created_names:
            display_text = ", ".join(created_names)
            self.created_vars_text.config(text=display_text, fg="black")
        else:
            self.created_vars_text.config(text="(None yet)", fg="gray")

    def _edit_variable(self):
        """Edit selected variable from list."""
        try:
            idx = self.formula_list.curselection()[0]
        except IndexError:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn biến để sửa.")
            return

        formula = self.model.formulas[idx]

        if formula.get('type') == 'mean':
            # Remove and re-open mean dialog pre-filled; re-insert at same position on confirm
            self.formula_list.delete(idx)
            self.model.formulas.pop(idx)
            self._update_created_vars_display()

            def on_apply(name, mean_var, mean_groups):
                expr = f"mean({mean_var}) by {', '.join(mean_groups)}"
                new_formula = {
                    'name': name,
                    'expression': expr,
                    'type': 'mean',
                    'mean_var': mean_var,
                    'mean_groups': mean_groups,
                }
                self.model.formulas.insert(idx, new_formula)
                self.formula_list.insert(idx, f"{name} = {expr}")
                self._update_created_vars_display()

            MeanVariableDialog(
                self.root,
                self.model.available_vars,
                self.model.id_col,
                on_apply=on_apply,
                initial_values=formula,
            )
            return

        if formula.get('type') == 'stdev':
            # Remove and re-open stdev dialog pre-filled; re-insert at same position on confirm
            self.formula_list.delete(idx)
            self.model.formulas.pop(idx)
            self._update_created_vars_display()

            def on_apply(name, stdev_var, stdev_groups):
                if stdev_groups:
                    expr = f"stdev({stdev_var}) by {', '.join(stdev_groups)}"
                else:
                    expr = f"stdev({stdev_var})"
                
                new_formula = {
                    'name': name,
                    'expression': expr,
                    'type': 'stdev',
                    'stdev_var': stdev_var,
                    'stdev_groups': stdev_groups,
                }
                self.model.formulas.insert(idx, new_formula)
                self.formula_list.insert(idx, f"{name} = {expr}")
                self._update_created_vars_display()

            StdevVariableDialog(
                self.root,
                self.model.available_vars,
                self.model.id_col,
                on_apply=on_apply,
                initial_values=formula,
            )
            return

        # Regular formula – load into text fields
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, formula['name'])

        self.entry_expression.delete("1.0", tk.END)
        self.entry_expression.insert("1.0", formula['expression'])

        # Remove from list and model (re-added when user presses 'Thêm biến')
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
            self._update_created_vars_display()
            messagebox.showinfo("Thành công", f"Đã xóa biến '{formula_name}'.")

    # ── Mean ─────────────────────────────────────────────────

    def _open_mean_dialog(self):
        def on_apply(name, mean_var, mean_groups):
            expr = f"mean({mean_var}) by {', '.join(mean_groups)}"
            self.model.formulas.append({
                'name': name,
                'expression': expr,
                'type': 'mean',
                'mean_var': mean_var,
                'mean_groups': mean_groups,
            })
            self.formula_list.insert(tk.END, f"{name} = {expr}")
            self._update_created_vars_display()

        MeanVariableDialog(
            self.root,
            self.model.available_vars,
            self.model.id_col,
            on_apply=on_apply,
        )

    # ── STDEV.S ──────────────────────────────────────────────

    def _open_stdev_dialog(self):
        def on_apply(name, stdev_var, stdev_groups):
            if stdev_groups:
                expr = f"stdev({stdev_var}) by {', '.join(stdev_groups)}"
            else:
                expr = f"stdev({stdev_var})"
            
            self.model.formulas.append({
                'name': name,
                'expression': expr,
                'type': 'stdev',
                'stdev_var': stdev_var,
                'stdev_groups': stdev_groups,
            })
            self.formula_list.insert(tk.END, f"{name} = {expr}")
            self._update_created_vars_display()

        StdevVariableDialog(
            self.root,
            self.model.available_vars,
            self.model.id_col,
            on_apply=on_apply,
        )

    # ── Expression Builder ───────────────────────────────────

    def _open_expression_builder(self):
        def on_apply(expr):
            self.entry_expression.delete("1.0", tk.END)
            self.entry_expression.insert("1.0", expr)

        ExpressionBuilderDialog(
            self.root,
            self.model.available_vars,
            self.model.column_sources,
            [f['name'] for f in self.model.formulas],
            on_apply=on_apply,
        )
