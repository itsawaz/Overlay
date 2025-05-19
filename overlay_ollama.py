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
        self.root.geometry("400x550+200+200")
        self.root.attributes("-topmost", True)
        # self.root.overrideredirect(True) # Optional: frameless

        self.root.configure(bg="#23272e")
        self.root.wm_attributes('-alpha', 0.92)  # Make window slightly see-through
        self.root.wm_attributes('-transparentcolor', '#1a1a1a')  # For more transparency on some systems

        # --- Modern Dark Theme Styles ---
        dark_bg = "#23272e"
        accent = "#3a3f4b"
        text_fg = "#f1f1f1"
        entry_bg = "#181a20"
        button_bg = "#3a3f4b"
        button_fg = "#f1f1f1"
        border_color = "#444857"
        accent2 = "#0078d4"  # Windows 11 blue accent

        label = tk.Label(self.root, text="Try to screenshot this window's content!\n(Windows Only Experiment)",
                         font=("Segoe UI", 13, "bold"), padx=20, pady=20, bg=dark_bg, fg=text_fg)
        label.pack(expand=False, fill="x")

        # --- Model Selection ---
        self.available_models = [
            "deepseek-r1:14b",
            "deepseek-r1:7b",
            "deepseek-r1:32b",
            "llama4:latest",
            "qwen3:0.6b",
            "granite3.3:8b",
            "granite3.3:2b",
            "granite3.2-vision:latest"
        ]
        self.selected_model = tk.StringVar(value="deepseek-r1:7b")
        model_frame = tk.Frame(self.root, bg=dark_bg)
        model_frame.pack(fill="x", padx=10, pady=(5,0))
        tk.Label(model_frame, text="Model:", bg=dark_bg, fg=text_fg, font=("Segoe UI", 10)).pack(side="left")
        model_menu = tk.OptionMenu(model_frame, self.selected_model, *self.available_models)
        model_menu.config(bg=accent, fg=text_fg, font=("Segoe UI", 10), highlightthickness=0, bd=0, activebackground=accent2, activeforeground=text_fg)
        model_menu['menu'].config(bg=accent, fg=text_fg, font=("Segoe UI", 10))
        model_menu.pack(side="left", padx=(5,0))

        # --- Chat UI ---
        chat_frame = tk.Frame(self.root, bg=dark_bg)
        chat_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.chat_display = tk.Text(chat_frame, height=15, state="disabled", wrap="word",
                                    bg=accent, fg=text_fg, insertbackground=text_fg, font=("Segoe UI", 11),
                                    bd=0, highlightthickness=1, highlightbackground=border_color)
        self.chat_display.pack(side="top", fill="both", expand=True, pady=(0, 8))
        self.setup_chat_tags()

        entry_frame = tk.Frame(chat_frame, bg=dark_bg)
        entry_frame.pack(side="bottom", fill="x")

        self.user_entry = tk.Entry(entry_frame, bg=entry_bg, fg=text_fg, insertbackground=text_fg,
                                   font=("Segoe UI", 11), bd=0, highlightthickness=1, highlightbackground=border_color)
        self.user_entry.pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=6)
        self.user_entry.bind("<Return>", self.send_message)

        send_btn = tk.Button(entry_frame, text="Send", command=self.send_message,
                             bg=accent2, fg=button_fg, font=("Segoe UI", 10, "bold"),
                             bd=0, activebackground="#005fa3", activeforeground=text_fg, padx=18, pady=6, cursor="hand2")
        send_btn.pack(side="right")

        # --- Stop Button ---
        self.stop_event = None
        stop_btn = tk.Button(entry_frame, text="Stop", command=self.stop_response,
                             bg="#c50f1f", fg=button_fg, font=("Segoe UI", 10, "bold"),
                             bd=0, activebackground="#a80000", activeforeground=text_fg, padx=10, pady=6, cursor="hand2")
        stop_btn.pack(side="right", padx=(0, 5))

        close_button = tk.Button(self.root, text="Close (and reset affinity)", command=self.on_close,
                                 bg=button_bg, fg=button_fg, font=("Segoe UI", 10),
                                 bd=0, activebackground="#c50f1f", activeforeground=text_fg, padx=10, pady=4, cursor="hand2")
        close_button.pack(pady=10)

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

    def append_chat(self, text, sender="user", stream=False):
        self.chat_display.config(state="normal")
        separator_line = "\n\n────────────────────────────────────────────\n\n"
        if sender == "user":
            # User message formatting
            self.chat_display.insert(tk.END, "You: ", ("user_label",))
            self.chat_display.insert(tk.END, text + "\n", ("user_msg",))
            # No separator after user message
        elif sender == "ai":
            self.chat_display.insert(tk.END, "AI: ", ("ai_label",))
            self.chat_display.insert(tk.END, text + "\n", ("ai_msg",))
            self.chat_display.insert(tk.END, separator_line, ("separator",))
        elif sender == "system":
            self.chat_display.insert(tk.END, text + "\n", ("system_msg",))
            self.chat_display.insert(tk.END, separator_line, ("separator",))
        else:
            self.chat_display.insert(tk.END, text + "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state="disabled")

    def setup_chat_tags(self):
        # Call this after chat_display is created
        self.chat_display.tag_configure("user_label", foreground="#0078d4", font=("Segoe UI", 11, "bold"))
        self.chat_display.tag_configure("user_msg", foreground="#f1f1f1", font=("Segoe UI", 11, "normal"))
        self.chat_display.tag_configure("ai_label", foreground="#22c55e", font=("Segoe UI", 11, "bold"))
        self.chat_display.tag_configure("ai_msg", foreground="#e0ffe0", font=("Segoe UI", 11, "normal"))
        self.chat_display.tag_configure("system_msg", foreground="#b0b0b0", font=("Segoe UI", 10, "italic"))
        self.chat_display.tag_configure("separator", foreground="#444857")

    def send_message(self, event=None):
        user_text = self.user_entry.get().strip()
        if not user_text:
            return
        self.append_chat(user_text, sender="user")
        self.user_entry.delete(0, tk.END)
        model = self.selected_model.get()
        system_instruction = (
            "You are an AI assistant helping with real-time interview questions for an experienced Software Development Engineer (SDE). "
            "Always answer as quickly as possible, be concise and to the point, but ensure your answers are informative and demonstrate depth of knowledge. "
            "If the question is technical, give a direct, expert-level answer first, then a brief but insightful explanation. "
            "Do not use <think> or similar tags in your response. "
            "If you output code, always format it as a single code block between triple backticks (```), and do not add extra commentary inside the code block."
        )
        full_prompt = f"{system_instruction}\n\nUser: {user_text}"
        self.root.after(100, lambda: self.query_ollama(full_prompt, model))

    def query_ollama(self, prompt, model=None):
        import threading
        def worker(stop_event):
            import requests
            try:
                url = "http://localhost:11434/api/generate"
                model_to_use = model or getattr(self, 'selected_model', None)
                if isinstance(model_to_use, tk.StringVar):
                    model_to_use = model_to_use.get()
                if not model_to_use:
                    model_to_use = "llama3"
                data = {"model": model_to_use, "prompt": prompt}
                response = requests.post(url, json=data, timeout=120, stream=True)
                if response.status_code == 200:
                    ai_buffer = ""
                    first_chunk = True
                    def stream_append(chunk, first=False):
                        self.chat_display.config(state="normal")
                        if first:
                            self.chat_display.insert(tk.END, "AI: ", ("ai_label",))
                            self.chat_display.mark_set("ai_stream", tk.END)
                        self.chat_display.insert("ai_stream", chunk, ("ai_msg",))
                        self.chat_display.see(tk.END)
                        self.chat_display.config(state="disabled")
                    for line in response.iter_lines(decode_unicode=True):
                        if stop_event.is_set():
                            break
                        if not line:
                            continue
                        try:
                            import json
                            resp_json = json.loads(line)
                            chunk = resp_json.get("response", "")
                            if chunk:
                                ai_buffer += chunk
                                if first_chunk:
                                    self.root.after(0, lambda c=chunk: stream_append(c, first=True))
                                    first_chunk = False
                                else:
                                    self.root.after(0, lambda c=chunk: stream_append(c))
                        except Exception as e:
                            print(f"Streaming parse error: {e}, line: {line}")
                    # After streaming, add separator
                    def finish_stream():
                        self.chat_display.config(state="normal")
                        separator_line = "\n\n────────────────────────────────────────────\n\n"
                        self.chat_display.insert(tk.END, separator_line, ("separator",))
                        self.chat_display.config(state="disabled")
                    self.root.after(0, finish_stream)
                else:
                    answer = f"[Ollama error: {response.status_code}]"
                    self.root.after(0, lambda: self.append_chat(answer, sender="system"))
            except Exception as e:
                answer = f"[Error: {e}]"
                self.root.after(0, lambda: self.append_chat(answer, sender="system"))
        self.stop_event = threading.Event()
        threading.Thread(target=worker, args=(self.stop_event,), daemon=True).start()

    def stop_response(self):
        if self.stop_event:
            self.stop_event.set()

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