# Corpus

Ground-truth sample `.LSO` files and their expected parse fixtures. These are the evidence
behind the KNOWN claims in the spec and the input to `reference/validate_corpus.py`.

## Files

| file | tempo | contents | purpose |
|------|------:|----------|---------|
| `a.LSO` | 120 | one audio region (TEST.WAV) at **bar 1** | position field ground truth |
| `b.LSO` | 120 | same region at **bar 9** | " |
| `c.LSO` | 120 | same region at **bar 17** | " |

`expected/{a,b,c}.json` record the tempo and the expected decoded position in ticks
(34560 / 65280 / 96000 — bar 1/9/17 under the +34560 bias).

## Provenance

Created in **Emagic Logic Platinum 5.5.1** running on **Windows XP** under **UTM/QEMU**
(emulated i386, i440FX+PIIX). A single audio region was placed at bar 1, then moved +8 bars
per save, isolating the timeline-position field for a clean structural diff. Only the
synthetic TEST.WAV project is included here — **no third-party or personal audio**.

## Adding to the corpus

Keep samples small and synthetic, and pair each with an `expected/*.json` fixture stating
what was set in Logic so the conformance check can verify the decode. The next planned
addition is a **length-varying** set (one region at a fixed bar, saved at lengths 2/4/6
bars) to crack the region-length field.
