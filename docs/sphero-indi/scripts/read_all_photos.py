"""Batch-read FCC teardown photos via z.ai glm-4.6v-flash vision, with patient retries.

Writes results to /tmp/sphero-indi/fcc/photo-readings.txt as it goes (one
section per image). Tolerates the free tier's 1305 'overloaded' responses by
backing off and retrying. Run detached; check output file or wait for exit.
"""
import base64
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

API_URL = 'https://api.z.ai/api/paas/v4/chat/completions'
MODEL = os.environ.get('ZAI_VISION_MODEL', 'glm-4.6v-flash')
KEY_PATH = os.path.expanduser('~/.config/polytoken/secrets/zai')
OUT_PATH = '/tmp/sphero-indi/fcc/photo-readings.txt'

IMAGES = [
    # Priority first: close-ups most likely to show the SoC.
    'p8-x28', 'p7-x25', 'p6-x21', 'p7-x24',
    'p2-x3', 'p2-x4', 'p3-x7', 'p3-x8', 'p4-x11', 'p4-x12',
    'p5-x15', 'p5-x16', 'p6-x19', 'p6-x20', 'p8-x29',
]

PROMPT = (
    'Photo from an FCC teardown of a Sphero indi toy car. Transcribe EVERY chip '
    'marking and all silkscreen text you can see, verbatim, line by line, per '
    'component. Especially: main SoC (likely Nordic nRF52: N52832/N52840 plus '
    'second-line code plus date code), shielded modules, the floor-facing color '
    'sensor, motor driver chip, connectors, rows of test pads, battery, board '
    'name/revision silkscreen. If a marking is illegible, write illegible rather '
    'than guessing. End with a one-line summary of what the photo shows.'
)

key = open(KEY_PATH).read().strip()


def read_image(path):
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    body = {
        'model': MODEL,
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
                {'type': 'text', 'text': PROMPT},
            ],
        }],
        'max_tokens': 2000,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read())
    content = resp['choices'][0]['message']['content']
    if not content or not content.strip():
        raise RuntimeError('empty response')
    return content


def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)


def main():
    d = '/tmp/sphero-indi/fcc/original'
    done = {}
    for name in IMAGES:
        path = f'{d}/{name}.jpg'
        if not os.path.exists(path):
            log(f'{name}: missing jpg, skipping')
            continue
        attempt = 0
        while attempt < 60:
            attempt += 1
            try:
                content = read_image(path)
                done[name] = content
                with open(OUT_PATH, 'a') as f:
                    f.write(f'\n===== {name} =====\n{content}\n')
                log(f'{name}: OK on attempt {attempt}')
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors='replace')[:120]
                log(f'{name}: attempt {attempt} HTTP {e.code} {detail}')
                if e.code == 401 or e.code == 1211:
                    log(f'{name}: fatal, giving up on this image')
                    break
            except Exception as e:  # noqa: BLE001
                log(f'{name}: attempt {attempt} {type(e).__name__}: {e}')
            time.sleep(min(300, 20 * attempt) + random.uniform(0, 8))
        else:
            log(f'{name}: EXHAUSTED retries')
        time.sleep(5)
    log(f'batch complete: {len(done)}/{len(IMAGES)} images read; results in {OUT_PATH}')


if __name__ == '__main__':
    main()
