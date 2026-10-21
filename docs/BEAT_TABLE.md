# The Beat Table

The H5 report describes every beat the analysis found, one row per beat, in time order. The data is
spread over three groups that all have one entry per beat (`N = /meta/total_beats`):

| Group | What it holds |
| --- | --- |
| `/beats` | Where each beat is: P, QRS and T onsets and offsets |
| `/beat_table` | What each beat measures: intervals, heart rate, quality, rhythm and ectopic scores, flags |
| `/beat_peaks` | Peak positions, amplitudes and shapes, per lead (when present) |

`examples/beat_table_to_csv.py` writes all of it to one CSV, and `report_h5.read_beat_table()`
returns it as a pandas DataFrame.

## Conventions

- **Times** are milliseconds from the start of the recording.
- **Sampling.** The analysis runs at 250 Hz, so every time is a multiple of 4 ms. To find a time in
  your own signal, use `sample = ms * fs / 1000`.
- **Missing intervals are 0, not NaN.** A beat without a P wave has `pr = 0`; the last beat has
  `rr = 0`. Drop zeros before averaging. In the CSV, the P and T onsets and offsets are empty when the
  wave is missing.
- **Booleans** are stored as `uint8` 0 / 1.
- **Beat index.** Row `i` of every group is the same beat. Events refer to beats by this index.

## `/beats`: wave geometry

| Column | Type | Description |
| --- | --- | --- |
| `r` | uint64 | QRS onset. Despite the name, this is the **onset**, not the R peak. The R peak is in `/beat_peaks/r_peak_ms` |
| `r_end` | uint64 | QRS offset |
| `has_t` | uint8 | 1 when a T wave was found |
| `t_start`, `t_end` | uint64 | T onset and offset; 0 when `has_t` is 0 |
| `p_wave_count` | uint32 | Number of P waves of the beat (0, 1, or more in heart block) |
| `p_waves_start`, `p_waves_end` | uint64, `(P,)` | P onsets and offsets, all beats back to back |

A beat can have several P waves, so the P waves are stored flat. Beat `i`'s P waves are the
`p_wave_count[i]` entries starting at `sum(p_wave_count[:i])`. The last one is the conducted P wave
used for the PR interval. `report_h5.read_beat_list()` rebuilds the list as Python objects:

```python
beats = report_h5.read_beat_list('report.h5')
beats[1]
# Beat(index=1, qrs=Wave(start=704, end=784), p_waves=[Wave(start=588, end=656)], t=Wave(start=848, end=1024))
```

The CSV names these `qrs_onset_ms`, `qrs_offset_ms`, `t_onset_ms`, `t_offset_ms`, `p_onset_ms`,
`p_offset_ms`. The CSV keeps only the last P wave of each beat.

## `/beat_table`: measurements

### Intervals (ms)

| Column | Definition | 0 when |
| --- | --- | --- |
| `rr` | Next QRS onset − this QRS onset | Last beat, or a gap of 30 s or more |
| `p_duration` | Last P offset − last P onset | No P wave |
| `pr` | QRS onset − last P onset | No P wave, or it does not precede the QRS |
| `pr_segment` | QRS onset − last P offset | Same as `pr` |
| `qrs_duration` | QRS offset − QRS onset | — |
| `st` | T onset − QRS offset (the ST segment) | No T wave |
| `qt` | T offset − QRS onset | No T wave |
| `qtc` | Bazett: `qt / sqrt(rr / 1000)` (float) | `rr` is 0 |

### Heart rate

| Column | Description |
| --- | --- |
| `hr` | Heart rate in bpm: `60000 / mean RR` over a 9-interval window centred on the beat. NaN when the mean RR is 100 ms or less |
| `rr_irregularity` | Fraction of successive RR differences in the same window that exceed a heart-rate-dependent threshold (0 = perfectly regular). NaN where undefined |
| `hr_band` | `0` NAN_HR, `1` BRAD (< 60), `2` NORMAL, `3` TACH (> 100), `4` VERY_HIGH (> 180) |

### Quality

| Column | Description |
| --- | --- |
| `quality` | Best signal quality across leads in the second containing the QRS onset, scaled 0–255 |
| `good_quality` | 1 when that quality is at least 0.5 (`/config/report_signal_quality_threshold`). Use this to filter beats before computing statistics |

### Ectopic beats

| Column | Description |
| --- | --- |
| `pac_score` | Model probability that the beat is a PAC, 0–1. Zeroed inside AF |
| `pvc_score` | Model probability that the beat is a PVC, 0–1 |

The beat class is not stored. Derive it from the scores. A beat is ectopic when a score is at least
0.5, and when both are, the higher one wins, with PVC winning a tie:

```python
is_pvc = (pvc_score >= 0.5) & (pvc_score >= pac_score)
is_pac = (pac_score >= 0.5) & ~is_pvc
```

`report_h5.beat_class()` does this, and the CSV has it as `beat_class` (`N`, `PAC`, `PVC`).

### Rhythm

| Column | Description |
| --- | --- |
| `dominant_rhythm` | The beat's rhythm: `0` NSR, `1` S_TACH, `2` S_BRAD, `3` AF, `4` INDETERMINATE. AF includes atrial flutter |
| `p_nsr`, `p_stach`, `p_sbrad`, `p_af`, `p_indeterminate` | Probability of each rhythm for the beat; each row sums to 1 |
| `nsr_score`, `stach_score`, `sbrad_score`, `af_score` | Raw score of each rhythm, 0–1 |

For rhythm episodes (start, end and duration of each AF episode, for example), use the rhythm event
table rather than grouping `dominant_rhythm` yourself; see [EVENTS.md](EVENTS.md).

### Flags

| Column | Description |
| --- | --- |
| `qrs_wide` | `qrs_duration > 120 ms` |
| `p_present` | The beat has at least one P wave |
| `pr_drift_local` | The PR interval varies by more than 20 ms (std) over the beats within ±4 of this one |
| `rr_irregular_local` | `rr_irregularity ≥ 0.5` |
| `gap_flat_after_beat` | The RR is a pause candidate (3–10 s) and the signal is flat until the next beat |

## `/beat_peaks`: peaks per lead

Present when beat peaks ran, which is the default (`/config/beat_peaks` is then 1). Unlike
the other two groups, these are measured on **each lead separately**: every dataset is `(L, N)`,
leads by beats, where `L` is the number of analyzed leads in the order they were analyzed. Peaks
are measured on the raw signal (resampled to 250 Hz, not filtered or normalized), and each peak is
searched only inside its own wave's onset–offset window.

`report_h5.read_beat_peaks(path, lead)` returns one lead as a DataFrame. The CSV adds the columns as
`lead<n>_<column>` with `--peaks`.

| Column | Description |
| --- | --- |
| `p_peak_ms`, `p_amp` | Largest deflection of the last P wave |
| `q_peak_ms`, `q_amp` | Deepest point before R (the deflection of a QS complex) |
| `r_peak_ms`, `r_amp` | Largest positive deflection of the QRS. None in a QS complex |
| `s_peak_ms`, `s_amp` | Deepest point after R |
| `qrs_main_peak_ms`, `qrs_main_amp` | Whichever of Q, R and S is largest |
| `r2_peak_ms`, `r2_amp` | R′, a second positive lobe |
| `t_peak_ms`, `t_amp` | The T wave's larger lobe |
| `t_peak2_ms`, `t_amp2` | The opposite lobe of a biphasic T |
| `baseline` | Isoelectric level, mV: mean of the PQ segment, else of the 40 ms before the QRS |
| `st_j`, `st_60`, `st_80` | ST deviation from the baseline at J (the QRS offset), J+60 ms and J+80 ms, mV |
| `st_slope` | ST slope from J to J+80, mV/s |
| `t_shape` | `absent`, `upright`, `inverted`, `biphasic`, `flat`, `unmeasured` |
| `qrs_shape` | `None`, `R`, `Rs`, `qRs`, `qR`, `QS`, `rsR'`, `rR'`, `Other` |
| `qrs_notches` | Extra turning points inside the QRS lobes |
| `p_edge`, `q_edge`, `r_edge`, `s_edge`, `t_edge`, `t2_edge` | 1 when the peak sits on the first or last sample of its window: the wave probably extends past the delineation |
| `mv_per_unit` | `(L,)`: mV per unit of each lead's EDF signal, NaN when the unit is unknown |

- **Positions** are ms from the start of the recording, `-1` where there is no such peak.
- **Amplitudes** are in mV, measured from `baseline` (signed), NaN where there is no peak or where
  the EDF does not give the lead's unit.
- In the H5 file, `t_shape` and `qrs_shape` are `uint8`, and their names are in the dataset's
  `names` attribute.

## Recording-level values

These sit next to the table and are useful when working with it:

| Dataset | Description |
| --- | --- |
| `/meta/total_beats` | `N` |
| `/meta/analyzed_time_ms` | Length of the analyzed recording |
| `/meta/start_time` | Recording start as a Unix epoch in seconds, 0 when unknown |
| `/signal_quality/per_second` | `(L, S)`: quality of each lead for each second, 0–1 |
| `/clinical_metrics/*` | Overall HR, HRV (SDNN, RMSSD, pNN50) and PR / QRS / QTc summaries |
| `/config/*` | The thresholds the analysis ran with |

The clinical metrics use stricter samples than a plain average of the table. For example, PR uses
only sinus beats with PR between 50 and 500 ms, and min / max are the 1st / 99th percentiles.
`examples/beat_stats.py` prints both side by side.
