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


def wave_pool(d):
    """Region/file pool entries from the format blocks tagged 'EVAW' (reversed 'WAVE')
    or 'FFIA' (reversed 'AIFF'). Each entry (offsets relative to the tag):
        +0x04 u32  source file size in bytes        (WAVE)
        +0x0c u32  source file length in sample FRAMES
        +0x10 u32  sample rate (Hz)
        +0x14 u16  channels   +0x16 u16  bits/sample
        +0x70 u32  this entry's length in FRAMES  (region length; == file length if untrimmed)
    Region length in seconds = frames@+0x70 / rate@+0x10.  (KNOWN: ground truth d/e/f.)
    The region's own name (embeds the source basename) follows the length field."""
    out = []
    for m in re.finditer(b"EVAW|FFIA", d):
        o = m.start()
        if o + 0x74 > len(d):
            continue
        rate = struct.unpack_from("<I", d, o + 0x10)[0] or 44100
        frames = struct.unpack_from("<I", d, o + 0x70)[0] & 0xFFFFFF
        runs = re.findall(rb"[ -~]{2,}", d[o + 0x74:o + 0x74 + 0x40])
        out.append(dict(off=o, fmt=d[o:o+4][::-1].decode("latin1"),
                        file_bytes=struct.unpack_from("<I", d, o + 4)[0],
                        file_frames=struct.unpack_from("<I", d, o + 0x0c)[0],
                        rate=rate,
                        channels=struct.unpack_from("<H", d, o + 0x14)[0],
                        bits=struct.unpack_from("<H", d, o + 0x16)[0],
                        length_frames=frames,
                        length_sec=frames / rate,
                        name=runs[0].decode("latin1", "replace").strip() if runs else ""))
    return out


def region_length_sec_by_file(d):
    """Map pooled filename (lower) -> region length in seconds, by matching each
    pool entry's embedded region name to a filename stem. NOTE: there is ONE pool
    entry per source FILE, not per arrange placement -- a file placed multiple times
    (e.g. a looped clip) shares one region length; per-placement length is not stored
    here (cap by the gap to the next placement for looped/sub-clip cases)."""
    files = list(file_handles(d).values())
    stems = {f.rsplit(".", 1)[0].lower(): f for f in files}
    out = {}
    for w in wave_pool(d):
        nm = w["name"].lower()
        hit = stems.get(nm.rsplit(".", 1)[0].lstrip()) or \
              next((fn for st, fn in stems.items() if st and st in nm), None)
        if hit and hit.lower() not in out:
            out[hit.lower()] = w["length_sec"]
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    d = open(sys.argv[1], "rb").read()
    print(f"{sys.argv[1]}")
    print(f"  tempo = {tempo_bpm(d):.4f} BPM")
    regs = regions(d)
    print(f"  {len(regs)} distinct audio regions (position):")
    for r in sorted(regs, key=lambda r: (r["file"], r["bar"])):
        print(f"    {r['file']:<34} bar {r['bar']:7.2f}  (ticks {r['ticks']})")
    pool = wave_pool(d)
    print(f"  {len(pool)} WAVE pool entries (length @ EVAW+0x70):")
    for p in pool:
        print(f"    @{p['off']:#08x} {p['rate']}Hz {p['channels']}ch/{p['bits']}b  "
              f"len {p['length_frames']} frames = {p['length_sec']:.3f}s")


if __name__ == "__main__":
    main()
