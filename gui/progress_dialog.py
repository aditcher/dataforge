"""
DataForge Progress Dialog

Tkinter progress dialog for long-running operations like:
- Loading large files
- Cleaning data
- Generating outputs
"""

import tkinter as tk
from tkinter import ttk


class ProgressDialog:
    """
    Modal progress dialog with cancel support.
    """

    def __init__(self, parent, title: str = "Processing", 
                 message: str = "Please wait...",
                 max_value: int = 100,
                 show_cancel: bool = True):
        """
        Initialize progress dialog.

        Args:
            parent: Parent tkinter window
            title: Dialog title
            message: Status message
            max_value: Maximum progress value
            show_cancel: Whether to show cancel button
        """
        self.parent = parent
        self.max_value = max_value
        self.cancelled = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (150 // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Content
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        self.message_label = ttk.Label(frame, text=message, font=("Helvetica", 11))
        self.message_label.pack(anchor=tk.W, pady=(0, 10))

        self.progress = ttk.Progressbar(frame, mode='determinate', 
                                       maximum=max_value, length=350)
        self.progress.pack(fill=tk.X, pady=(0, 10))

        self.detail_label = ttk.Label(frame, text="", font=("Helvetica", 9), 
                                     foreground="#666666")
        self.detail_label.pack(anchor=tk.W)

        if show_cancel:
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill=tk.X, pady=(10, 0))
            self.cancel_btn = ttk.Button(btn_frame, text="Cancel", 
                                        command=self._on_cancel)
            self.cancel_btn.pack(side=tk.RIGHT)

        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.dialog.update()

    def update(self, value: int, message: str = None, detail: str = None):
        """Update progress."""
        if self.cancelled:
            return False

        self.progress['value'] = value

        if message:
            self.message_label.config(text=message)
        if detail:
            self.detail_label.config(text=detail)

        self.dialog.update_idletasks()
        return True

    def update_indeterminate(self, message: str = None):
        """Update in indeterminate mode (for unknown duration)."""
        if self.cancelled:
            return False

        self.progress.step(5)
        if message:
            self.message_label.config(text=message)
        self.dialog.update_idletasks()
        return True

    def _on_cancel(self):
        """Handle cancel button."""
        self.cancelled = True
        self.message_label.config(text="Cancelling...")
        self.dialog.update_idletasks()

    def close(self):
        """Close the dialog."""
        self.dialog.grab_release()
        self.dialog.destroy()

    def is_cancelled(self) -> bool:
        """Check if user cancelled."""
        return self.cancelled
