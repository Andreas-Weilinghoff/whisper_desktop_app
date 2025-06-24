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
        self.root.title("KI-Transkriptionsprogramm")
        self.root.geometry("700x700")
        self.root.option_add("*Font", ("Arial", 11))

        self.audio_files = []
        self.output_dir = tk.StringVar()

        self.model_choice = tk.StringVar(value="winzig")
        self.language_choice = tk.StringVar(value="de")
        self.punctuate = tk.BooleanVar()
        self.include_srt = tk.BooleanVar()

        self.logo_image = PhotoImage(file=resource_path("UK_Logo_white.png")).subsample(2, 2)
        self.aw_logo = PhotoImage(file=resource_path("AW_logo.png")).subsample(2, 2)

        settings = load_settings()
        self.model_choice.set(settings.get("model", "winzig"))
        self.output_dir.set(settings.get("output_dir", ""))
        self.language_choice.set(settings.get("language", "de"))
        self.punctuate.set(settings.get("punctuate", False))
        self.include_srt.set(settings.get("include_srt", False))

        self._build_ui()

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


        ttk.Label(
            header_frame,
            text="KI-Transkriptionsprogramm",
            font=("Arial", 14, "bold"),
            anchor="center",
            justify="center"
        ).pack(side="left", padx=10, expand=True)
        
        uni_logo_label = ttk.Label(header_frame, image=self.logo_image, cursor="hand2")
        uni_logo_label.pack(side="right", padx=10)
        uni_logo_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.uni-koblenz.de/de"))


        self.short_text = "Diese App transkribiert automatisch beliebige Audio- und Mediendateien..."
        self.full_text = """
Diese App transkribiert automatisch beliebige Audio- und Mediendateien (z. B. .wav, .mp3, .mp4, .mov, .ogg) in geschriebenen Text.
Die KI-basierte Anwendung läuft lokal auf Ihrem Gerät - Daten werden nicht weitergeleitet. Die App wurde entwickelt von JProf. Dr. Andreas Weilinghoff [https://andreas-weilinghoff.com] und Saran Nair (M.Sc.) an der Universität Koblenz [https://www.uni-koblenz.de/de].

So funktioniert's:
Wählen Sie unten eine Datei aus, bestimmen Sie das gewünschte KI-Modell zur Transkription (je größer das Modell, desto besser das Ergebnis - allerdings verlängert sich dadurch auch die Verarbeitungszeit), legen Sie die Sprache fest und wählen Sie auf Ihrem Gerät den Speicherort für das fertige Transkript. Klicken Sie dann einfach auf 'Transkribieren starten'.

Bitte beachten Sie:
Die Dauer der Verarbeitung hängt von der Länge der Datei, der Größe des gewählten Modells sowie der Rechenleistung Ihres Geräts ab - in manchen Fällen kann die Transkription entsprechend mehr Zeit in Anspruch nehmen.
            """

        self.description_label = ttk.Label(frm, text=self.short_text, wraplength=650, justify="left")
        self.description_label.pack(pady=(0, 10))

        self.toggle_button = ttk.Button(frm, text="..mehr", command=self.toggle_description)
        self.toggle_button.pack()

        ttk.Button(frm, text="Audiodateien auswählen", command=self.select_files).pack(pady=5)
        self.file_label = ttk.Label(frm, text="Keine Datei ausgewählt")
        self.file_label.pack(pady=5)

        ttk.Label(frm, text="Speicherort wählen:").pack(anchor="w")
        path_frame = ttk.Frame(frm)
        path_frame.pack(fill="x", pady=5)
        ttk.Entry(path_frame, textvariable=self.output_dir, width=45).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(path_frame, text="Durchsuchen", command=self.select_output_folder).pack(side="left")

        ttk.Label(frm, text="Modell wählen:").pack(anchor="w", pady=(10, 0))
        model_display = {"tiny": "winzig", "medium": "mittel", "turbo": "mittelgroß (effizienter)", "large": "groß", "large-v3": "groß (neuere Version)"}
        ttk.Combobox(frm, textvariable=self.model_choice, values=list(model_display.values()), width=25).pack(pady=(0, 10))

        ttk.Label(frm, text="Sprache wählen:").pack(anchor="w")
        ttk.Combobox(frm, textvariable=self.language_choice, values=["de", "en", "fr", "es", "it"], width=25).pack(pady=(0, 10))

        ttk.Label(frm, text="Die Defaultsprache ist Deutsch (de), aber das Modell kann auch mit weiteren Sprachen arbeiten. Wenn die Datei nicht deutsch ist, tippen Sie hier einfach manuell den Namen oder Code für die jeweilige Sprache ein. Die vollständige Sprachliste entnehmen Sie bitte dem Handbuch.", wraplength=650, justify="left").pack(pady=(0, 10))

        punctuate_frame = ttk.Frame(frm)
        punctuate_frame.pack(anchor="w", pady=3)
        ttk.Checkbutton(punctuate_frame, text="Zeichensetzung bei Diktataufnahmen", variable=self.punctuate).pack(side="left")
        ttk.Button(punctuate_frame, text="?", width=2, command=self.toggle_punctuate_info).pack(side="left", padx=5)

        self.punctuate_info = ttk.Label(frm, text="Wenn Ihre Audiodatei Begriffe wie 'PUNKT' zur Kennzeichnung von Satzzeichen enthält, können diese durch Aktivieren dieser Checkbox automatisch in die entsprechenden Satzzeichen umgewandelt werden.", wraplength=650, justify="left")
        self.punctuate_info.pack_forget()

        srt_frame = ttk.Frame(frm)
        srt_frame.pack(anchor="w", pady=3)
        ttk.Checkbutton(srt_frame, text="SRT-Datei erzeugen", variable=self.include_srt).pack(side="left")
        ttk.Button(srt_frame, text="?", width=2, command=self.toggle_srt_info).pack(side="left", padx=5)

        self.srt_info = ttk.Label(frm, text="Eine SRT-Datei ist eine zeitgestempelte Textdatei. Bei Aktivierung dieser Checkbox wird automatisch neben dem normalen Text-Output (TXT-Datei) auch eine SRT-Datei erstellt.", wraplength=650, justify="left")
        self.srt_info.pack_forget()

        ttk.Button(frm, text="Transkribieren starten", command=self.start_transcription).pack(pady=10)

        self.status_label = ttk.Label(frm, text="Bereit.", foreground="lightgreen")
        self.status_label.pack(pady=10)

        ttk.Label(frm, text="(C) 2025 | Saran Nair & Andreas Weilinghoff | University of Koblenz", font=("Arial", 8)).pack(side="bottom", pady=10)

    def hide_all_info(self):
        self.punctuate_info.pack_forget()
        self.srt_info.pack_forget()

    def toggle_description(self):
        if self.description_label["text"] == self.short_text:
            self.description_label["text"] = self.full_text
            self.toggle_button["text"] = "..weniger"
        else:
            self.description_label["text"] = self.short_text
            self.toggle_button["text"] = "..mehr"

    def toggle_punctuate_info(self):
        self.hide_all_info()
        if not self.punctuate_info.winfo_ismapped():
            self.punctuate_info.pack()

    def toggle_srt_info(self):
        self.hide_all_info()
        if not self.srt_info.winfo_ismapped():
            self.srt_info.pack()


    def select_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Audio Files", "*.wav *.mp3 *.m4a *.mp4 *.mov *.ogg")])
        if files:
            self.audio_files = files
            self.file_label.config(text=f"{len(files)} Datei(en) ausgewählt")
        else:
            self.audio_files = []
            self.file_label.config(text="Keine Datei ausgewählt")

    def select_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir.set(folder)

    def start_transcription(self):
        if not self.audio_files:
            messagebox.showerror("Fehler", "Bitte wählen Sie mindestens eine Audiodatei.")
            return
        if not self.output_dir.get():
            messagebox.showerror("Fehler", "Bitte wählen Sie einen Speicherort.")
            return

        save_settings({
            "model": self.model_choice.get(),
            "output_dir": self.output_dir.get(),
            "language": self.language_choice.get(),
            "punctuate": self.punctuate.get(),
            "include_srt": self.include_srt.get()
        })

        self.status_label.config(text="Transkription läuft...", foreground="orange")
        threading.Thread(target=self.run_transcription, daemon=True).start()

    def run_transcription(self):
        for file in self.audio_files:
            try:
                temp_dir = tempfile.mkdtemp()
                local_path = os.path.join(temp_dir, os.path.basename(file))
                shutil.copy(file, local_path)

                logging.info("Starting transcription for: %s", file)
                self.status_label.config(text=f"Verarbeite: {os.path.basename(file)}")

                transcribe_audio_file(
                    local_path,
                    self.output_dir.get(),
                    self.model_choice.get(),
                    self.language_choice.get(),
                    self.punctuate.get(),
                    self.include_srt.get()
                )
                logging.info("Finished transcription for: %s", file)
            except Exception as e:
                logging.error("Error processing %s: %s", file, str(e))
                messagebox.showerror("Fehler bei Transkription", str(e))
        self.status_label.config(text="Fertig!", foreground="green")

if __name__ == '__main__':
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()