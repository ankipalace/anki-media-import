# Obsfucate api key in a basic way
# to prevent bots from grabbing keys.
# Not intended to prevent manual grabbing.
# Never use this for important api keys!

from pathlib import Path
import random
import sys

google_api_key = sys.argv[1]
root_path = Path(__file__).resolve().parents[1]
google_api_file = root_path / "src" / "addon" / "google_api_key.py"


chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

code = ""
chosen = random.sample(range(0, len(chars)), len(google_api_key))
for idx, char in enumerate(chars):
    try:
        i = chosen.index(idx)
        code += f"{char}='{google_api_key[i]}'\n"
    except ValueError:
        r = random.randint(0, len(chars) - 1)  # includes end number
        code += f"{char}='{chars[r]}'\n"

code += "def get_google_api_key() -> str:\n"
code += "  return ''"

for i in chosen:
    code += "+"
    code += f"{chars[i]}"

google_api_file.write_text(code)
