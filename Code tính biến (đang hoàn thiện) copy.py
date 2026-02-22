import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import re
from tkinter import scrolledtext

class FinancialCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Công cụ Tính Toán Biến Tài Chính - Linh hoạt file")
        self.root.geometry("950x750")

        self.df = None
        self.file_paths = {'BS': None, 'IS': None, 'CF': None}
        self.column_sources = {}
        self.id_col = None
        self.time_col = None
        self.group_cols = []
        self.available_vars = []
        self.formulas = []

        self.show_data_input_wizard()

    def show_data_input_wizard(self):
        self.frame_data = ttk.Frame(self.root)
        self.frame_data.pack(pady=20, padx=20, fill='both', expand=True)

        tk.Label(self.frame_data, text="Chọn file (không bắt buộc chọn hết)", font=("Arial", 12)).pack(pady=10)

        for ft in ['BS', 'IS', 'CF']:
            tk.Label(self.frame_data, text=f"File {ft}:").pack(anchor='w')
            btn = ttk.Button(self.frame_data, text=f"Browse {ft}", command=lambda t=ft: self.browse_file(t))
            btn.pack(anchor='w', pady=2)
            lbl = tk.Label(self.frame_data, text="Chưa chọn", fg="gray")
            lbl.pack(anchor='w')
            setattr(self, f"lbl_{ft.lower()}", lbl)

        ttk.Button(self.frame_data, text="Tiếp tục (Next >>)", command=self.load_selected_files).pack(pady=30)

    def browse_file(self, file_type):
        path = filedialog.askopenfilename(filetypes=[("Excel/CSV files", "*.xlsx *.xls *.csv")])
        if path:
            self.file_paths[file_type] = path
            getattr(self, f"lbl_{file_type.lower()}").config(text=path, fg="green")

    def load_selected_files(self):
        selected_files = {k: v for k, v in self.file_paths.items() if v is not None}
        if not selected_files:
            if not messagebox.askyesno("Cảnh báo", "Bạn chưa chọn file nào. Tiếp tục?"):
                return

        try:
            dfs = {}
            for ft, path in selected_files.items():
                if path.endswith('.csv'):
                    df_temp = pd.read_csv(path)
                else:
                    df_temp = pd.read_excel(path)
                dfs[ft] = df_temp

                for col in df_temp.columns:
                    if col not in self.column_sources:
                        self.column_sources[col] = ft
                    else:
                        if ft not in self.column_sources[col]:
                            self.column_sources[col] += f"/{ft}"

            self.df = None
            for df_temp in dfs.values():
                if self.df is None:
                    self.df = df_temp.copy()
                else:
                    self.df = self.df.merge(df_temp, how='outer')

            if self.df is None or self.df.empty:
                messagebox.showerror("Lỗi", "Không đọc được dữ liệu.")
                return

            self.available_vars = list(self.df.columns)
            if self.available_vars:
                self.df = self.df.sort_values(by=self.available_vars[0], ignore_index=True)

            messagebox.showinfo("Thành công", f"Đã đọc {len(selected_files)} file. Số cột: {len(self.available_vars)}")
            self.show_column_selection()

        except Exception as e:
            messagebox.showerror("Lỗi đọc file", str(e))

    def show_column_selection(self, is_adding_group=False):
        self.clear_window()

        tk.Label(self.root, text="Chọn cột định danh" + (" (thêm ID phụ)" if is_adding_group else "")).pack(pady=10)

        tree = ttk.Treeview(self.root, columns=("Column", "From File"), show="headings", height=12)
        tree.heading("Column", text="Tên cột")
        tree.heading("From File", text="Nguồn file")
        tree.column("Column", width=350)
        tree.column("From File", width=150)

        for col in sorted(self.available_vars):
            source = self.column_sources.get(col, 'Unknown')
            tree.insert("", "end", values=(col, source))

        tree.pack(pady=10, padx=10, fill='both', expand=True)

        frame = ttk.Frame(self.root)
        frame.pack(pady=10)

        if not is_adding_group:
            tk.Label(frame, text="ID chính (Firm/ISIN/...):").pack(side='left')
            self.combo_id = ttk.Combobox(frame, values=self.available_vars, width=35)
            self.combo_id.pack(side='left', padx=5)

            tk.Label(frame, text="Thời gian (Year/Date):").pack(side='left')
            self.combo_time = ttk.Combobox(frame, values=self.available_vars, width=35)
            self.combo_time.pack(side='left', padx=5)

            ttk.Button(frame, text="Thêm Biến ID", command=lambda: self.show_column_selection(True)).pack(side='left', padx=10)
            ttk.Button(frame, text="Xác nhận & Hoàn tất", command=self.confirm_and_finish_columns).pack(side='left', padx=10)

        else:
            tk.Label(frame, text="Chọn thêm cột ID phụ (Industry/Country...):").pack()
            self.list_group = tk.Listbox(frame, selectmode="multiple", height=8, width=50)
            for col in sorted(self.available_vars):
                self.list_group.insert(tk.END, col)
            self.list_group.pack(pady=5)

            btn_frame = ttk.Frame(frame)
            btn_frame.pack(pady=10)

            ttk.Button(btn_frame, text="Xác nhận thêm & Quay lại", command=self.confirm_group_cols_and_return).pack(side='left', padx=10)
            ttk.Button(btn_frame, text="Hủy thêm", command=lambda: self.show_column_selection(False)).pack(side='left', padx=10)

    def confirm_and_finish_columns(self):
        self.id_col = self.combo_id.get()
        self.time_col = self.combo_time.get()

        if not self.id_col or not self.time_col:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ID chính và cột thời gian.")
            return

        if self.id_col == self.time_col:
            messagebox.showwarning("Cảnh báo", "ID chính và cột thời gian không nên trùng nhau.")
            return

        self.df = self.df.sort_values([self.id_col, self.time_col])
        messagebox.showinfo("Hoàn tất bước chọn cột", f"ID chính: {self.id_col}\nThời gian: {self.time_col}\nID phụ: {', '.join(self.group_cols) if self.group_cols else 'Không có'}")
        self.show_variable_generator()

    def confirm_group_cols_and_return(self):
        selected = [self.list_group.get(i) for i in self.list_group.curselection()]
        if selected:
            self.group_cols.extend(selected)
            messagebox.showinfo("Đã thêm", f"Đã thêm {len(selected)} cột phụ.")
        self.show_column_selection(False)

    def show_variable_generator(self):
        self.clear_window()

        tk.Label(self.root, text="Generate - Create a new variable", font=("Arial", 12)).pack(pady=10)

        frame_main = ttk.Frame(self.root)
        frame_main.pack(pady=10, padx=20)

        tk.Label(frame_main, text="Variable type:").grid(row=0, column=0, sticky='e', pady=5)
        self.combo_type = ttk.Combobox(frame_main, values=["float", "double", "long", "int", "byte", "str"])
        self.combo_type.set("double")
        self.combo_type.grid(row=0, column=1, sticky='w')

        tk.Label(frame_main, text="Variable name:").grid(row=0, column=2, sticky='e', padx=10)
        self.entry_name = ttk.Entry(frame_main, width=35)
        self.entry_name.grid(row=0, column=3, sticky='w')

        tk.Label(frame_main, text="Expression (hỗ trợ lag riêng: NetSales_lag1, NetSales{2}):").grid(row=1, column=0, columnspan=4, pady=5, sticky='w')

        self.entry_expression = scrolledtext.ScrolledText(frame_main, height=5, width=80, wrap=tk.WORD)
        self.entry_expression.grid(row=2, column=0, columnspan=4, pady=5)

        ttk.Button(frame_main, text="Expression Builder...", command=self.open_expression_builder).grid(row=2, column=4, padx=10, sticky='nw')

        tk.Label(frame_main, text="Gợi ý cú pháp lag:").grid(row=3, column=0, columnspan=4, sticky='w', pady=3)
        tk.Label(frame_main, text="• NetSales_lag1 → NetSales năm t-1", fg="gray").grid(row=4, column=0, columnspan=4, sticky='w', padx=20)
        tk.Label(frame_main, text="• NetSales{2} → NetSales năm t-2", fg="gray").grid(row=5, column=0, columnspan=4, sticky='w', padx=20)

        # Checkbox tính trung bình
        self.var_mean = tk.BooleanVar(value=False)
        tk.Checkbutton(frame_main, text="Tính trung bình theo nhóm (Mean)", variable=self.var_mean, command=self.toggle_mean_options).grid(row=6, column=0, columnspan=4, pady=10, sticky='w')

        ttk.Button(self.root, text="Thêm biến", command=self.add_variable).pack(pady=15)

        tk.Label(self.root, text="Danh sách biến đã thêm:").pack()
        self.formula_list = tk.Listbox(self.root, height=12, width=100)
        self.formula_list.pack(pady=10, padx=10)

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Thực hiện tính toán", command=self.compute_variables).pack(side='left', padx=30)
        ttk.Button(btn_frame, text="Xuất file Excel", command=self.export_file).pack(side='left', padx=30)

    def toggle_mean_options(self):
        if self.var_mean.get():
            self.open_mean_selection_window()

    def open_mean_selection_window(self):
        mean_win = tk.Toplevel(self.root)
        mean_win.title("Tính trung bình theo nhóm")
        mean_win.geometry("600x500")

        tk.Label(mean_win, text="Chọn biến cần tính trung bình:").pack(pady=5)
        self.mean_var_list = tk.Listbox(mean_win, height=8, width=60)
        for col in sorted(self.available_vars):
            self.mean_var_list.insert(tk.END, col)
        self.mean_var_list.pack(pady=5)

        tk.Label(mean_win, text="Chọn cột nhóm (nếu không chọn sẽ dùng ID chính):").pack(pady=5)
        self.mean_group_list = tk.Listbox(mean_win, selectmode="multiple", height=10, width=60)
        for col in sorted(self.available_vars):
            self.mean_group_list.insert(tk.END, col)
        self.mean_group_list.pack(pady=5)

        ttk.Button(mean_win, text="Xác nhận thêm mean", command=lambda: self.add_mean_variable(mean_win)).pack(pady=15)

    def add_mean_variable(self, window):
        try:
            mean_var_idx = self.mean_var_list.curselection()[0]
            mean_var = self.mean_var_list.get(mean_var_idx)
        except IndexError:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn 1 biến cần tính trung bình.")
            return

        mean_groups = [self.mean_group_list.get(i) for i in self.mean_group_list.curselection()]

        # Nếu không chọn nhóm → dùng ID chính
        if not mean_groups:
            if not self.id_col:
                messagebox.showwarning("Cảnh báo", "Chưa có ID chính để dùng mặc định. Hãy chọn nhóm hoặc quay lại chọn ID.")
                return
            mean_groups = [self.id_col]

        name = f"{mean_var}_mean"
        expr = f"mean({mean_var}) by {', '.join(mean_groups)}"

        self.formulas.append({
            'name': name,
            'expression': expr,
            'type': 'mean',
            'mean_var': mean_var,
            'mean_groups': mean_groups
        })

        self.formula_list.insert(tk.END, f"{name} = {expr}")

        window.destroy()

    def open_expression_builder(self):
        builder = tk.Toplevel(self.root)
        builder.title("Expression Builder")
        builder.geometry("700x500")

        tk.Label(builder, text="Expression:").pack(pady=5)
        self.builder_entry = ttk.Entry(builder, width=80)
        self.builder_entry.pack(pady=5)

        tk.Label(builder, text="Lọc biến theo file:").pack()
        self.combo_filter = ttk.Combobox(builder, values=["All", "BS", "IS", "CF"])
        self.combo_filter.set("All")
        self.combo_filter.pack()
        self.combo_filter.bind("<<ComboboxSelected>>", self.update_var_list)

        frame_vars = ttk.Frame(builder)
        frame_vars.pack(side='left', padx=10, pady=10, fill='y')

        tk.Label(frame_vars, text="Variables:").pack()
        self.list_vars = tk.Listbox(frame_vars, height=20, width=30)
        self.update_var_list()
        self.list_vars.pack()
        self.list_vars.bind("<<ListboxSelect>>", self.insert_var_to_expression)

        frame_keypad = ttk.Frame(builder)
        frame_keypad.pack(side='right', padx=10)

        buttons = ['7','8','9','/','==','4','5','6','*','>','1','2','3','-','<','0','.','**','+','<=','(',')','!=','&','|']
        for i in range(0, len(buttons), 5):
            row = ttk.Frame(frame_keypad)
            row.pack()
            for b in buttons[i:i+5]:
                ttk.Button(row, text=b, width=6, command=lambda x=b: self.insert_to_builder(x)).pack(side='left')

        ttk.Button(builder, text="OK", command=lambda: self.apply_expression(builder)).pack(pady=10)

    def update_var_list(self, event=None):
        filter_val = self.combo_filter.get()
        self.list_vars.delete(0, tk.END)
        for col in sorted(self.available_vars):
            source = self.column_sources.get(col, 'Unknown')
            if filter_val == "All" or filter_val in source.split('/'):
                self.list_vars.insert(tk.END, col)

    def insert_var_to_expression(self, event):
        sel = self.list_vars.curselection()
        if sel:
            var = self.list_vars.get(sel[0])
            self.builder_entry.insert(tk.END, var + " ")

    def insert_to_builder(self, text):
        self.builder_entry.insert(tk.END, text)

    def apply_expression(self, builder):
        expr = self.builder_entry.get().strip()
        self.entry_expression.delete(0, tk.END)
        self.entry_expression.insert(0, expr)
        builder.destroy()

    def add_variable(self):
        name = self.entry_name.get().strip()
        expr = self.entry_expression.get().strip()

        if not name or not expr:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên biến và công thức.")
            return

        self.formulas.append({'name': name, 'expression': expr})
        self.formula_list.insert(tk.END, f"{name} = {expr}")

        self.entry_name.delete(0, tk.END)
        self.entry_expression.delete(0, tk.END)

    def compute_variables(self):
        if self.df is None or self.id_col is None or self.time_col is None:
            messagebox.showerror("Lỗi", "Chưa có dữ liệu hoặc chưa chọn cột ID/Thời gian.")
            return

        try:
            # Xử lý các biến mean riêng
            for f in self.formulas:
                if 'type' in f and f['type'] == 'mean':
                    mean_var = f['mean_var']
                    groups = f['mean_groups'] + [self.time_col] if self.time_col not in f['mean_groups'] else f['mean_groups']
                    self.df[f['name']] = self.df.groupby(groups)[mean_var].transform('mean')
                    continue

                expr = f['expression']

                # Xử lý lag riêng từng biến
                lag_pattern = r'(\w+?)(?:_lag(\d+)|{(\d+)})'
                matches = re.findall(lag_pattern, expr)

                for base_var, lag1, lag2 in matches:
                    lag = int(lag1 or lag2)
                    lag_col = f"{base_var}_lag{lag}"
                    if lag_col not in self.df.columns:
                        self.df[lag_col] = self.df.groupby(self.id_col)[base_var].shift(lag)

                # Thay thế trong biểu thức
                def replace_lag(m):
                    var, l1, l2 = m.groups()
                    lag = l1 or l2
                    return f"{var}_lag{lag}"

                expr = re.sub(lag_pattern, replace_lag, expr)

                # Tính toán
                self.df[f['name']] = self.df.eval(expr)

            messagebox.showinfo("Thành công", f"Đã tính {len(self.formulas)} biến mới!")

        except Exception as e:
            messagebox.showerror("Lỗi tính toán", f"{str(e)}\n\nKiểm tra lại công thức và tên biến.")

    def export_file(self):
        if self.df is None:
            messagebox.showerror("Lỗi", "Chưa có dữ liệu để xuất.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")])
        if path:
            try:
                if path.endswith('.csv'):
                    self.df.to_csv(path, index=False, encoding='utf-8-sig')
                else:
                    self.df.to_excel(path, index=False)
                messagebox.showinfo("Thành công", f"Đã xuất file: {path}")
            except Exception as e:
                messagebox.showerror("Lỗi xuất file", str(e))

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    try:
        print("Đang khởi tạo GUI...")
        root = tk.Tk()
        app = FinancialCalculatorApp(root)
        print("GUI khởi tạo thành công. Bắt đầu mainloop...")
        root.mainloop()
    except Exception as e:
        print("LỖI:", str(e))
        import traceback
        traceback.print_exc()