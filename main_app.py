# main_app.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, PhotoImage
import threading
from transcriber import transcribe_audio_file
import os
import json
import logging
import shutil
import tempfile
import sys
import webbrowser
from translations import translations

SETTINGS_FILE = "settings.json"

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

class TranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = tk.StringVar(value="en")
        self.root.title("AI Transcription Tool")
        self.root.geometry("700x700")
        self.root.option_add("*Font", ("Arial", 11))

        # Model mapping from display names to Whisper model names
        self.model_mapping = {
            # German display names
            "winzig": "tiny",
            "mittel": "medium",
            "mittelgroß (effizienter)": "turbo",
            "groß": "large",
            "groß (neuere Version)": "large-v3",
            
            # English display names
            "tiny": "tiny",
            "medium": "medium",
            "medium (efficient)": "turbo",
            "large": "large",
            "large (newer version)": "large-v3"
        }

        self.audio_files = []
        self.output_dir = tk.StringVar()

        self.model_choice = tk.StringVar(value="tiny")
        self.language_choice = tk.StringVar(value="de")
        self.punctuate = tk.BooleanVar()
        self.include_srt = tk.BooleanVar()

        self.logo_image = PhotoImage(file=resource_path("UK_Logo_white.png")).subsample(2, 2)
        self.aw_logo = PhotoImage(file=resource_path("AW_logo.png")).subsample(2, 2)

        settings = load_settings()
        self.model_choice.set(settings.get("model", "tiny"))
        self.output_dir.set(settings.get("output_dir", ""))
        self.language_choice.set(settings.get("language", "de"))
        self.punctuate.set(settings.get("punctuate", False))
        self.include_srt.set(settings.get("include_srt", False))
        self.current_lang.set(settings.get("language_ui", "en"))

        self._build_ui()
        self.update_ui_language()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#2e2e2e")
        style.configure("TLabel", background="#2e2e2e", foreground="white", font=("Arial", 11))
        style.configure("TButton", background="#444", foreground="white", padding=6, font=("Arial", 11))
        style.configure("TCheckbutton", background="#2e2e2e", foreground="white", font=("Arial", 11))
        style.configure("TEntry", font=("Arial", 11))

        # Scrollable canvas setup
        canvas = tk.Canvas(self.root, background="#2e2e2e")
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frm_container = ttk.Frame(scrollable_frame)
        frm_container.pack(expand=True, anchor='center')

        frm = frm_container

        # Header Frame with logo and title
        header_frame = ttk.Frame(frm)
        header_frame.pack(fill="x", pady=(0, 10))

        # AW Logo with link
        aw_logo_label = ttk.Label(header_frame, image=self.aw_logo, cursor="hand2")
        aw_logo_label.pack(side="left", padx=10)
        aw_logo_label.bind("<Button-1>", lambda e: webbrowser.open("https://andreas-weilinghoff.com/"))

        # Language switch
        lang_frame = ttk.Frame(header_frame)
        lang_frame.pack(side="right", padx=10)
        
        self.en_btn = ttk.Button(lang_frame, text="EN", width=3,
                                command=lambda: self.set_language("en"))
        self.de_btn = ttk.Button(lang_frame, text="DE", width=3,
                                command=lambda: self.set_language("de"))
        self.en_btn.pack(side="right", padx=2)
        self.de_btn.pack(side="right", padx=2)

        self.title_label = ttk.Label(
            header_frame,
            text="",
            font=("Arial", 14, "bold"),
            anchor="center",
            justify="center"
        )
        self.title_label.pack(side="left", padx=10, expand=True)
        
        uni_logo_label = ttk.Label(header_frame, image=self.logo_image, cursor="hand2")
        uni_logo_label.pack(side="right", padx=10)
        uni_logo_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.uni-koblenz.de/de"))

        # Description
        self.description_label = ttk.Label(frm, text="", wraplength=650, justify="left")
        self.description_label.pack(pady=(0, 10))

        self.toggle_button = ttk.Button(frm, text="", command=self.toggle_description)
        self.toggle_button.pack()

        self.select_files_btn = ttk.Button(frm, text="", command=self.select_files)
        self.select_files_btn.pack(pady=5)
        self.file_label = ttk.Label(frm, text="")
        self.file_label.pack(pady=5)

        self.output_dir_label = ttk.Label(frm, text="")
        self.output_dir_label.pack(anchor="w")
        path_frame = ttk.Frame(frm)
        path_frame.pack(fill="x", pady=5)
        ttk.Entry(path_frame, textvariable=self.output_dir, width=45).pack(side="left", fill="x", expand=True, padx=5)
        self.browse_btn = ttk.Button(path_frame, text="", command=self.select_output_folder)
        self.browse_btn.pack(side="left")

        self.model_label = ttk.Label(frm, text="")
        self.model_label.pack(anchor="w", pady=(10, 0))
        self.model_combobox = ttk.Combobox(frm, textvariable=self.model_choice, width=25)
        self.model_combobox.pack(pady=(0, 10))
        self.update_model_options()

        self.language_label = ttk.Label(frm, text="")
        self.language_label.pack(anchor="w")
        self.language_combobox = ttk.Combobox(frm, textvariable=self.language_choice, values=["de", "en", "fr", "es", "it"], width=25)
        self.language_combobox.pack(pady=(0, 10))

        self.language_note = ttk.Label(frm, text="", wraplength=650, justify="left")
        self.language_note.pack(pady=(0, 10))

        punctuate_frame = ttk.Frame(frm)
        punctuate_frame.pack(anchor="w", pady=3)
        self.punctuate_cb = ttk.Checkbutton(punctuate_frame, variable=self.punctuate)
        self.punctuate_cb.pack(side="left")
        self.punctuate_info_btn = ttk.Button(punctuate_frame, text="?", width=2, command=self.toggle_punctuate_info)
        self.punctuate_info_btn.pack(side="left", padx=5)

        self.punctuate_info = ttk.Label(frm, text="", wraplength=650, justify="left")
        self.punctuate_info.pack_forget()

        srt_frame = ttk.Frame(frm)
        srt_frame.pack(anchor="w", pady=3)
        self.srt_cb = ttk.Checkbutton(srt_frame, variable=self.include_srt)
        self.srt_cb.pack(side="left")
        self.srt_info_btn = ttk.Button(srt_frame, text="?", width=2, command=self.toggle_srt_info)
        self.srt_info_btn.pack(side="left", padx=5)

        self.srt_info = ttk.Label(frm, text="", wraplength=650, justify="left")
        self.srt_info.pack_forget()

        self.start_btn = ttk.Button(frm, text="", command=self.start_transcription)
        self.start_btn.pack(pady=10)

        self.status_label = ttk.Label(frm, text="", foreground="lightgreen")
        self.status_label.pack(pady=10)

        self.copyright_label = ttk.Label(frm, text="", font=("Arial", 8))
        self.copyright_label.pack(side="bottom", pady=10)

    def update_model_options(self):
        """Update model combobox options based on current language"""
        lang = self.current_lang.get()
        trans = translations[lang]
        self.model_combobox['values'] = trans["model_options"]
        
        # Try to preserve current selection if it exists in new options
        current_val = self.model_choice.get()
        if current_val not in trans["model_options"]:
            # Reset to first option if current not available
            self.model_choice.set(trans["model_options"][0])
    
    def set_language(self, lang):
        self.current_lang.set(lang)
        self.update_ui_language()
        self.update_model_options()
        save_settings({
            "model": self.model_choice.get(),
            "output_dir": self.output_dir.get(),
            "language": self.language_choice.get(),
            "punctuate": self.punctuate.get(),
            "include_srt": self.include_srt.get(),
            "language_ui": lang
        })

    def update_ui_language(self):
        lang = self.current_lang.get()
        trans = translations[lang]
        
        # Update UI elements
        self.root.title(trans["app_title"])
        self.title_label.config(text=trans["app_title"])
        self.description_label.config(text=trans["description_short"])
        self.toggle_button.config(text=trans["more"])
        self.file_label.config(text=trans["no_file"])
        self.status_label.config(text=trans["ready"])
        
        # Update buttons and labels
        self.output_dir_label.config(text=trans["output_dir"])
        self.model_label.config(text=trans["model"])
        self.language_label.config(text=trans["language"])
        self.language_note.config(text=trans["language_note"])
        self.punctuate_cb.config(text=trans["punctuate"])
        self.srt_cb.config(text=trans["srt"])
        self.start_btn.config(text=trans["start"])
        self.copyright_label.config(text=trans["copyright"])
        self.select_files_btn.config(text=trans["select_files"])
        self.browse_btn.config(text=trans["browse"])
        self.punctuate_info_btn.config(text=trans["info"])
        self.srt_info_btn.config(text=trans["info"])
        
        # Update combobox values
        self.model_combobox['values'] = trans["model_options"]
        
        # Update info text
        self.punctuate_info.config(text=trans["punctuate_info"])
        self.srt_info.config(text=trans["srt_info"])

    def hide_all_info(self):
        self.punctuate_info.pack_forget()
        self.srt_info.pack_forget()

    def toggle_description(self):
        lang = self.current_lang.get()
        trans = translations[lang]
        
        if self.description_label["text"] == trans["description_short"]:
            self.description_label["text"] = trans["description_full"]
            self.toggle_button["text"] = trans["less"]
        else:
            self.description_label["text"] = trans["description_short"]
            self.toggle_button["text"] = trans["more"]

    def toggle_punctuate_info(self):
        self.hide_all_info()
        if not self.punctuate_info.winfo_ismapped():
            self.punctuate_info.pack()

    def toggle_srt_info(self):
        self.hide_all_info()
        if not self.srt_info.winfo_ismapped():
            self.srt_info.pack()

    def select_files(self):
        lang = self.current_lang.get()
        files = filedialog.askopenfilenames(filetypes=[("Audio Files", "*.wav *.mp3 *.m4a *.mp4 *.mov *.ogg")])
        if files:
            self.audio_files = files
            self.file_label.config(text=f"{len(files)} {translations[lang]['files_selected']}")
        else:
            self.audio_files = []
            self.file_label.config(text=translations[lang]["no_file"])

    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir.set(folder)

    def start_transcription(self):
        lang = self.current_lang.get()
        if not self.audio_files:
            messagebox.showerror("Error", translations[lang]["error_file"])
            return
        if not self.output_dir.get():
            messagebox.showerror("Error", translations[lang]["error_dir"])
            return

        # Map displayed model name to actual Whisper model name
        model_display = self.model_choice.get()
        model_actual = self.model_mapping.get(model_display, model_display)
        
        save_settings({
            "model": model_actual,
            "output_dir": self.output_dir.get(),
            "language": self.language_choice.get(),
            "punctuate": self.punctuate.get(),
            "include_srt": self.include_srt.get(),
            "language_ui": lang
        })

        self.status_label.config(text=translations[lang]["processing"].format(""), foreground="orange")
        threading.Thread(target=self.run_transcription, daemon=True).start()

    def run_transcription(self):
        lang = self.current_lang.get()
        for file in self.audio_files:
            try:
                temp_dir = tempfile.mkdtemp()
                local_path = os.path.join(temp_dir, os.path.basename(file))
                shutil.copy(file, local_path)

                logging.info("Starting transcription for: %s", file)
                
                # Map displayed model name to actual Whisper model name
                model_display = self.model_choice.get()
                model_actual = self.model_mapping.get(model_display, model_display)
                
                self.status_label.config(
                    text=translations[lang]["processing"].format(os.path.basename(file)),
                    foreground="orange"
                )
                self.status_label.update_idletasks()

                transcribe_audio_file(
                    local_path,
                    self.output_dir.get(),
                    model_name=model_actual,
                    language=self.language_choice.get(),
                    apply_punctuation=self.punctuate.get(),
                    generate_srt_file=self.include_srt.get()
                )
                logging.info("Finished transcription for: %s", file)
            except Exception as e:
                logging.error("Error processing %s: %s", file, str(e))
                messagebox.showerror("Transcription Error", str(e))
        self.status_label.config(text=translations[lang]["finished"], foreground="green")

if __name__ == '__main__':
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()