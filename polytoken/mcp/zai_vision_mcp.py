#!/usr/bin/env python3
"""zai_vision_mcp.py — stdio MCP server exposing z.ai GLM vision as a tool.

Implements the Model Context Protocol over newline-delimited JSON-RPC on
stdin/stdout using only the Python standard library (no SDK dependency).

Tool: read_image(path, prompt?, model?)
  Sends the image to a z.ai vision model (default glm-4.5v, override with
  ZAI_VISION_MODEL env or the per-call `model` argument) with a transcription
  prompt and returns the model's text answer.

Auth: reads the z.ai API key from ~/.config/polytoken/secrets/zai (the same
file polytoken/config.template.yaml references), so no secret lives in config.

Logs go to stderr only — stdout is the protocol channel.
"""
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

API_URL = 'https://api.z.ai/api/paas/v4/chat/completions'
DEFAULT_MODEL = os.environ.get('ZAI_VISION_MODEL', 'glm-4.6v-flash')
KEY_PATH = os.path.expanduser('~/.config/polytoken/secrets/zai')
MAX_IMAGE_BYTES = 5 * 1024 * 1024

TOOL_DEF = {
    'name': 'read_image',
    'description': (
        'Send an image file to the z.ai GLM vision model and return its '
        'answer. Use for reading text/markings in photos, describing boards, '
        'screenshots, diagrams.'
    ),
    'inputSchema': {
        'type': 'object',
        'additionalProperties': False,
        'required': ['path'],
        'properties': {
            'path': {'type': 'string', 'description': 'Absolute or ~-relative path to the image file.'},
            'prompt': {'type': 'string', 'description': 'What to look for / transcribe. Default: describe in detail.'},
            'model': {'type': 'string', 'description': f'Vision model override (default {DEFAULT_MODEL}).'},
        },
    },
}


def log(msg):
    print(f'[zai_vision] {msg}', file=sys.stderr, flush=True)


def read_image(path, prompt, model):
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return f'error: no such file: {path}'
    size = os.path.getsize(path)
    if size > MAX_IMAGE_BYTES:
        return f'error: image is {size} bytes; convert/downscale below {MAX_IMAGE_BYTES} and retry'
    mime = mimetypes.guess_type(path)[0] or 'image/png'
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    try:
        key = open(KEY_PATH).read().strip()
    except OSError:
        return f'error: cannot read z.ai key at {KEY_PATH}'

    body = {
        'model': model or DEFAULT_MODEL,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}},
                    {'type': 'text', 'text': prompt or 'Describe this image in detail.'},
                ],
            }
        ],
        'max_tokens': 2000,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read())
        return resp['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')[:400]
        return f'error: z.ai HTTP {e.code}: {detail}'
    except Exception as e:  # noqa: BLE001
        return f'error: {type(e).__name__}: {e}'


def rpc_result(result):
    return {'jsonrpc': '2.0', 'id': None, 'result': result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            log(f'non-JSON input: {line[:80]}')
            continue
        if 'id' not in msg:  # notification
            continue
        method = msg.get('method', '')
        if method == 'initialize':
            client_proto = (msg.get('params') or {}).get('protocolVersion', '2024-11-05')
            out = rpc_result({
                'protocolVersion': client_proto,
                'capabilities': {'tools': {}},
                'serverInfo': {'name': 'zai_vision', 'version': '1.0.0'},
            })
        elif method == 'tools/list':
            out = rpc_result({'tools': [TOOL_DEF]})
        elif method == 'tools/call':
            params = msg.get('params') or {}
            args = params.get('arguments') or {}
            text = read_image(args.get('path', ''), args.get('prompt'), args.get('model'))
            out = {
                'jsonrpc': '2.0',
                'id': msg['id'],
                'result': {'content': [{'type': 'text', 'text': text}]},
            }
        elif method == 'ping':
            out = rpc_result({})
        else:
            out = {
                'jsonrpc': '2.0',
                'id': msg['id'],
                'error': {'code': -32601, 'message': f'method not found: {method}'},
            }
        out['id'] = msg['id']
        sys.stdout.write(json.dumps(out) + '\n')
        sys.stdout.flush()
        if method == 'initialize':
            log('initialized')


if __name__ == '__main__':
    main()
