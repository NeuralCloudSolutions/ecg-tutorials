# H5 Report Format

The analysis returns its results as an HDF5 file, `report.h5`. HDF5 is a standard format for
numeric data. Any HDF5 library can read it (`h5py` in Python, HDF5 in MATLAB, `rhdf5` in R), and
[HDFView](https://www.hdfgroup.org/downloads/hdfview/) lets you browse it.

Every group holds plain datasets (columns). A table such as the beat table is a group whose
datasets all have the same length, one entry per row.

## Conventions

- **Times** are milliseconds from the start of the recording, except `/meta/start_time` (Unix
  epoch, seconds; 0 when unknown).
- **Sampling.** The analysis runs at 250 Hz, so every time is a multiple of 4 ms.
- **Booleans** are `uint8` 0 / 1, and **enumerations** are `uint8` codes, listed in the docs below.
- **Missing intervals** are 0. A heart rate that cannot be computed is NaN.
- **Leads** are numbered 0-based in the order they were analyzed. If you passed `--leads 2,3`,
  report lead 0 is EDF signal 2.
- **Version.** The root attribute `version` is the analysis software version that wrote the file
  (for example `2.0.0`). The layout is fixed for a given version.

## Layout

```
/                              attributes: version, version_date, checksum
  /config                      thresholds the analysis ran with
  /meta                        analyzed_time_ms, start_time, total_beats
    /features                  which analyses were run
  /beats                       P, QRS and T onsets / offsets, one row per beat     -> BEAT_TABLE.md
  /beat_table                  intervals, HR, quality, rhythm and PAC/PVC scores    -> BEAT_TABLE.md
  /beat_peaks                  P, Q, R, S, T peaks and shapes, per lead and beat    -> BEAT_TABLE.md
  /beat_encoding               16-d shape vector per lead and beat                  -> BEAT_ENCODING.md
  /heart_rate                  per-beat HR, fastest / slowest beats
  /rhythm_events               NSR, sinus tach / brady, AF, indeterminate episodes  -> EVENTS.md
    /payload                   type-specific columns
  /ectopic_events              PAC / PVC singles, couplets, triplets, runs          -> EVENTS.md
  /gap_events                  pauses                                               -> EVENTS.md
  /events
    /artifact                  low signal quality regions per lead                  -> EVENTS.md
  /signal_quality              per-second signal quality per lead
  /clinical_metrics            overall HR, HRV, PR / QRS / QTc summaries
  /histograms
    /rr                        RR histogram, 1 ms bins
    /qtc                       QTc histogram, 1 ms bins
  /hourly                      per-hour statistics
```

The beats, events and beat encoding have their own docs:

- [BEAT_TABLE.md](BEAT_TABLE.md): `/beats`, `/beat_table` and `/beat_peaks`
- [EVENTS.md](EVENTS.md): the rhythm, ectopic, gap and artifact event tables
- [BEAT_ENCODING.md](BEAT_ENCODING.md): `/beat_encoding`, and how to compare beat shapes

The other groups are summarized below.

## `/meta`

| Dataset | Type | Description |
| --- | --- | --- |
| `analyzed_time_ms` | uint64 | Length of the analyzed recording |
| `start_time` | int64 | Recording start, Unix epoch seconds. 0 when unknown |
| `total_beats` | uint64 | Number of beats, `N` |
| `features/*` | uint8 | 1 for each analysis that ran: `tachybrady`, `af`, `pacpvc`, `pauses`, `beat_stats`, `hourly_analysis`, `rr_histogram`, `qtc_histogram`, `artifacts` |

## `/clinical_metrics`

All scalars.

| Dataset | Description |
| --- | --- |
| `average_hr_overall` | Average heart rate over good-quality beats, bpm (harmonic mean) |
| `hrv_sdnn`, `hrv_rmssd` | HRV over normal sinus RR intervals, ms |
| `hrv_pnn50` | Percentage of successive normal RR differences over 50 ms |
| `pr_mean`, `pr_min`, `pr_max` | PR interval over sinus beats: mean, 1st and 99th percentile, ms |
| `qrs_mean`, `qrs_min`, `qrs_max` | QRS duration: mean, 1st and 99th percentile, ms |
| `qtc_average`, `qtc_minimum`, `qtc_maximum` | QTc (Bazett): mean, 1st and 99th percentile, ms |
| `qtc_prolonged_episodes` | Number of beats with QTc over 460 ms |
| `fastest_hr_timestamp`, `slowest_hr_timestamp` | Reserved, always 0 |

Only good-quality beats are used. AF burden and time in each rhythm are not stored here; compute
them from `/rhythm_events` ([EVENTS.md](EVENTS.md)).

## `/heart_rate`

| Dataset | Shape | Description |
| --- | --- | --- |
| `beats_per_minute` | `(N,)` | Per-beat heart rate (same as `/beat_table/hr`) |
| `rr_irregularity` | `(N,)` | Per-beat RR irregularity (same as `/beat_table/rr_irregularity`) |
| `fastest_hr_indices` | `(≤100,)` | Beat indices of the fastest moments, fastest first, at least 20 beats apart, good quality and outside AF |
| `slowest_hr_indices` | `(≤100,)` | Same for the slowest moments, slowest first |

## `/signal_quality`

| Dataset | Shape | Description |
| --- | --- | --- |
| `per_second` | `(L, S)` | Quality of lead `l` in second `s`, 0 (unreadable) to 1. A beat is good quality at 0.5 and above; below 0.3 is an artifact |

## `/histograms/rr`, `/histograms/qtc`

| Dataset | Description |
| --- | --- |
| `start`, `end` | Value of the first and last bin, ms |
| `bins` | `end − start + 1` counts; bin `i` counts beats with a value of `start + i` ms |

```python
count_at_400_ms = bins[400 - start]
```

## `/hourly`

One entry per hour, aligned to wall-clock hours when `start_time` is known. Empty when
`features/hourly_analysis` is 0.

| Dataset | Description |
| --- | --- |
| `timestamps` | Hour number, 1-based |
| `hr_low`, `hr_mean`, `hr_high` | Heart rate in the hour, bpm |
| `total_beats`, `nsr_beats`, `af_beats` | Beat counts |
| `pac_total`, `pac_runs`, `pvc_total`, `pvc_runs` | Ectopic beats and events in the hour |
| `af_burden`, `nsr` | Percentage of the hour in AF / NSR |

## `/config`

The thresholds the analysis ran with, one scalar per setting. The values are the defaults.

| Dataset | Default | Description |
| --- | --- | --- |
| `report_signal_quality_threshold` | 0.5 | Signal quality at which a beat is good quality |
| `artifact_signal_quality_threshold` | 0.3 | Signal quality below which a region is an artifact |
| `rr_min_ms`, `rr_max_ms` | 200, 2000 | Physiological RR range |
| `pr_min_ms`, `pr_max_ms` | 50, 500 | Physiological PR range |
| `qrs_min_ms`, `qrs_max_ms` | 20, 300 | Physiological QRS range |
| `qtc_min_ms`, `qtc_max_ms` | 200, 800 | Physiological QTc range |
| `prolonged_qtc_ms` | 460 | QTc above which a beat counts as prolonged |
| `brady_hr_max_bpm` | 60 | Heart rate below which a beat is bradycardic |
| `tachy_hr_min_bpm` | 100 | Heart rate above which a beat is tachycardic |
| `nsr_hr_min_bpm`, `nsr_hr_max_bpm` | 60, 100 | Heart-rate range of normal sinus rhythm |
| `pause_min_rr_ms`, `pause_max_rr_ms` | 3000, 10000 | RR range of a pause |
| `beat_encoding` | 1 | Present (and 1) when the beat encoding ran |
| `beat_peaks` | 1 | Present (and 1) when beat peaks ran |

## Reading it in Python

```python
import h5py

with h5py.File('report.h5', 'r') as f:
    print(f.attrs['version'])
    onsets = f['beats/r'][:]                    # QRS onsets, ms
    hr = f['beat_table/hr'][:]                  # bpm per beat
    sdnn = f['clinical_metrics/hrv_sdnn'][()]   # a scalar
```

[examples/report_h5.py](../examples/report_h5.py) has ready-made readers that return Python objects and pandas DataFrames.
