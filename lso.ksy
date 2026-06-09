meta:
  id: lso
  title: Emagic Logic Platinum 5.x project file (.LSO)
  file-extension: lso
  endian: le
  encoding: latin1
  license: CC0-1.0
doc: |
  Emagic Logic for Windows (Logic Platinum / Logic Audio ~5.x, 2003-2004) project
  file. This grammar is REVERSE-ENGINEERED from a read-only corpus; it is read-only
  and intentionally partial. Every field carries a confidence tag in its `doc:`
  string:

    KNOWN   - empirical evidence exists (cited in LSO_FORMAT_SPEC.md).
    PARTIAL - structure decoded, semantics or scope uncertain.
    UNKNOWN - named region, raw bytes, hypotheses only.

  The full prose specification, evidence, and the pointer scheme live in
  LSO_FORMAT_SPEC.md. The corpus/ directory holds ground-truth samples and the
  reference/ directory a Python reference reader + corpus validator.

  NOTE ON DISCOVERY: most objects are reached through a root-relative pointer
  directory in the header (see `root_off`), which is not yet fully decoded. The
  types below therefore describe the *record layouts* (parse one given its offset)
  rather than a single top-down walk. The audio-region placements in particular are
  located today by scanning the arrange section for the 0x24 tag byte.

seq:
  - id: magic
    contents: [0x13, 0x47, 0xc0, 0xab]
    doc: 'KNOWN. File signature, identical across all known files.'
  - id: version
    type: u2
    doc: 'KNOWN. 0x0517 => Logic 5.x. Uniform across the corpus.'

instances:
  root_off:
    pos: 0x0c
    type: s4
    doc: |
      KNOWN. Base for the root-relative pointer scheme. A stored pointer P is
      resolved to a file offset as:  real_offset = P - root_off.
      This is why naive absolute-offset scans fail. Value differs per file/save.

  tempo_raw:
    pos: 0x11a
    type: s4
    doc: 'KNOWN. Song tempo, fixed-point. See tempo_bpm.'

  tempo_bpm:
    value: tempo_raw / 10000.0
    doc: |
      KNOWN. Beats per minute = tempo_raw / 10000.
      Verified: hiphop 72, afterxmas 120, final 40, Mesquite 122, kidsmelody 120.

enums:
  # Single-byte type tags seen in the arrange/object stream.
  region_tag:
    0x24: region_start    # bar-aligned timeline start of an audio region placement
    0x20: content_offset  # content/anchor offset (often off-grid); also Hyper Draw runs

  chunk_tag:
    # Chunk tags are stored as REVERSED FourCCs (read 4 bytes, reverse them).
    0x4c465541: aufl      # 'AUFL' reversed -> audio-file pool entry
    0x45564157: wave      # 'WAVE'
    0x46464941: aiff      # 'AIFF'
    0x47414d45: emag      # 'EMAG' -> Emagic (stock) plugin signature

types:

  # ---- Audio-region timeline placement -----------------------------------
  region_placement:
    doc: |
      PARTIAL (position field itself is KNOWN). One audio-region arrange placement.
      Located by scanning the arrange section for tag 0x24. Layout:
        24 <pos:u4> .. <0x81> 00 00 <file_handle:u2> 00 <fine:s2> <range:u2> ..
      The same region's start is written into a few consecutive 0x24 sub-records
      (arrange / matrix / overview views); de-duplicate by (pos_ticks, file_handle).
    seq:
      - id: tag
        type: u1
        enum: region_tag
        doc: 'KNOWN. 0x24 for a region-start placement.'
      - id: pos_ticks
        type: u4
        doc: |
          KNOWN. Timeline position in TICKS (low 24 bits used). 3840 ticks/bar
          (960 ticks/quarter, 4/4), biased by +34560 ticks (= 9 bars). So bar 1 is
          stored as 34560. Cracked by controlled ground truth: corpus a/b/c hold one
          region at bar 1 / 9 / 17 and read 34560 / 65280 / 96000 (step 30720 = 8 bars).
          Cross-validated against audio correlation (hiphop, 4/5 exact). See `bar`.
    instances:
      bar:
        value: (pos_ticks - 34560) / 3840.0 + 1
        doc: 'KNOWN. 1-based musical bar. bar = (pos_ticks - 34560) / 3840 + 1.'
      beats_from_start:
        value: (pos_ticks - 34560) / 960.0
        doc: 'KNOWN. Quarter-note beats from bar 1 beat 1.'
      # NOTE: file_handle and the region LENGTH are not modelled here yet --
      # handle is read heuristically (u2 three bytes past the first 0x81 after pos);
      # length is UNKNOWN (not present in this record -- needs length-varying ground
      # truth). See reference/lsopos.py and LSO_FORMAT_SPEC.md sec. "Region length".

  # ---- Audio-file pool entry (AUFL) --------------------------------------
  aufl_entry:
    doc: |
      KNOWN (layout) / PARTIAL (all fields). One audio-file pool record. Found by the
      literal 'LFUA' (the reversed 'AUFL' tag). The per-file HANDLE (a 4-aligned u16
      object id) sits 14 bytes before the tag; the filename 10 bytes after it. The
      original Windows path (D:\ / C:\ / E:\) appears further inside the record.
    seq:
      - id: handle
        type: u2
        doc: 'KNOWN. 4-aligned object handle (region records reference this).'
      - id: unknown_idx
        type: u2
        doc: 'PARTIAL. Pairs with a shared type/rate code word.'
      - id: type_or_rate
        type: u2
        doc: 'UNKNOWN. Shared across files (0x02ae for most WAVs); format/rate code?'
    # (positioned parsing of name/path is done in the reference reader, not modelled
    #  positionally here -- the tag is discovered by scan.)

  # ---- Environment channel strip -----------------------------------------
  channel_strip:
    doc: |
      KNOWN (record size & two fields) / PARTIAL (rest). One mixer channel strip.
      The environment holds a fixed table of 113 of these, each 204 (0xCC) bytes,
      reached via the header object directory. Object id at +0x22 (step 4), the
      latin-1 name at +0x90.
    seq:
      - id: body
        size: 0xcc
        doc: 'PARTIAL. 204-byte record; id @ +0x22, name @ +0x90 within this body.'

  end_marker:
    doc: 'KNOWN. 0x7FFFFFF1 (bytes f1 ff ff 7f) terminates object/event streams.'
    seq:
      - id: marker
        contents: [0xf1, 0xff, 0xff, 0x7f]
