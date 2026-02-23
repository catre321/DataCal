import tkinter as tk
from tkinter import messagebox
import traceback

from logics.data_model import DataModel
from logics.file_handler import load_individual_files, export_to_file
from logics.computation import compute_variables

from UIs.data_input_wizard import DataInputWizard
from UIs.column_selection import ColumnSelection
from UIs.variable_generator import VariableGenerator
from UIs.progress_dialog import ProgressDialog


class FinancialCalculatorApp:
    """Main application controller that manages navigation between views."""

    def __init__(self, root):
        self.root = root
        self.root.title("Công cụ Tính Toán Biến Tài Chính - Linh hoạt file")
        self.root.geometry("1050x950")

        self.model = DataModel()

        self.show_data_input_wizard()

    # ── Navigation ──────────────────────────────────────────

    def show_data_input_wizard(self):
        self._clear_window()
        DataInputWizard(self.root, self.model, on_next=self._on_files_loaded)

    def _on_files_loaded(self):
        """Called after files are selected – load them with a progress dialog."""
        def run(progress_cb):
            return load_individual_files(self.model.file_paths, progress_callback=progress_cb)

        def on_success(result):
            dfs_by_type, col_sources, avail_vars = result
            self.model.dfs_by_type = dfs_by_type
            self.model.column_sources = col_sources
            self.model.available_vars = avail_vars
            messagebox.showinfo(
                "Thành công",
                f"Đã đọc {len(dfs_by_type)} file. Số cột: {len(avail_vars)}",
            )
            self.show_column_selection()

        def on_error(err):
            print(f"[ERROR] File load failed: {err}")
            if "Không có file" in err:
                messagebox.showerror("Lỗi", err)
            else:
                messagebox.showerror("Lỗi đọc file", err)

        ProgressDialog(self.root, "Đang tải file...", "Đang tải file...", "File").run(
            run, on_success=on_success, on_error=on_error
        )

    def show_column_selection(self, is_adding_group=False):
        self._clear_window()
        ColumnSelection(
            self.root,
            self.model,
            is_adding_group=is_adding_group,
            on_finish=self.show_variable_generator,
            on_add_group=lambda: self.show_column_selection(True),
            on_cancel_group=lambda: self.show_column_selection(False),
        )

    def show_variable_generator(self):
        self._clear_window()
        VariableGenerator(
            self.root,
            self.model,
            on_compute=self._on_compute,
            on_export=self._on_export,
        )

    # ── Logic callbacks ─────────────────────────────────────

    def _on_compute(self):
        if self.model.df is None or not self.model.id_col or not self.model.time_col:
            messagebox.showerror("Lỗi", "Chưa có dữ liệu hoặc chưa chọn cột ID/Thời gian.")
            return

        def run(progress_cb):
            return compute_variables(
                self.model.df,
                self.model.formulas,
                self.model.id_col,
                self.model.time_col,
                progress_callback=progress_cb,
            )

        def on_success(df):
            self.model.calculated_df = df
            messagebox.showinfo("Thành công", f"Đã tính {len(self.model.formulas)} biến mới!")

        def on_error(err):
            print(f"[ERROR] Computation failed: {err}")
            messagebox.showerror("Lỗi tính toán", f"{err}\n\nKiểm tra lại công thức và tên biến.")

        ProgressDialog(self.root, "Đang tính toán...", "Đang tính toán biến...", "Công thức").run(
            run, on_success=on_success, on_error=on_error
        )

    def _on_export(self):
        if self.model.calculated_df is None:
            messagebox.showerror("Lỗi", "Chưa có dữ liệu tính toán để xuất. Vui lòng tính toán trước.")
            return

        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if path:
            try:
                export_to_file(
                    self.model.calculated_df,
                    path,
                    formulas=self.model.formulas,
                    source_df=self.model.df,
                )
                messagebox.showinfo("Thành công", f"Đã xuất file: {path}")
            except Exception as e:
                messagebox.showerror("Lỗi xuất file", str(e))

    # ── Helpers ──────────────────────────────────────────────

    def _clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
