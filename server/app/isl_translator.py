# server/app/isl_translator.py
import json
from typing import List, Dict
class ISLTranslator:
    def __init__(self, mapping_path):
        with open(mapping_path, 'r', encoding='utf8') as f:
            self.mapping = json.load(f)  # e.g., {"hello":[{"sign":"sign_hello","duration":1.0}], ...}

    def translate(self, text: str) -> List[Dict]:
        text = text.lower()
        # simple token matching: longest phrase first
        seq = []
        words = text.split()
        i = 0
        while i < len(words):
            matched = False
            # try 3-word ngrams down to 1
            for L in (3,2,1):
                if i+L <= len(words):
                    phrase = ' '.join(words[i:i+L])
                    if phrase in self.mapping:
                        entries = self.mapping[phrase]
                        for e in entries:
                            # e might be {"sign":"sign_hello","duration":1.0}
                            seq.append({'sign': e['sign'], 'start': sum(x.get('duration',1.0) for x in seq), 'duration': e.get('duration',1.0)})
                        i += L
                        matched = True
                        break
            if not matched:
                # fallback: skip word
                i += 1
        return seq
