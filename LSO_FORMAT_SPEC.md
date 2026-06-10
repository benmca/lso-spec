# Emagic Logic `.LSO` Project File — Format Specification

Status: **working draft, reverse-engineered, read-only.** Version 0.1.0 (2026-06-09).

This is the normative prose layer. The machine-readable layout lives in [`lso.ksy`](lso.ksy)
(Kaitai Struct — compiles to parsers in Python/C++/JS/Java/Go/Rust/…). Ground-truth
samples and a conformance check are in [`corpus/`](corpus/) and [`reference/`](reference/).

## Provenance

Files written by **Emagic Logic for Windows** (Logic Platinum / Logic Audio ~5.x,
2003–2004). Identifying evidence: header magic `13 47 C0 AB`, version `u16 @ 0x04 = 0x0517`
(uniform across every sampled file), Windows drive-letter audio paths (`D:\`, `C:\`, `E:\`),
and an embedded Csound environment dump. Little-endian throughout.

## Confidence scheme

Every claim carries one of three tags (mirrored in the `.ksy` `doc:` strings):

| tag | meaning |
|-----|---------|
| **KNOWN** | empirical evidence exists (controlled ground truth, cross-validation, or invariance across the corpus) |
| **PARTIAL** | record structure decoded; some semantics or scope still uncertain |
| **UNKNOWN** | named region only; raw bytes + hypotheses |

When a field is promoted to KNOWN, the [CHANGELOG](CHANGELOG.md) cites the evidence.

---

## 1. Container & header — KNOWN (header) / PARTIAL (full map)

| offset | size | field | conf | notes |
|-------:|-----:|-------|------|-------|
| 0x00 | 4 | magic `13 47 C0 AB` | KNOWN | file signature |
| 0x04 | 2 | version `0x0517` | KNOWN | Logic 5.x; uniform |
| 0x0C | 4 | `root_off` (s32) | KNOWN | base of the pointer scheme (§2) |
| 0x11A | 4 | `tempo_raw` (s32) | KNOWN | BPM = `tempo_raw / 10000` (§4) |

The remainder of the header (≈0x10–0x800) holds a root-relative **pointer directory**
to environment objects; only partially decoded.

## 2. Root-relative pointer scheme — KNOWN

Pointers stored in the file are **biased by a root base**. To resolve a stored pointer
`P` to a file offset:

```
real_offset(P) = P − root_off          where root_off = s32 @ 0x0C
```

This is the single most important mechanism in the format, and why naïve absolute-offset
scans fail. `root_off` changes per file/save. *Evidence:* following the header directory
through this transform resolves to correctly-named environment objects.

## 3. Text encodings — KNOWN

Strings are NUL-terminated within fixed fields, **latin-1** (object/region names) or
**UTF-16LE** (some UI strings). FourCC chunk tags are stored as **reversed** ASCII:
`AUFL`→`LFUA`, `WAVE`→`EVAW`, `AIFF`→`FFIA`, `EMAG`→`GAME`.

## 4. Tempo — KNOWN

`BPM = (s32 @ 0x11A) / 10000`. Verified: hiphop 72, afterxmas 120, final 40,
Mesquite 122, kidsmelody 120, and the corpus 120.

## 5. Audio-file pool (AUFL) — KNOWN (layout) / PARTIAL (fields)

Each pooled audio file is one record found by the literal `LFUA`. Relative to the tag at
offset `T`:

| field | location | conf | notes |
|-------|----------|------|-------|
| handle (u16) | `T − 14` | KNOWN | 4-aligned object id; region records reference this |
| filename (latin-1) | `T + 10` | KNOWN | NUL-terminated |
| original path | further in | KNOWN | Windows `D:\…` etc., NUL-terminated |
| type/rate code (u16) | `T − 16` | UNKNOWN | shared across files (`0x02AE` for most WAVs) |

Audio FILE lengths/offsets inside the pool are **sample frames @ 44100** (calibrated vs
real `.aif`/`.wav` headers) — distinct from timeline positions (§7, which are ticks).

## 6. Environment (mixer) — KNOWN (table) / PARTIAL (fields)

A fixed table of **113 channel strips**, each **204 (0xCC) bytes**, reached via the header
directory. Object id at `+0x22` (step 4), latin-1 name at `+0x90`. Insert plugins carry the
`EMAG` (reversed `GAME`) signature ⇒ stock Emagic/Logic plugins.

## 7. Audio-region timeline position — **KNOWN** ✅

The deliverable field. **Cracked by controlled ground truth** (`corpus/a,b,c.LSO`: one
region saved at bar 1 / 9 / 17).

- **Encoding:** `u24`/`u32` LE, in **ticks**.
- **Resolution:** **3840 ticks/bar** = 960 ticks/quarter (4/4).
- **Bias:** constant **+34560 ticks (9 bars)**. Bar 1 is stored as 34560.
  - `bar  = ticks / 3840 − 8`
  - `ticks = (bar + 8) × 3840`
- **Where:** region sub-objects tagged **`0x24`** (bar-aligned start), layout
  `24 <pos:u32 LE> … 81 00 00 <file_handle:u16> 00 …`. The same start is written into a
  few consecutive `0x24` sub-records (arrange/matrix/overview views); de-dup by
  `(ticks, file_handle)`. Tag `0x20` carries a content/anchor offset (often off-grid) but
  is too common a byte to anchor on alone.

**Evidence (independent, agreeing):**
1. Corpus a/b/c read 34560 / 65280 / 96000 (step 30720 = 8 bars exactly).
2. Decoded clip bars land on exact integers across dozens of real clips; first clips read
   34560 (bar 1) in multiple songs ⇒ the bias is universal, not per-project.
3. Audio cross-correlation of stems vs the bounced mix independently matches the LSO bars
   (hiphop: 4 of 5 confident locks exact).

> ⚠️ This **+34560 (9-bar)** region-position bias differs from the **0x9600 (=38400, 10-bar)**
> bias the LSO2MIDI project applies to the *tempo table*. Region positions use 34560.

### Region → audio-file link — PARTIAL

A `0x24` region references its audio file by the **handle** (§5) read as the `u16` three
bytes past the first `0x81` tag following the position. ~91% of regions resolve to a valid
handle and the cleanest clusters match audio correlation exactly; a minority disagree
(likely similar/derived source audio). Reference: [`reference/lsopos.py`](reference/lsopos.py).

### Region length — **KNOWN** ✅ (cracked 2026-06-10 by length-varying ground truth)

NOT in the `0x24` arrange record (that record holds only position). Length lives in the
**WAVE region-pool entry**, tagged `EVAW` (reversed `WAVE`), and is stored in **sample
FRAMES** — not ticks. (So Logic keeps region *position* musical/ticks but region *length*
in audio samples.) Offsets relative to the `EVAW` tag at `T`:

| field | location | conf | notes |
|-------|----------|------|-------|
| source file size (bytes) | `T+0x04` u32 | KNOWN | matches the real `.wav` byte size |
| source file length (frames) | `T+0x0C` u32 | KNOWN | full file, in sample frames |
| sample rate (Hz) | `T+0x10` u32 | KNOWN | 44100 in the corpus |
| channels / bits | `T+0x14` u16 / `T+0x16` u16 | KNOWN | e.g. 1 / 16 |
| **region length (frames)** | `T+0x70` u32 | **KNOWN** | this entry's length; `== file length` when untrimmed |

`region_length_seconds = frames@(T+0x70) / rate@(T+0x10)`.

*Evidence:* ground truth `corpus/d,e,f.LSO` — one region at bar 1 resized to 2 / 3 / 5 bars
reads `176400 / 264600 / 441000` frames at `EVAW+0x70` (= 4.0 / 6.0 / 10.0 s at 44100 =
exactly 2 / 3 / 5 bars at 120 BPM). Untrimmed entries read 705600 (the full 8-bar file).

### Region → length association — PARTIAL

Each placed region has its own `EVAW` entry (plus a full-length entry per source file, and
undo-history duplicates). Matching a length to its arrange placement (by region name / parent
file) is the same open association problem as the region→file link above.

## 8. Sentinels & invariants — KNOWN

- `0x7FFFFFF1` (`F1 FF FF 7F`) terminates object/event streams.
- `0xFFFF` is a recurring object-id sentinel.
- Object ids are 4-aligned 16-bit handles.
- Save reorganizes the file wholesale (no stable byte alignment between saves); diffs must
  be structural, not positional.

## Open items (toward a complete spec)

- Region **length** (§7) — needs the length-varying ground truth.
- The header **pointer directory** walk (to enumerate objects top-down instead of scanning).
- The **`Sequence`** object payload (Hyper Draw lanes; likely holds region definitions).
- Tighten region→file handle extraction for older record variants.
- Plugin parameter blocks (only names recovered so far).
