"""One-off probe: send an image to z.ai glm-4.5v and print the response.

Usage: python3 zai_vision_probe.py <image-path> [prompt]
Reads the API key from ~/.config/polytoken/secrets/zai
"""
import base64
import json
import os
import sys
import urllib.request

API_URL = 'https://api.z.ai/api/paas/v4/chat/completions'
MODEL = os.environ.get('ZAI_VISION_MODEL', 'glm-4.5v')

img_path = sys.argv[1]
prompt = sys.argv[2] if len(sys.argv) > 2 else 'Describe this image in detail.'
key = open(os.path.expanduser('~/.config/polytoken/secrets/zai')).read().strip()

with open(img_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

body = {
    'model': MODEL,
    'messages': [
        {
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
                {'type': 'text', 'text': prompt},
            ],
        }
    ],
    'max_tokens': 1500,
}

req = urllib.request.Request(
    API_URL,
    data=json.dumps(body).encode(),
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
)
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read())
    print(resp['choices'][0]['message']['content'])
except urllib.error.HTTPError as e:
    print('HTTP', e.code, e.read().decode()[:500])
