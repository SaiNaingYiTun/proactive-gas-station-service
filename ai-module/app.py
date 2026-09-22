"""Desktop window for the live detection.

Type (or paste) the camera's stream link -- or browse to a recorded video --
press Start, and the annotated detection view opens inside the window, with
the entries and exits it sends to the backend listed underneath.  The web
dashboard stays the place where visits are reviewed.

Start it with "Start Live Detection.bat" (no console window), or
    .venv\\Scripts\\pythonw.exe app.py
"""

import os
import queue
import re
import sys
import threading
import time
import traceback
from datetime import datetime

# main.py only turns the make/model classifier on through this variable.
os.environ.setdefault("ENABLE_MAKE_MODEL", "1")

_log_queue = queue.Queue()


class _LineWriter:
    """Collects everything the pipeline prints so the window can show it.

    pythonw.exe has no console at all, and even in a console the pipeline's
    events are more useful next to the video than scrolling past in a terminal."""

    def __init__(self, passthrough):
        self._passthrough = passthrough
        self._buffer = ""
        self._lock = threading.Lock()

    def write(self, text):
        if not text:
            return 0
        if self._passthrough is not None:
            try:
                self._passthrough.write(text)
            except Exception:
                pass
        with self._lock:
            self._buffer += text
            *lines, self._buffer = re.split(r"[\r\n]", self._buffer)
        for line in lines:
            if line.strip():
                _log_queue.put(line.rstrip())
        return len(text)

    def flush(self):
        pass

    def isatty(self):
        return False


sys.stdout = _LineWriter(sys.__stdout__)
sys.stderr = _LineWriter(sys.__stderr__)

import json  # noqa: E402
import tkinter as tk  # noqa: E402
from tkinter import filedialog, messagebox, ttk  # noqa: E402

import cv2  # noqa: E402
import requests  # noqa: E402
from PIL import Image, ImageTk  # noqa: E402

import backend  # noqa: E402

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_settings.json")
STREAM_PATTERN = re.compile(r"^(rtsp|rtsps|rtmp|http|https|udp|tcp)://", re.IGNORECASE)

BG, PANEL, FIELD = "#0d1117", "#161b22", "#0b0f14"
TEXT, MUTED, BORDER = "#e6edf3", "#8b949e", "#30363d"
ACCENT, OK, WARN, BAD = "#f0883e", "#3fb950", "#d29922", "#f85149"

# Lines from the pipeline worth showing in the event list, and how to word them.
# Everything else (per-frame OCR/debug chatter) stays out unless "Show all" is on.
_TAGGED = (
    ("[seen again]", "Entry saved", "ok"),
    ("[NEW]", "Entry saved", "ok"),
    ("[ENTRY-UPDATE]", "Entry updated", "ok"),
    ("[ENTRY-SKIPPED]", "Entry skipped", "warn"),
    ("[EXIT]", "Exit saved", "warn"),
    ("[EXIT-VEHICLE]", "Vehicle crossed exit line", "warn"),
    ("[DETECTED]", "Vehicle read", "ok"),
    ("[SINGLE-READ]", "Plate (single read)", "ok"),
    ("[PROVISIONAL]", "Plate (provisional)", "warn"),
)
_PLAIN_PREFIXES = (
    "Live detection", "End of video", "Lost camera", "Reconnect", "Cannot open", "Reconnected",
    "[MAKE] track", "[COLOR] track", "[MAKE] Using", "[OCR] Using", "[THAI-PLATE] Using", "[APP]",
)
_ERROR_HINTS = ("error", "traceback", "failed", "cannot", "⚠")


def _redact(text):
    return re.sub(r"(://[^/:@\s]+):[^@/\s]*@", r"\1:***@", text)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Proactive Gas Station - Live Detection")
        # Fit the screen: most of it, but never a window taller than the display.
        width = min(1280, int(self.winfo_screenwidth() * 0.86))
        height = min(880, int(self.winfo_screenheight() * 0.88))
        self.geometry(f"{width}x{height}+{(self.winfo_screenwidth() - width) // 2}+{max(0, (self.winfo_screenheight() - height) // 3)}")
        self.minsize(860, 560)
        self.configure(bg=BG)

        self._main = None                       # the detection module, imported in the background
        self._thread = None
        self._stop = threading.Event()
        self._events = queue.Queue()
        self._frame_lock = threading.Lock()
        self._latest = None
        self._has_frame = False
        self._photo = None
        self._frame_count = 0
        self._fps_mark = (time.time(), 0)
        self._closing = False
        self._backend_url = ""

        self._build_style()
        self._build_ui(self._load_settings())
        self._set_state("Loading AI models... (this takes a moment)", MUTED)
        self._sync_buttons()

        threading.Thread(target=self._load_models, daemon=True).start()
        threading.Thread(target=self._watch_backend, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(30, self._tick)

    # ------------------------------------------------------------------ UI
    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 15))
        style.configure("Eyebrow.TLabel", foreground=ACCENT, font=("Segoe UI Semibold", 8))
        style.configure(
            "TEntry", fieldbackground=FIELD, foreground=TEXT, bordercolor=BORDER,
            lightcolor=BORDER, darkcolor=BORDER, insertcolor=TEXT, padding=6,
        )
        style.configure("TCheckbutton", background=BG, foreground=MUTED)
        style.map("TCheckbutton", background=[("active", BG)], foreground=[("active", TEXT)])
        style.configure(
            "TButton", background=PANEL, foreground=TEXT, bordercolor=BORDER,
            lightcolor=PANEL, darkcolor=PANEL, padding=(12, 6),
        )
        style.map("TButton", background=[("active", "#21262d"), ("disabled", BG)],
                  foreground=[("disabled", MUTED)])
        style.configure(
            "Accent.TButton", background=ACCENT, foreground="#1a1206", bordercolor=ACCENT,
            lightcolor=ACCENT, darkcolor=ACCENT, font=("Segoe UI Semibold", 10), padding=(18, 6),
        )
        style.map("Accent.TButton", background=[("active", "#f5a05f"), ("disabled", "#5b4630")],
                  foreground=[("disabled", "#2a2116")])
        style.configure("Stop.TButton", background=BAD, foreground="white", bordercolor=BAD,
                        lightcolor=BAD, darkcolor=BAD, font=("Segoe UI Semibold", 10), padding=(18, 6))
        style.map("Stop.TButton", background=[("active", "#ff6b63"), ("disabled", "#5a2a28")])

    def _build_ui(self, settings):
        outer = ttk.Frame(self, padding=(18, 14, 18, 10))
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="LIVE DETECTION", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(header, text="Proactive Gas Station", style="Title.TLabel").pack(anchor="w")

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(12, 8))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Stream link", style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.link_var = tk.StringVar(value=settings.get("stream", ""))
        self.link_entry = ttk.Entry(controls, textvariable=self.link_var, show="•")
        self.link_entry.grid(row=0, column=1, sticky="ew")
        self.show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Show", variable=self.show_var, command=self._toggle_show).grid(
            row=0, column=2, padx=(8, 0))
        self.browse_btn = ttk.Button(controls, text="Browse video...", command=self._browse)
        self.browse_btn.grid(row=0, column=3, padx=(8, 0))
        self.start_btn = ttk.Button(controls, text="Start", style="Accent.TButton", command=self._toggle_run)
        self.start_btn.grid(row=0, column=4, padx=(8, 0))

        ttk.Label(controls, text="Backend", style="Muted.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        self.backend_var = tk.StringVar(value=settings.get("backend", backend.DEFAULT_API_BASE))
        self._backend_url = self.backend_var.get()
        self.backend_var.trace_add("write", lambda *_: setattr(self, "_backend_url", self.backend_var.get()))
        ttk.Entry(controls, textvariable=self.backend_var).grid(row=1, column=1, sticky="ew", pady=(8, 0))
        self.backend_status = tk.Label(controls, text="● checking...", bg=BG, fg=MUTED, font=("Segoe UI", 10))
        self.backend_status.grid(row=1, column=2, columnspan=2, sticky="w", padx=(10, 0), pady=(8, 0))
        self.send_var = tk.BooleanVar(value=settings.get("send", True))
        ttk.Checkbutton(controls, text="Save events to backend", variable=self.send_var).grid(
            row=1, column=4, sticky="e", padx=(8, 0), pady=(8, 0))

        # The parts under the video are packed first, from the bottom up, so a
        # small window shrinks the video instead of pushing the status bar off.
        status = ttk.Frame(outer)
        status.pack(side="bottom", fill="x", pady=(8, 0))
        self.state_label = tk.Label(status, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="w")
        self.state_label.pack(side="left")
        self.fps_label = tk.Label(status, text="", bg=BG, fg=MUTED, font=("Consolas", 10))
        self.fps_label.pack(side="right")

        log_frame = ttk.Frame(outer, style="Panel.TFrame")
        log_frame.pack(side="bottom", fill="x")

        log_header = ttk.Frame(outer)
        log_header.pack(side="bottom", fill="x", pady=(10, 4))
        ttk.Label(log_header, text="EVENTS", style="Eyebrow.TLabel").pack(side="left")
        self.verbose_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(log_header, text="Show all output", variable=self.verbose_var).pack(side="right")

        self.canvas = tk.Canvas(outer, bg="black", width=1, height=1, highlightthickness=1,
                                highlightbackground=BORDER)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._draw_placeholder())

        self.log = tk.Text(
            log_frame, height=6, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word",
            font=("Consolas", 10), padx=10, pady=8, state="disabled", highlightthickness=0,
        )
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        for tag, colour in (("ok", OK), ("warn", WARN), ("bad", BAD), ("muted", MUTED), ("plain", TEXT)):
            self.log.tag_configure(tag, foreground=colour)

    def _toggle_show(self):
        self.link_entry.configure(show="" if self.show_var.get() else "•")

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Choose a recorded video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv"), ("All files", "*.*")],
        )
        if path:
            self.link_var.set(os.path.normpath(path))
            self.show_var.set(True)
            self._toggle_show()

    def _set_state(self, text, colour=MUTED):
        self.state_label.configure(text=text, fg=colour)

    def _sync_buttons(self):
        running = self._thread is not None and self._thread.is_alive()
        stopping = running and self._stop.is_set()
        if running:
            self.start_btn.configure(text="Stopping..." if stopping else "Stop", style="Stop.TButton",
                                     state="disabled" if stopping else "normal")
        else:
            self.start_btn.configure(text="Start", style="Accent.TButton",
                                     state="normal" if self._main is not None else "disabled")
        self.browse_btn.configure(state="disabled" if running else "normal")

    def _draw_placeholder(self):
        if self._has_frame:
            return
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_text(
            w // 2, h // 2, fill="#5c6570", font=("Segoe UI", 13), justify="center",
            text="Enter the camera's stream link (or browse to a recorded video)\nand press Start",
        )

    # ------------------------------------------------------------- settings
    def _load_settings(self):
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return {}

    def _save_settings(self):
        data = {"stream": self.link_var.get().strip(), "backend": self.backend_var.get().strip(),
                "send": bool(self.send_var.get())}
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
        except OSError:
            pass

    # ------------------------------------------------------------ background
    def _load_models(self):
        try:
            import main  # loads every model; slow, so it happens after the window is up
            self._main = main
            self._events.put(("ready", None))
        except Exception:
            self._events.put(("load_failed", traceback.format_exc()))

    def _watch_backend(self):
        while not self._closing:
            url = self._backend_url.strip().rstrip("/")
            state = False
            if url:
                try:
                    # /api/visits now requires a staff login (the dashboard
                    # got real authentication); /api/health is the
                    # unauthenticated liveness check meant for exactly this.
                    state = requests.get(f"{url}/api/health", timeout=2).ok
                except requests.RequestException:
                    state = False
            self._events.put(("backend", state))
            for _ in range(16):          # re-check every ~8 s, but notice closing quickly
                if self._closing:
                    return
                time.sleep(0.5)

    def _on_frame(self, frame):
        with self._frame_lock:
            self._latest = frame
        self._frame_count += 1

    def _run(self, source):
        try:
            self._main.run_live(source=source, on_frame=self._on_frame, should_stop=self._stop.is_set)
            self._events.put(("finished", None))
        except Exception:
            print(traceback.format_exc(), flush=True)
            self._events.put(("finished", "error"))
        finally:
            self._main.stop_flag = True       # make sure the pipeline's worker threads end

    # --------------------------------------------------------------- actions
    def _toggle_run(self):
        if self._thread is not None and self._thread.is_alive():
            self._stop.set()
            self._set_state("Stopping...", MUTED)
            self._sync_buttons()
            return
        source = self.link_var.get().strip().strip('"')
        if not source:
            messagebox.showinfo("Stream link", "Enter the camera's stream link, or choose a video file with Browse.")
            return
        if not (os.path.isfile(source) or STREAM_PATTERN.match(source)):
            messagebox.showerror(
                "Stream link",
                "That doesn't look like a stream link or a video file.\n\n"
                "A link starts with rtsp:// (or http://), for example\n"
                "rtsp://user:password@192.168.1.209:554/Streaming/Channels/101",
            )
            return
        backend.set_api_base(self.backend_var.get().strip() or backend.DEFAULT_API_BASE)
        backend.set_enabled(self.send_var.get())
        self._save_settings()
        self._stop.clear()
        with self._frame_lock:
            self._latest = None
        self._has_frame = False
        self._frame_count = 0
        self._fps_mark = (time.time(), 0)
        self._set_state("Connecting...", MUTED)
        self._thread = threading.Thread(target=self._run, args=(source,), daemon=True)
        self._thread.start()
        self._sync_buttons()

    def _on_close(self):
        self._save_settings()
        self._closing = True
        if self._thread is not None and self._thread.is_alive():
            self._stop.set()
            self._set_state("Closing...", MUTED)
            deadline = time.time() + 15

            def wait_then_close():
                if self._thread.is_alive() and time.time() < deadline:
                    self.after(150, wait_then_close)
                else:
                    self.destroy()

            wait_then_close()
        else:
            self.destroy()

    # ------------------------------------------------------------ UI updates
    def _tick(self):
        try:
            self._drain_log()
            self._drain_events()
            self._draw_frame()
            self._update_fps()
        except Exception:
            print(traceback.format_exc(), flush=True)
        finally:
            try:
                self.after(30, self._tick)
            except tk.TclError:          # window already destroyed
                pass

    def _draw_frame(self):
        with self._frame_lock:
            frame, self._latest = self._latest, None
        if frame is None:
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 20 or ch < 20:
            return
        height, width = frame.shape[:2]
        scale = min(cw / width, ch / height)
        size = (max(1, int(width * scale)), max(1, int(height * scale)))
        small = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        photo = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)))
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=photo)
        self._photo = photo                     # keep a reference or Tk drops the image
        if not self._has_frame:
            self._has_frame = True
            self._set_state("Running", OK)

    def _update_fps(self):
        mark_time, mark_count = self._fps_mark
        now = time.time()
        if now - mark_time >= 1.0:
            running = self._thread is not None and self._thread.is_alive() and self._has_frame
            fps = (self._frame_count - mark_count) / (now - mark_time)
            self.fps_label.configure(text=f"{fps:4.1f} FPS" if running else "")
            self._fps_mark = (now, self._frame_count)

    def _drain_events(self):
        try:
            while True:
                kind, payload = self._events.get_nowait()
                if kind == "ready":
                    self._set_state("Ready. Enter the stream link and press Start.", MUTED)
                    self._sync_buttons()
                elif kind == "load_failed":
                    self._set_state("The AI models could not be loaded - see the event list.", BAD)
                    for line in payload.strip().splitlines()[-12:]:
                        self._add_log(line, force=True)
                elif kind == "backend":
                    self.backend_status.configure(
                        text="● connected" if payload else "● not reachable",
                        fg=OK if payload else BAD,
                    )
                elif kind == "finished":
                    self._thread = None
                    self._has_frame = False
                    self._draw_placeholder_after_run()
                    self._set_state("Stopped." if payload is None and self._stop.is_set()
                                    else "Finished." if payload is None else "Stopped because of an error.",
                                    MUTED if payload is None else BAD)
                    self.fps_label.configure(text="")
                    self._sync_buttons()
        except queue.Empty:
            pass

    def _draw_placeholder_after_run(self):
        # keep the last frame on screen after the run ends; only show the
        # prompt again if nothing was ever drawn
        if self._photo is None:
            self._draw_placeholder()

    def _drain_log(self):
        try:
            while True:
                self._add_log(_log_queue.get_nowait())
        except queue.Empty:
            pass

    def _add_log(self, line, force=False):
        line = _redact(line)
        tag, shown = "plain", None
        for prefix, label, colour in _TAGGED:
            if line.startswith(prefix):
                tag, shown = colour, f"{label}{line[len(prefix):]}"
                break
        if shown is None:
            if any(line.startswith(prefix) for prefix in _PLAIN_PREFIXES):
                shown, tag = line, "muted"
            elif force or self.verbose_var.get():
                shown, tag = line, "muted"
        if shown is None:
            return
        if any(hint in shown.lower() for hint in _ERROR_HINTS) and tag != "ok":
            tag = "bad"
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"{stamp}  {shown}\n", tag)
        if int(self.log.index("end-1c").split(".")[0]) > 500:
            self.log.delete("1.0", "100.0")
        self.log.see("end")
        self.log.configure(state="disabled")


def main():
    try:  # keep text crisp on high-DPI Windows displays
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()


if __name__ == "__main__":
    main()
