import os
from dotenv import load_dotenv

load_dotenv()
b64 = os.environ.get('GOOGLE_SHEETS_CREDENTIALS_B64', '')

with open('render.yaml', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the first `sync: false` under GOOGLE_SHEETS_CREDENTIALS_B64
# We will use exactly replace to inject the value
target = """      - key: GOOGLE_SHEETS_CREDENTIALS_B64
        sync: false"""
replacement = f"""      - key: GOOGLE_SHEETS_CREDENTIALS_B64
        value: "{b64}" """

content = content.replace(target, replacement)

with open('render.yaml', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated render.yaml')
