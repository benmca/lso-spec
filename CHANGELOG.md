# Changelog

Each entry records what was promoted in confidence (KNOWN / PARTIAL / UNKNOWN) and the
evidence behind it. For a reverse-engineered format the audit trail is the credibility.

## 0.1.0 — 2026-06-09 (initial)

Promoted to **KNOWN**:
- Container header: magic `13 47 C0 AB`, version `0x0517`. *Evidence:* uniform across all
  sampled files.
- Root-relative pointer scheme `real_offset(P) = P − s32@0x0C`. *Evidence:* resolves the
  header directory to correctly-named environment objects.
- Tempo `BPM = s32@0x11A / 10000`. *Evidence:* matches each song's audio bar grid.
- Audio-file pool (AUFL) handle/name/path layout. *Evidence:* names + Windows paths read
  correctly; handles referenced by region records.
- Channel-strip table (113 × 204 bytes; id@+0x22, name@+0x90). *Evidence:* names decode.
- **Audio-region timeline position**: u24/u32 LE ticks, 3840 ticks/bar, +34560 (9-bar) bias.
  *Evidence:* controlled ground truth `corpus/a,b,c.LSO` (one region at bar 1/9/17 →
  34560/65280/96000, step 30720 = 8 bars); decoded clips land on integer bars across real
  songs; agrees with audio cross-correlation (hiphop 4/5 exact).

**PARTIAL:**
- Region → audio-file link via the handle field (~91% resolve; cleanest clusters match
  correlation; a minority disagree).

**UNKNOWN (named, not decoded):**
- Region **length** — not in the `0x24` arrange record; needs length-varying ground truth.
- Header pointer-directory walk; `Sequence` object payload; plugin parameter blocks.
