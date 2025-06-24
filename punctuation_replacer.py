import re

def transform_text_content(text: str) -> str:
    # Protect "§ ... Absatz" patterns from replacements
    protected_matches = re.findall(r"(?i)(§\s?\d+\sAbsatz\s?\d*)", text)
    protected_map = {match: f"§PROTECTED{index}§" for index, match in enumerate(protected_matches)}

    for original, placeholder in protected_map.items():
        text = text.replace(original, placeholder)

    replacements = {
        r"(?i)\babsatz[.,]?\b": "\n",
        r"(?i)doppelpunkt[.,]?": ":",
        r"(?i)\bpunkt[.,]?": ".",
        r"(?i)komma[.,]?": ",",
        r"(?i)nächste ziffer\.": "\nNächste Ziffer"
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)

    for original, placeholder in protected_map.items():
        text = text.replace(placeholder, original)

    text = re.sub(r"\.\s*\.", ".", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\.\s*:", ":", text)
    text = re.sub(r"\.\s*,", ",", text)
    text = re.sub(r",\s*doppel\s*\.", ":", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdoppel\s*\.", ":", text, flags=re.IGNORECASE)
    text = re.sub(r"\?\s*fragezeichen\.", "?", text, flags=re.IGNORECASE)
    text = re.sub(r"\?\?", "?", text)
    text = re.sub(r"^\.\s*", "", text, flags=re.MULTILINE)

    return text
