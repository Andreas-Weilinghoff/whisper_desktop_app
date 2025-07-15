# transcriber.py
import whisper
import os
from punctuation_replacer import transform_text_content
from generate_srt import generate_srt

def transcribe_audio_file(filepath, output_dir, model_name="base", language="de", 
                          diarize=False, apply_punctuation=False, generate_srt_file=False):
    model = whisper.load_model(model_name)
    result = model.transcribe(filepath, language=language)

    if not isinstance(result, dict) or "text" not in result:
        raise ValueError("Invalid Whisper transcription output")

    text = result["text"]
    if apply_punctuation:
        text = transform_text_content(text)

    base = os.path.splitext(os.path.basename(filepath))[0]
    txt_path = os.path.join(output_dir, f"{base}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    if generate_srt_file and "segments" in result:
        srt_text = generate_srt(result["segments"])
        srt_path = os.path.join(output_dir, f"{base}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_text)