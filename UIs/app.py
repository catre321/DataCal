import tkinter as tk
from tkinter import ttk, messagebox
import threading

from logics.data_model import DataModel
from logics.file_handler import load_individual_files, export_to_file
from logics.computation import compute_variables

from UIs.data_input_wizard import DataInputWizard
from UIs.column_selection import ColumnSelection
from UIs.variable_generator import VariableGenerator


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
        """Called after files are selected – load them with progress dialog in separate thread."""
        # Create loading dialog
        loading_dialog = tk.Toplevel(self.root)
        loading_dialog.title("Đang tải file...")
        loading_dialog.geometry("400x150")
        loading_dialog.resizable(False, False)
        
        # Center dialog
        loading_dialog.transient(self.root)
        loading_dialog.grab_set()
        
        # Labels
        tk.Label(loading_dialog, text="Đang tải file...", font=("Arial", 12, "bold")).pack(pady=10)
        
        file_label = tk.Label(loading_dialog, text="File: ", fg="blue")
        file_label.pack(pady=5)
        
        progress_label = tk.Label(loading_dialog, text="", fg="gray")
        progress_label.pack(pady=5)
        
        # Progress bar
        progress_bar = ttk.Progressbar(
            loading_dialog, 
            mode='determinate', 
            length=300
        )
        progress_bar.pack(pady=10, padx=20)
        
        # Storage for results
        load_results = {'success': False, 'error': None, 'data': None}
        
        def load_in_background():
            """Load files in background thread without blocking UI."""
            try:
                def update_progress(current_idx, total, filename):
                    # Schedule UI update on main thread
                    self.root.after(0, lambda: update_ui(current_idx, total, filename))
                
                dfs_by_type, col_sources, avail_vars = load_individual_files(
                    self.model.file_paths, 
                    progress_callback=update_progress
                )
                load_results['success'] = True
                load_results['data'] = (dfs_by_type, col_sources, avail_vars)
            except Exception as e:
                load_results['error'] = str(e)
            
            # Close dialog on main thread
            self.root.after(0, lambda: finish_loading())
        
        def update_ui(current_idx, total, filename):
            """Update UI elements (called on main thread)."""
            if loading_dialog.winfo_exists():
                file_label.config(text=f"File: {filename}")
                progress_label.config(text=f"Tiến độ: {current_idx}/{total}")
                progress_bar['value'] = (current_idx / total) * 100
        
        def finish_loading():
            """Called when loading completes."""
            if loading_dialog.winfo_exists():
                loading_dialog.destroy()
            
            if load_results['success']:
                dfs_by_type, col_sources, avail_vars = load_results['data']
                self.model.dfs_by_type = dfs_by_type
                self.model.column_sources = col_sources
                self.model.available_vars = avail_vars
                
                selected_count = len(dfs_by_type)
                messagebox.showinfo(
                    "Thành công",
                    f"Đã đọc {selected_count} file. Số cột: {len(avail_vars)}",
                )
                self.show_column_selection()
            else:
                error_msg = load_results['error']
                if "Không có file" in error_msg:
                    messagebox.showerror("Lỗi", error_msg)
                else:
                    messagebox.showerror("Lỗi đọc file", error_msg)
        
        # Start loading in background thread
        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

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

        # Create progress dialog
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("Đang tính toán...")
        progress_dialog.geometry("400x150")
        progress_dialog.resizable(False, False)
        
        # Center dialog
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        # Labels
        tk.Label(progress_dialog, text="Đang tính toán biến...", font=("Arial", 12, "bold")).pack(pady=10)
        
        formula_label = tk.Label(progress_dialog, text="Công thức: ", fg="blue")
        formula_label.pack(pady=5)
        
        progress_label = tk.Label(progress_dialog, text="", fg="gray")
        progress_label.pack(pady=5)
        
        # Progress bar
        progress_bar = ttk.Progressbar(
            progress_dialog, 
            mode='determinate', 
            length=300
        )
        progress_bar.pack(pady=10, padx=20)
        
        # Storage for results
        compute_results = {'success': False, 'error': None, 'df': None}
        
        def compute_in_background():
            """Compute formulas in background with parallel processing."""
            try:
                def progress_callback(current_idx, total, formula_name):
                    # Schedule UI update on main thread
                    self.root.after(0, lambda: update_ui(current_idx, total, formula_name))
                
                calculated_df = compute_variables(
                    self.model.df,
                    self.model.formulas,
                    self.model.id_col,
                    self.model.time_col,
                    progress_callback=progress_callback
                )
                compute_results['success'] = True
                compute_results['df'] = calculated_df
            except Exception as e:
                compute_results['error'] = str(e)
            
            # Close dialog on main thread
            self.root.after(0, lambda: finish_compute())
        
        def update_ui(current_idx, total, formula_name):
            """Update UI elements (called on main thread)."""
            if progress_dialog.winfo_exists():
                formula_label.config(text=f"Công thức: {formula_name}")
                progress_label.config(text=f"Tiến độ: {current_idx}/{total}")
                progress_bar['value'] = (current_idx / total) * 100
        
        def finish_compute():
            """Called when computation completes."""
            if progress_dialog.winfo_exists():
                progress_dialog.destroy()
            
            if compute_results['success']:
                self.model.calculated_df = compute_results['df']
                messagebox.showinfo("Thành công", f"Đã tính {len(self.model.formulas)} biến mới!")
            else:
                error_msg = compute_results['error']
                messagebox.showerror(
                    "Lỗi tính toán",
                    f"{error_msg}\n\nKiểm tra lại công thức và tên biến.",
                )
        
        # Start computation in background thread
        thread = threading.Thread(target=compute_in_background, daemon=True)
        thread.start()

    def _on_export(self):
        if self.model.calculated_df is None:
            messagebox.showerror("Lỗi", "Chưa có dữ liệu tính toán để xuất. Vui lòng tính toán trước.")
            return

        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
        )
        if path:
            try:
                export_to_file(self.model.calculated_df, path)
                messagebox.showinfo("Thành công", f"Đã xuất file: {path}")
            except Exception as e:
                messagebox.showerror("Lỗi xuất file", str(e))

    # ── Helpers ──────────────────────────────────────────────

    def _clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
