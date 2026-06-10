# lso-spec — Emagic Logic `.LSO` format specification

A reverse-engineered, read-only specification of the **Emagic Logic for Windows**
(Logic Platinum / Logic Audio ~5.x, 2003–2004) project file format, aimed at anyone
building a parser.

It is published as four layers:

| layer | file | purpose |
|-------|------|---------|
| **grammar** | [`lso.ksy`](lso.ksy) | [Kaitai Struct](https://kaitai.io) description — compiles to parsers in Python, C++, JS, Java, Go, Rust, C#, … and visualizes in the Web IDE |
| **prose** | [`LSO_FORMAT_SPEC.md`](LSO_FORMAT_SPEC.md) | normative semantics: units, biases, the pointer scheme, and per-field **KNOWN / PARTIAL / UNKNOWN** confidence with evidence |
| **corpus** | [`corpus/`](corpus/) | ground-truth sample files + expected parse fixtures |
| **reference** | [`reference/`](reference/) | a stdlib-only Python reader and a corpus conformance check |

## Why these choices

ASN.1 and similar abstract-syntax tools assume the bytes follow a standardized encoding
rule; `.LSO` is an application-private layout (root-relative pointers, biased integers,
reversed FourCC tags, sentinel-terminated streams) that no standard ER describes. A binary
**grammar DSL** (Kaitai) expresses that layout directly *and* generates working parsers, so
it is the executable core; the prose layer carries the semantics a grammar can't, and —
crucially for reverse-engineered work — the **confidence and evidence** behind every claim.

## Quick start

```sh
# Reference reader (no dependencies):
python3 reference/lsopos.py corpus/a.LSO

# Conformance check (parses the ground truth, asserts the decoded positions):
python3 reference/validate_corpus.py

# Generate a parser from the grammar (needs the Kaitai compiler):
kaitai-struct-compiler -t python lso.ksy
# …or open lso.ksy in the Kaitai Web IDE to parse a file interactively.
```

## Status (v0.2.0)

**KNOWN:** container/header, root-relative pointer scheme, text encodings, tempo, audio-file
pool, channel-strip table, sentinels, the **audio-region timeline position** (ticks, 3840/bar,
+34560 bias), and the **region length** (sample frames @ `EVAW+0x70`) — both cracked by
controlled ground truth; position also cross-validated against audio correlation.

**Open:** associating each length/handle to its arrange placement (the region→file/length
link), the header pointer-directory walk, and the `Sequence` object payload. See
[`LSO_FORMAT_SPEC.md`](LSO_FORMAT_SPEC.md) §"Open items" and [`CHANGELOG.md`](CHANGELOG.md).

## License

Specification text, grammar, and reference code: CC0-1.0 (public domain). The corpus holds
small synthetic test projects only — no third-party audio.
