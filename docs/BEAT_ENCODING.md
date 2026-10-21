# Beat Encoding

Every beat on every lead is described by a **16-number vector**, its *encoding*. The encoding
captures the beat's **shape**. Beats that look alike have encodings that point in the same
direction, and beats that look different point elsewhere. Timing such as heart rate or the RR
interval does not enter it.

This lets you compare beat shapes without hand-made features:

- **Find the record's normal beat:** the direction most beats point in
  (`examples/normal_beat.py`).
- **Find a representative beat:** the real beat closest to that direction
  (`examples/closest_beat.py`).
- **Find beats that look unusual:** low similarity to the normal shape. PVCs, aberrant beats and
  noise stand out.
- **Group beats by shape:** cluster the encodings (k-means, DBSCAN, ...).
- **Find beats like this one:** a nearest-neighbour search.

## Where it is in the report

The `/beat_encoding` group of the H5 report. `L` is the number of analyzed leads (in the order they
were analyzed) and `N` the number of beats.

| Dataset | Type | Shape | Description |
| --- | --- | --- | --- |
| `encoding` | float32 | `(L, N, 16)` | Encoding of beat `i` on lead `l` at `[l, i]`. Unit length; NaN where `status` is not 0 |
| `status` | uint8 | `(L, N)` | 0 when the beat was encoded on that lead, otherwise the reason it was not (below) |
| `lead_ok` | uint8 | `(L, N)` | 1 when that lead's signal quality was good at the beat. Informational: it does not block encoding |
| `t_estimated` | uint8 | `(N,)` | 1 when the beat had no detected T wave and its T offset was estimated |
| `t_offset_ms` | int64 | `(N,)` | The beat's T offset, detected or estimated; −1 if none |

The group's attributes:

| Attribute | Value |
| --- | --- |
| `dim` | 16 |
| `metric` | `cosine` |
| `version_key` | Identifies the encoder version. **Only compare encodings with the same key** |

The group is missing when the encoder did not run, for example in animal analyses.

```python
import h5py, numpy as np

with h5py.File('report.h5') as f:
    enc = f['beat_encoding/encoding'][0]          # lead 0: (N, 16)
    ok = f['beat_encoding/status'][0] == 0        # encoded beats
```

## Comparing encodings

Encodings are unit vectors, so the **cosine similarity** of two beats is their dot product:

```python
similarity = enc[i] @ enc[j]      # 1 = same shape, 0 = unrelated, -1 = opposite
similarity_to_all = enc @ enc[i]  # beat i against every beat, (N,)
```

Euclidean distance ranks beats the same way (`|a − b|² = 2 − 2 a·b`), so any nearest-neighbour or
clustering library works as is.

Rules of thumb:

- **Compare beats on the same lead.** The same beat looks different on different leads, so its
  encodings differ too.
- **Compare encodings with the same `version_key`.** Encodings from a different encoder version
  live in a different space.
- **Skip beats where `status` is not 0** (their encoding is NaN). For clean results, also skip beats
  where `lead_ok` is 0 or `/beat_table/good_quality` is 0. `report_h5.encoded_beats()` does both.
- **Similarities are relative.** The same morphology on a noisy lead scores lower. Compare
  similarities within a record and lead rather than against a fixed threshold.

## Finding the normal beat

Most beats in most recordings are the patient's normal beat, so the average direction of all
encodings points toward the normal shape. Outliers (PVCs, noise) pull a plain average, so
`report_h5.normal_centroid()` trims them:

```python
centroid = enc.mean(axis=0)
centroid /= np.linalg.norm(centroid)
keep = np.argsort(-(enc @ centroid))[:len(enc) // 2]    # the closest half
centroid = enc[keep].mean(axis=0)
centroid /= np.linalg.norm(centroid)
```

Then:

- **The 50 most typical beats** are `np.argsort(-(enc @ centroid))[:50]`. Averaging their signal
  aligned on the QRS onset gives a clean template beat (`examples/normal_beat.py`).
- **The single most typical beat** is `np.argmax(enc @ centroid)`. It is a real beat with real
  onsets, offsets and peaks (`examples/closest_beat.py`).
- **Unusual beats** are those with the lowest `enc @ centroid`. In the example recording
  (`example_files/mitdb_221_60s.edf`, an AF record with 12 PVCs) the 12 PVCs are exactly the 12
  least similar beats on lead 1, at a similarity near 0.2 against about 0.95 for the normal beats.

If a recording is mostly ectopic or paced, the dominant shape is that shape. "Normal" here means
*the most common*, not *clinically normal*.

## Status codes

| Value | Name | Meaning |
| --- | --- | --- |
| 0 | OK | Encoded |
| 1 | NO_T | No T offset, detected or estimated |
| 2 | BAD_T | The T wave's onset and offset are inconsistent |
| 3 | TOO_SHORT | The beat is too short to encode |
| 4 | TOO_LONG | The beat is too long to encode |
| 5 | EDGE | The beat runs past the start or end of the recording |
| 6 | FLAT | The lead is flat over the beat |
| 7 | QUALITY | Reserved, never written (see `lead_ok`) |

The last beat of a recording is often `EDGE`.
