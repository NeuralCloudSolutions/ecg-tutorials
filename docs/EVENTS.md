# The Event Tables

The H5 report has four event tables. Each is a group with one dataset per column, all of the same
length (one entry per event):

| Group | Events |
| --- | --- |
| `/rhythm_events` | Rhythm episodes: NSR, sinus tachycardia, sinus bradycardia, AF / flutter, indeterminate |
| `/ectopic_events` | PAC and PVC singles, couplets, triplets and runs |
| `/gap_events` | Pauses |
| `/events/artifact` | Regions of low signal quality, per lead |

`examples/events_to_csv.py` writes each to its own CSV, and `report_h5.read_events()` returns them
as pandas DataFrames with the type codes decoded.

## Conventions

- **Times** are milliseconds from the start of the recording. If `/meta/start_time` (Unix epoch
  seconds) is set, the wall-clock time is `start_time + ms / 1000`. The CSV then adds `start_clock`
  and `end_clock` columns.
- **Beat indices** (`start_beat`, `end_beat`, ...) are rows of the beat table
  ([BEAT_TABLE.md](BEAT_TABLE.md)) and are inclusive on both ends.
- **A beat's end** is its T offset when it has a T wave, otherwise its QRS offset. Rhythm and
  ectopic events end at the end of their last beat.
- **Type codes** are stored as `uint8` and listed with each table below.
- A table can be empty: no pauses means a `/gap_events` group whose datasets have length 0.

## `/rhythm_events`

One row per rhythm episode, sorted by start beat. Episodes of the **same** type never overlap. Episodes
of **different** types may, so don't assume the table tiles the recording.

| Column | Type | Description |
| --- | --- | --- |
| `id` | uint64 | Row index |
| `type` | uint8 | `0` NSR, `1` S_TACH, `2` S_BRAD, `3` AF (atrial fibrillation or flutter), `4` INDETERMINATE |
| `start_beat`, `end_beat` | uint64 | First and last beat |
| `start_ms` | uint64 | QRS onset of the first beat |
| `end_ms` | uint64 | End of the last beat |
| `duration_ms` | uint64 | `end_ms − start_ms` |
| `beat_count` | uint64 | `end_beat − start_beat + 1` |
| `confidence` | float32 | Mean probability of this rhythm (`p_<type>` in the beat table) over the episode |
| `initial_score` | float32 | The rhythm's raw score (1.0 for INDETERMINATE) |
| `good_quality_fraction` | float32 | Fraction of the episode's beats with good signal quality |
| `hr_mean`, `hr_min`, `hr_max` | float32 | Heart rate over the episode, bpm |
| `rr_mean_ms`, `rr_std_ms` | float32 | RR mean and standard deviation |
| `rr_irregularity_mean` | float32 | Mean RR irregularity (0 = regular) |
| `qrs_mean_ms` | float32 | Mean QRS duration |
| `qrs_wide_count` | uint64 | Beats with QRS > 120 ms |
| `pr_present_fraction` | float32 | Fraction of beats with a P wave |
| `pr_mean_ms`, `pr_std_ms` | float32 | PR mean and standard deviation over beats with a P wave |
| `qtc_mean` | float32 | Mean QTc over beats with a T wave |

### `/rhythm_events/payload`

Extra columns for specific rhythm types, one entry per event like the rest of the table. A column
that does not apply to the event's type is 0.

| Column | Set for | Description |
| --- | --- | --- |
| `pr_drift_index` | NSR, S_TACH, S_BRAD | How much the PR interval drifts over the episode, ms |
| `onset_hr` | S_TACH | Heart rate at the start of the episode |
| `peak_hr` | S_TACH | Highest heart rate in the episode |
| `trough_hr` | S_BRAD | Lowest heart rate in the episode |
| `mean_af_probability` | AF | Mean AF probability over the episode |
| `p_wave_fraction` | AF | Fraction of the episode's beats with a P wave |
| `tach_fraction` | INDETERMINATE | Fraction of the episode's beats in the tachycardia band |
| `brad_fraction` | INDETERMINATE | Fraction in the bradycardia band |

The CSV puts the payload columns after the main ones.

### Common questions

AF burden is the total AF duration divided by the analyzed time:

```python
events = report_h5.read_events('report.h5')
rhythm = events['rhythm']
af = rhythm[rhythm['type'] == 'AF']
burden = af['duration_ms'].sum() / report_h5.read_meta('report.h5')['analyzed_time_ms']
longest_af_ms = af['duration_ms'].max()
```

Time in each rhythm: `rhythm.groupby('type')['duration_ms'].sum()`.

## `/ectopic_events`

One row per run of consecutive PAC or PVC beats, in beat order.

| Column | Type | Description |
| --- | --- | --- |
| `id` | uint64 | Always 0 in this version; use the row index |
| `type` | uint8 | `0` PAC, `1` PVC |
| `start_beat`, `end_beat` | uint64 | First and last beat of the run |
| `beat_count` | uint64 | `1` single, `2` couplet, `3` triplet, `4+` run. The CSV spells this out in a `kind` column |
| `start_ms` | uint64 | QRS onset of the first beat |
| `end_ms` | uint64 | End of the last beat |
| `duration_ms` | uint64 | `end_ms − start_ms` |
| `confidence` | float32 | Mean `pac_score` or `pvc_score` over the run |

A beat is ectopic when its `pac_score` or `pvc_score` is at least 0.5 (see
[BEAT_TABLE.md](BEAT_TABLE.md#ectopic-beats)). The total PVC count is
`ectopic[ectopic['type'] == 'PVC']['beat_count'].sum()`.

## `/gap_events`

One row per pause: an RR interval longer than 3 s and at most 10 s, with a flat signal between the
two beats.

| Column | Type | Description |
| --- | --- | --- |
| `id` | uint64 | Always 0 in this version; use the row index |
| `type` | uint8 | `0` PAUSE |
| `before_beat` | uint64 | Last beat before the pause |
| `after_beat` | uint64 | First beat after the pause (`before_beat + 1`) |
| `start_ms` | uint64 | QRS offset of `before_beat` |
| `end_ms` | uint64 | QRS onset of `after_beat` |
| `duration_ms` | uint64 | `end_ms − start_ms` |
| `confidence` | float32 | 0.5 for each of the two bounding beats with good signal quality: 0, 0.5 or 1 |

## `/events/artifact`

Regions where a lead's signal quality is too low to read (below 0.3,
`/config/artifact_signal_quality_threshold`), listed lead by lead, in time order within each lead.
Quality is scored per second, so regions start and end on whole seconds.

| Column | Type | Description |
| --- | --- | --- |
| `start` | uint64 | Start, ms, inclusive. The CSV calls this `start_ms` |
| `end` | uint64 | End, ms, exclusive. The CSV calls this `end_ms` |
| `lead` | uint64 | Lead, 0-based, in the order the leads were analyzed |
| `quality` | float32 | Mean quality score inside the region, 0–1 |

The per-second quality behind these regions is in `/signal_quality/per_second`, shape
`(leads, seconds)`.
