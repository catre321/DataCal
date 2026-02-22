import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from logics.file_handler import merge_files_on_keys, export_to_file


class ColumnSelection:
    """Second screen – choose ID, time, and optional group columns."""

    def __init__(self, root, model, *, is_adding_group, on_finish, on_add_group, on_cancel_group):
        self.root = root
        self.model = model
        self.is_adding_group = is_adding_group
        self.on_finish = on_finish
        self.on_add_group = on_add_group
        self.on_cancel_group = on_cancel_group

        self._build_ui()

    def _build_ui(self):
        title = "Chọn cột định danh"
        if self.is_adding_group:
            title += " (thêm ID phụ)"

        tk.Label(self.root, text=title).pack(pady=10)

        # Column tree
        tree = ttk.Treeview(
            self.root,
            columns=("Column", "From File"),
            show="headings",
            height=12,
        )
        tree.heading("Column", text="Tên cột")
        tree.heading("From File", text="Nguồn file")
        tree.column("Column", width=350)
        tree.column("From File", width=150)

        for col in sorted(self.model.available_vars):
            source = self.model.column_sources.get(col, 'Unknown')
            tree.insert("", "end", values=(col, source))

        tree.pack(pady=10, padx=10, fill='both', expand=True)

        frame = ttk.Frame(self.root)
        frame.pack(pady=10)

        if not self.is_adding_group:
            self._build_main_selection(frame)
        else:
            self._build_group_selection(frame)

    def _build_main_selection(self, frame):
        tk.Label(frame, text="ID chính (Firm/ISIN/...):").pack(side='left')
        self.combo_id = ttk.Combobox(frame, values=self.model.available_vars, width=35)
        self.combo_id.pack(side='left', padx=5)

        tk.Label(frame, text="Thời gian (Year/Date):").pack(side='left')
        self.combo_time = ttk.Combobox(frame, values=self.model.available_vars, width=35)
        self.combo_time.pack(side='left', padx=5)

        ttk.Button(frame, text="Kiểm tra Năm Liên Tục", command=self._check_continuous_years).pack(side='left', padx=10)
        ttk.Button(frame, text="Xác nhận & Hoàn tất (Merge)", command=self._confirm).pack(side='left', padx=10)

    def _build_group_selection(self, frame):
        tk.Label(frame, text="Chọn thêm cột ID phụ (Industry/Country...):").pack()
        self.list_group = tk.Listbox(frame, selectmode="multiple", height=8, width=50)
        for col in sorted(self.model.available_vars):
            self.list_group.insert(tk.END, col)
        self.list_group.pack(pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Xác nhận thêm & Quay lại", command=self._confirm_group).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Hủy thêm", command=self.on_cancel_group).pack(side='left', padx=10)

    def _confirm(self):
        id_col = self.combo_id.get()
        time_col = self.combo_time.get()

        if not id_col or not time_col:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ID chính và cột thời gian.")
            return

        if id_col == time_col:
            messagebox.showwarning("Cảnh báo", "ID chính và cột thời gian không nên trùng nhau.")
            return

        self.model.id_col = id_col
        self.model.time_col = time_col

        # Merge all files on ID and time columns (skip if already merged from check)
        try:
            if self.model.df is None:
                merged_df = merge_files_on_keys(self.model.dfs_by_type, id_col, time_col)
                self.model.df = merged_df
        except Exception as e:
            messagebox.showerror("Lỗi merge file", f"{str(e)}")
            return

        group_text = ', '.join(self.model.group_cols) if self.model.group_cols else 'Không có'
        messagebox.showinfo(
            "Hoàn tát bước chọn cột",
            f"ID chính: {id_col}\nThời gian: {time_col}\nID phụ: {group_text}\n\nĐã merge các file trên ID + Year.",
        )

        # Ask user if they want to export merged data
        if messagebox.askyesno("Xuất dữ liệu", "Xuất dữ liệu merge vào Excel?"):
            try:
                output_path = Path.cwd() / "merge_output.xlsx"
                export_to_file(self.model.df, str(output_path))
                messagebox.showinfo("Thành công", f"Đã xuất: {output_path}")
            except Exception as e:
                messagebox.showerror("Lỗi xuất file", str(e))

        self.on_finish()

    def _check_continuous_years(self):
        """Check if each ID has continuous years (no gaps)."""
        id_col = self.combo_id.get()
        time_col = self.combo_time.get()

        if not id_col or not time_col:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ID chính và cột thời gian trước.")
            return

        # Merge files temporarily to check (store in model for reuse)
        try:
            merged_df = merge_files_on_keys(self.model.dfs_by_type, id_col, time_col)
            # Store merged df to avoid merging again in _confirm()
            self.model.df = merged_df
        except Exception as e:
            messagebox.showerror("Lỗi merge", str(e))
            return

        # Check continuous years by ID
        results = {}
        has_gaps = False

        for entity_id, group in merged_df.groupby(id_col):
            years = sorted(group[time_col].dropna().unique())
            
            if len(years) == 0:
                results[entity_id] = {'years': [], 'continuous': False, 'gap_info': 'Không có dữ liệu'}
                has_gaps = True
                continue

            # Check for gaps
            years_list = sorted([int(y) if isinstance(y, (int, float)) else y for y in years])
            is_continuous = True
            gaps = []

            if isinstance(years_list[0], int):
                for i in range(len(years_list) - 1):
                    if years_list[i + 1] - years_list[i] != 1:
                        is_continuous = False
                        gaps.append(f"{years_list[i]} → {years_list[i + 1]}")

            status = "✓ Liên tục" if is_continuous else "✗ Có khoảng trống"
            gap_info = ', '.join(gaps) if gaps else "Không"
            
            results[entity_id] = {
                'years': years_list,
                'continuous': is_continuous,
                'gap_info': gap_info
            }
            
            if not is_continuous:
                has_gaps = True

        # Show results in dialog
        self._show_continuous_years_report(results, has_gaps)

    def _show_continuous_years_report(self, results, has_gaps):
        """Display continuous years check results."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Kiểm tra Năm Liên Tục")
        dialog.geometry("600x500")

        # Summary
        total = len(results)
        continuous = sum(1 for r in results.values() if r['continuous'])
        gaps = total - continuous

        summary_text = f"Tổng cộng: {total} ID | Liên tục: {continuous} | Có khoảng trống: {gaps}"
        tk.Label(
            dialog, text=summary_text, font=("Arial", 11, "bold"),
            fg="green" if gaps == 0 else "red"
        ).pack(pady=10)

        # Results list
        frame_text = ttk.Frame(dialog)
        frame_text.pack(fill='both', expand=True, padx=10, pady=10)

        text_widget = scrolledtext.ScrolledText(frame_text, height=20, width=70, wrap=tk.WORD)
        text_widget.pack(fill='both', expand=True)

        # Configure tags for styling
        text_widget.tag_config("header", font=("Arial", 10, "bold"))
        text_widget.tag_config("continuous", foreground="green")
        text_widget.tag_config("gap", foreground="red")

        # Display results
        for entity_id in sorted(results.keys()):
            result = results[entity_id]
            status = "✓" if result['continuous'] else "✗"
            tag = "continuous" if result['continuous'] else "gap"
            
            years_str = "-".join(str(y) for y in result['years'][:5])
            if len(result['years']) > 5:
                years_str += f"... ({len(result['years'])} năm)"
            
            text_widget.insert(tk.END, f"{status} {entity_id}\n", tag)
            text_widget.insert(tk.END, f"   Năm: {years_str}\n")
            text_widget.insert(tk.END, f"   Khoảng trống: {result['gap_info']}\n\n")

        text_widget.config(state='disabled')

        # Close button
        ttk.Button(dialog, text="Đóng", command=dialog.destroy).pack(pady=10)

    def _confirm_group(self):
        selected = [self.list_group.get(i) for i in self.list_group.curselection()]
        if selected:
            self.model.group_cols.extend(selected)
            messagebox.showinfo("Đã thêm", f"Đã thêm {len(selected)} cột phụ.")
        self.on_cancel_group()
