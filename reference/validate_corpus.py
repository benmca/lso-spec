#!/usr/bin/env python3
"""Conformance check: parse the ground-truth corpus and assert the decoded fields
match what was set in Logic. Keeps the spec honest as it evolves.

  a/b/c.LSO : one region at bar 1/9/17  -> position 34560/65280/96000 ticks.
  d/e/f.LSO : one region at bar 1, length 2/3/5 bars -> 176400/264600/441000 frames.
"""
import os, sys, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lsopos

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "corpus")

def main():
    failures = 0
    for name in ("a", "b", "c", "d", "e", "f"):
        exp = json.load(open(os.path.join(CORPUS, "expected", f"{name}.json")))
        d = open(os.path.join(CORPUS, f"{name}.LSO"), "rb").read()
        bpm = lsopos.tempo_bpm(d)

        # position: the test region's tick value must appear at a 0x24 tag
        raw_pos = {struct.unpack_from("<I", d, o+1)[0]
                   for o in range(1, len(d)-6) if d[o] == 0x24}
        pos_ok = exp["expected_position_ticks"] in raw_pos

        # length (d/e/f): the expected frame count must appear as a WAVE-pool length
        len_ok = True
        if "expected_length_frames" in exp:
            lens = {p["length_frames"] for p in lsopos.wave_pool(d)}
            len_ok = exp["expected_length_frames"] in lens

        ok = pos_ok and len_ok and abs(bpm - exp["tempo_bpm"]) < 0.01
        if not ok:
            failures += 1
        extra = ""
        if "expected_length_frames" in exp:
            extra = (f"  len {exp['expected_length_frames']}f "
                     f"({exp['region_length_bars']}bar) -> {'found' if len_ok else 'MISSING'}")
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}.LSO  bar {exp['region_bar']:>2}  "
              f"pos {exp['expected_position_ticks']} -> {'found' if pos_ok else 'MISSING'}"
              f";  tempo {bpm:.2f}{extra}")
    print("PASS" if not failures else f"{failures} FAILURE(S)")
    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()
