#!/usr/bin/env python3
"""Reference reader for the Emagic Logic .LSO timeline-position field.

Self-contained (stdlib only). Companion to lso.ksy / LSO_FORMAT_SPEC.md. Decodes:
  * tempo (BPM)
  * the audio-file pool (handle -> filename)
  * audio-region placements (timeline position in bars, + referenced file)

Position encoding (KNOWN, cracked by the corpus/ ground truth a/b/c.LSO):
  region position = u24/u32 LE in TICKS; 3840 ticks/bar (960/quarter, 4/4);
  constant +34560-tick (9-bar) bias.  bar = ticks/3840 - 8.

Usage:  python3 lsopos.py <file.LSO>
"""
import sys, struct, re

TICKS_PER_BAR = 3840
BIAS = 34560                 # = 9 * 3840 ; bar 1 -> 34560
MAX_TICKS = BIAS + 1300 * TICKS_PER_BAR


def tempo_bpm(d):
    return struct.unpack_from("<i", d, 0x11A)[0] / 10000.0


def ticks_to_bar(t):
    return (t - BIAS) / TICKS_PER_BAR + 1


def file_handles(d):
    """{handle:u16 -> filename} from the AUFL ('LFUA') pool. Handle = u16 @ tag-14."""
    out = {}
    for m in re.finditer(b"LFUA", d):
        o = m.start()
        if o < 14:
            continue
        handle = struct.unpack_from("<H", d, o - 14)[0]
        name = d[o + 10:o + 10 + 60].split(b"\x00")[0].decode("latin1", "replace")
        if name and handle not in out:
            out[handle] = name
    return out


def _handle_after(d, o):
    """Audio-file handle a 0x24 region references: u16 three bytes past the first
    0x81 tag following the 4-byte position (layout: ...81 00 00 <handle:u16> 00...)."""
    for j in range(o + 5, o + 14):
        if d[j] == 0x81:
            return struct.unpack_from("<H", d, j + 3)[0]
    return None


def regions(d):
    """Distinct audio regions: [{off, ticks, bar, handle, file}], deduped by
    (ticks, handle). The file stores a near-duplicate 2nd block (a 2nd track/view)."""
    hmap = file_handles(d)
    raw = []
    for o in range(1, len(d) - 20):
        if d[o] != 0x24:
            continue
        ticks = struct.unpack_from("<I", d, o + 1)[0]
        if not (BIAS <= ticks <= MAX_TICKS):
            continue
        h = _handle_after(d, o)
        if h not in hmap:
            continue
        raw.append((o, ticks, h))
    seen, out = set(), []
    for o, ticks, h in sorted(raw):
        if (ticks, h) in seen:
            continue
        seen.add((ticks, h))
        out.append(dict(off=o, ticks=ticks, bar=ticks_to_bar(ticks),
                        handle=h, file=hmap[h]))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    d = open(sys.argv[1], "rb").read()
    print(f"{sys.argv[1]}")
    print(f"  tempo = {tempo_bpm(d):.4f} BPM")
    regs = regions(d)
    print(f"  {len(regs)} distinct audio regions:")
    for r in sorted(regs, key=lambda r: (r["file"], r["bar"])):
        print(f"    {r['file']:<34} bar {r['bar']:7.2f}  (ticks {r['ticks']})")


if __name__ == "__main__":
    main()
