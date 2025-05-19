import tkinter as tk
import ctypes
import sys

# --- Windows Specific Constants and Functions ---
# User32.dll functions
# Docs: https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity
#       https://learn.microsoft.com/en-us/windows/win32/api/winuser/ne-winuser-windowdisplayaffinity

WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
# WDA_EXCLUDEFROMCAPTURE requires Windows 10 2004+ / Win 11 22H2+
# If not defined in your ctypes.wintypes, define it manually
WDA_EXCLUDEFROMCAPTURE = 0x00000011 # Hex 11, Decimal 17

# Window style constants
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080  # Hide from ALT+TAB

class ExperimentalOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Experimental Overlay")
        self.root.geometry("400x200+200+200")
        self.root.attributes("-topmost", True)
        # self.root.overrideredirect(True) # Optional: frameless

        label = tk.Label(self.root, text="Try to screenshot this window's content!\n(Windows Only Experiment)",
                         font=("Arial", 14), padx=20, pady=20)
        label.pack(expand=True, fill="both")

        close_button = tk.Button(self.root, text="Close (and reset affinity)", command=self.on_close)
        close_button.pack(pady=10)

        self.hwnd = None
        self.original_affinity_set = False
        self.original_exstyle = 0

        # Apply after window is created and visible
        self.root.after(100, self.apply_anti_capture)

    def apply_anti_capture(self):
        if sys.platform == "win32":
            try:
                self.hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                if not self.hwnd:
                    # Fallback for overrideredirect(True) where GetParent might fail
                    self.hwnd = self.root.winfo_id()

                print(f"Window HWND: {self.hwnd}")
                
                # Hide from ALT+TAB by applying WS_EX_TOOLWINDOW style
                self.original_exstyle = ctypes.windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
                new_exstyle = self.original_exstyle | WS_EX_TOOLWINDOW
                ctypes.windll.user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, new_exstyle)
                print("Applied WS_EX_TOOLWINDOW to hide from Alt+Tab")

                # Try WDA_EXCLUDEFROMCAPTURE first if available, then WDA_MONITOR
                # Note: Check your Windows version. WDA_EXCLUDEFROMCAPTURE is newer.
                affinity_to_set = WDA_EXCLUDEFROMCAPTURE
                # affinity_to_set = WDA_MONITOR # You can test this one too

                print(f"Attempting to set display affinity to: {affinity_to_set}")
                result = ctypes.windll.user32.SetWindowDisplayAffinity(self.hwnd, affinity_to_set)

                if result:
                    print("SetWindowDisplayAffinity successful.")
                    self.original_affinity_set = True
                else:
                    error_code = ctypes.windll.kernel32.GetLastError()
                    print(f"SetWindowDisplayAffinity failed. Error code: {error_code}")
                    # If WDA_EXCLUDEFROMCAPTURE failed, try WDA_MONITOR as a fallback
                    if affinity_to_set == WDA_EXCLUDEFROMCAPTURE:
                        print("Falling back to WDA_MONITOR...")
                        affinity_to_set = WDA_MONITOR
                        result = ctypes.windll.user32.SetWindowDisplayAffinity(self.hwnd, affinity_to_set)
                        if result:
                            print("SetWindowDisplayAffinity with WDA_MONITOR successful.")
                            self.original_affinity_set = True
                        else:
                            error_code = ctypes.windll.kernel32.GetLastError()
                            print(f"SetWindowDisplayAffinity with WDA_MONITOR failed. Error code: {error_code}")

            except Exception as e:
                print(f"Error applying anti-capture settings: {e}")
        else:
            print("This anti-capture experiment is for Windows only.")

    def reset_affinity(self):
        if sys.platform == "win32" and self.hwnd:
            try:
                # Restore original window style
                if hasattr(self, 'original_exstyle'):
                    ctypes.windll.user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, self.original_exstyle)
                    print("Restored original window style")
                
                # Reset display affinity
                if self.original_affinity_set:
                    print("Resetting display affinity to WDA_NONE.")
                    ctypes.windll.user32.SetWindowDisplayAffinity(self.hwnd, WDA_NONE)
            except Exception as e:
                print(f"Error resetting window properties: {e}")

    def on_close(self):
        self.reset_affinity()
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close) # Ensure reset on 'X' button
        self.root.mainloop()

if __name__ == "__main__":
    if sys.platform != "win32":
        print("WARNING: This script contains Windows-specific experiments for anti-screenshot measures.")
        # Fallback for non-Windows to just show a normal window
        root = tk.Tk()
        root.title("Overlay (Non-Windows)")
        tk.Label(root, text="This is a standard overlay on non-Windows systems.").pack(padx=50, pady=50)
        root.mainloop()
    else:
        overlay = ExperimentalOverlay()
        overlay.run()