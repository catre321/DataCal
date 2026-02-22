import tkinter as tk
from tkinter import ttk, filedialog


class DataInputWizard:
    """First screen – file selection for BS / IS / CF."""

    def __init__(self, root, model, on_next):
        self.root = root
        self.model = model
        self.on_next = on_next

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root)
        frame.pack(pady=20, padx=20, fill='both', expand=True)

        tk.Label(
            frame,
            text="Chọn file (không bắt buộc chọn hết)",
            font=("Arial", 12),
        ).pack(pady=10)

        self._labels = {}
        for ft in ['BS', 'IS', 'CF']:
            tk.Label(frame, text=f"File {ft}:").pack(anchor='w')
            ttk.Button(
                frame,
                text=f"Browse {ft}",
                command=lambda t=ft: self._browse(t),
            ).pack(anchor='w', pady=2)
            lbl = tk.Label(frame, text="Chưa chọn", fg="gray")
            lbl.pack(anchor='w')
            self._labels[ft] = lbl

        ttk.Button(frame, text="Tiếp tục (Next >>)", command=self.on_next).pack(pady=30)

    def _browse(self, file_type):
        path = filedialog.askopenfilename(
            filetypes=[("Excel/CSV files", "*.xlsx *.xls *.csv")],
        )
        if path:
            self.model.file_paths[file_type] = path
            self._labels[file_type].config(text=path, fg="green")
