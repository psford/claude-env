"""Full vision sweep of all Sphero indi FCC photos via Claude (Anthropic).

Reads: 7 high-res photos + their quadrant crops + unread original-exhibit
photos + BOLT+ exhibit photos. Appends each transcription to
/tmp/sphero-indi/fcc/claude-readings.txt under a ===== header.
"""
import glob
import os
import sys
import time

sys.path.insert(0, '/Users/patrickford/projects/claude-env/polytoken/mcp')
import zai_vision_mcp as m  # noqa: E402

OUT = '/tmp/sphero-indi/fcc/claude-readings.txt'

FULL_PROMPT = (
    'Photo from an FCC teardown of a Sphero indi toy car. Transcribe EVERY chip '
    'marking and all silkscreen text you can see, verbatim, line by line, per '
    'component: chip top-marks, shielded module text/QR, floor-facing color '
    'sensor, motor driver, connectors, test-pad labels, board name/revision. '
    'Write illegible for anything unreadable. End with one line on what the photo shows.'
)
CROP_PROMPT = (
    'Zoomed crop of an FCC teardown photo of a Sphero indi. Transcribe every '
    'printed or laser-etched character visible, verbatim, grouped per component: '
    'chip top-marks line by line, silkscreen labels, shield-can text, pad labels. '
    'State the package style and approximate pin count of the largest chip. '
    'Write illegible for anything unreadable.'
)


def quad_crops(src, outdir, tag):
    from PIL import Image
    os.makedirs(outdir, exist_ok=True)
    im = Image.open(src)
    w, h = im.size
    outs = []
    for name, box in {
        'tl': (0, 0, w // 2, h // 2), 'tr': (w // 2, 0, w, h // 2),
        'bl': (0, h // 2, w // 2, h), 'br': (w // 2, h // 2, w, h),
    }.items():
        p = f'{outdir}/{tag}-{name}.jpg'
        im.crop(box).save(p, quality=92)
        outs.append(p)
    return outs


def main():
    jobs = []
    # 1) high-res full photos
    for p in sorted(glob.glob('/tmp/sphero-indi/fcc/hires/x*.jpg')):
        jobs.append((p, FULL_PROMPT))
    # 2) quadrant crops of the high-res photos (2x effective zoom)
    for p in sorted(glob.glob('/tmp/sphero-indi/fcc/hires/x*.jpg')):
        tag = os.path.basename(p).replace('.jpg', '')
        for c in quad_crops(p, '/tmp/sphero-indi/fcc/hires-crops', tag):
            jobs.append((c, CROP_PROMPT))
    # 3) unread original-exhibit photos
    done = {'p8-x28', 'p8-x29'}
    for p in sorted(glob.glob('/tmp/sphero-indi/fcc/original/p*.jpg')):
        if os.path.basename(p).replace('.jpg', '') not in done:
            jobs.append((p, FULL_PROMPT))
    # 4) BOLT+ exhibit photos (corroboration, newer generation)
    for p in sorted(glob.glob('/tmp/sphero-indi/fcc/boltplus/p*.jpg')):
        jobs.append((p, FULL_PROMPT.replace('Sphero indi', 'Sphero BOLT+')))

    print(f'{len(jobs)} images queued', flush=True)
    # resume support: skip images already transcribed in a previous run
    done_names = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            if line.startswith('===== '):
                done_names.add(line.strip().strip('=').strip())
    jobs = [(p, pr) for p, pr in jobs if p.replace('/tmp/sphero-indi/fcc/', '') not in done_names]
    print(f'{len(jobs)} remain after resume-skip', flush=True)
    ok = fail = 0
    for i, (path, prompt) in enumerate(jobs):
        name = path.replace('/tmp/sphero-indi/fcc/', '')
        try:
            text = m.read_image(path, prompt, None)
        except Exception as e:  # noqa: BLE001
            text = f'error: {type(e).__name__}: {e}'
        if text.startswith('error'):
            fail += 1
        else:
            ok += 1
        with open(OUT, 'a') as f:
            f.write(f'\n===== {name} =====\n{text}\n')
        print(f'[{i + 1}/{len(jobs)}] {name}: {"OK" if not text.startswith("error") else text[:80]}', flush=True)
        time.sleep(1)
    print(f'done: {ok} ok, {fail} failed -> {OUT}', flush=True)


if __name__ == '__main__':
    main()
