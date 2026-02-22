import tkinter as tk
import multiprocessing
from UIs.app import FinancialCalculatorApp


def main():
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


if __name__ == "__main__":
    # Required for multiprocessing on Windows
    multiprocessing.freeze_support()
    main()