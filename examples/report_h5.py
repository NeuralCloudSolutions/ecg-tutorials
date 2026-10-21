"""Helpers for reading the H5 report returned by the NeuralCloud ECG analysis.

The report is plain HDF5, so only h5py, numpy and pandas are needed. Every
time in the report is in milliseconds from the start of the recording, and the
analysis runs at 250 samples per second (4 ms per sample).

The example scripts in this folder import this module:

    import report_h5

    beats = report_h5.read_beat_list('out/report.h5')
    table = report_h5.read_beat_table('out/report.h5')
"""
from dataclasses import dataclass, field
from typing import Optional

import h5py
import numpy as np
import pandas as pd
import pyedflib

# The analysis sampling rate. Beat times in ms map to sample `ms * 250 / 1000`.
SAMPLING_RATE = 250

# Enumerations, indexed by the uint8 value stored in the file.
RHYTHM_TYPES = ['NSR', 'S_TACH', 'S_BRAD', 'AF', 'INDETERMINATE']
GAP_TYPES = ['PAUSE']
ECTOPIC_TYPES = ['PAC', 'PVC']
HR_BANDS = ['NAN_HR', 'BRAD', 'NORMAL', 'TACH', 'VERY_HIGH']
ENCODING_STATUS = ['OK', 'NO_T', 'BAD_T', 'TOO_SHORT',
                   'TOO_LONG', 'EDGE', 'FLAT', 'QUALITY']

# A beat is a PAC or PVC when its score is at least this (the analysis default).
ECTOPIC_THRESHOLD = 0.5


#
# Beat list
#

@dataclass
class Wave:
    start: int  # onset, ms
    end: int    # offset, ms

    @property
    def duration(self):
        return self.end - self.start


@dataclass
class Beat:
    index: int
    qrs: Wave
    p_waves: list = field(default_factory=list)  # list[Wave], may be empty
    t: Optional[Wave] = None                     # None when no T wave was found

    @property
    def p(self):
        """The P wave that conducts to this QRS (the last one), or None."""
        return self.p_waves[-1] if self.p_waves else None

    @property
    def end(self):
        """End of the beat: T offset if it ends after the QRS, else QRS offset."""
        if self.t is not None and self.t.end > self.qrs.end:
            return self.t.end
        return self.qrs.end


def read_beat_list(path):
    """Rebuild the beat list from /beats as a list of Beat objects.

    /beats stores one row per beat, except for the P waves: a beat can have
    zero, one or several P waves, so all P waves are stored back to back in
    `p_waves_start` / `p_waves_end` and `p_wave_count[i]` says how many belong
    to beat i.
    """
    with h5py.File(path, 'r') as f:
        g = f['beats']
        r, r_end = g['r'][:], g['r_end'][:]
        has_t, t_start, t_end = g['has_t'][:], g['t_start'][:], g['t_end'][:]
        p_count = g['p_wave_count'][:]
        p_start, p_end = g['p_waves_start'][:], g['p_waves_end'][:]

    beats = []
    offset = 0
    for i in range(len(r)):
        n_p = int(p_count[i])
        p_waves = [Wave(int(p_start[j]), int(p_end[j]))
                   for j in range(offset, offset + n_p)]
        offset += n_p

        t = Wave(int(t_start[i]), int(t_end[i])) if has_t[i] else None

        beats.append(Beat(index=i,
                          qrs=Wave(int(r[i]), int(r_end[i])),
                          p_waves=p_waves,
                          t=t))
    return beats


#
# Report-level values
#

def read_meta(path):
    """Version, recording length, start time, beat and lead counts."""
    with h5py.File(path, 'r') as f:
        quality = f['signal_quality/per_second']
        return {
            'version': f.attrs['version'],
            'version_date': f.attrs['version_date'],
            'analyzed_time_ms': int(f['meta/analyzed_time_ms'][()]),
            'start_time': int(f['meta/start_time'][()]),
            'total_beats': int(f['meta/total_beats'][()]),
            'leads': int(quality.shape[0]),
        }


def read_group_scalars(path, group):
    """All scalar datasets of a group (e.g. /config, /clinical_metrics) as a dict."""
    with h5py.File(path, 'r') as f:
        return {k: v[()].item() for k, v in f[group].items()
                if isinstance(v, h5py.Dataset) and v.shape == ()}


def clock_time(start_time, ms):
    """Wall-clock time of a recording offset in ms, or None without a start time."""
    if not start_time:
        return None
    return pd.to_datetime(start_time, unit='s') + pd.to_timedelta(ms, unit='ms')


#
# Beat table
#

def beat_class(pac_score, pvc_score, threshold=ECTOPIC_THRESHOLD):
    """N / PAC / PVC per beat from the stored scores. PVC wins a tie."""
    pac_score = np.asarray(pac_score)
    pvc_score = np.asarray(pvc_score)
    is_pvc = (pvc_score >= threshold) & (pvc_score >= pac_score)
    is_pac = (pac_score >= threshold) & ~is_pvc
    return np.where(is_pvc, 'PVC', np.where(is_pac, 'PAC', 'N'))


def _missing_where(values, missing):
    """Integer column with <NA> where `missing` is set (the file stores 0 there)."""
    return pd.Series(values).astype('Int64').mask(missing)


def read_beat_table(path):
    """One row per beat: the wave geometry from /beats and every per-beat
    column of /beat_table, with the enumerations decoded."""
    with h5py.File(path, 'r') as f:
        g = f['beats']
        df = pd.DataFrame({
            'qrs_onset_ms': g['r'][:],
            'qrs_offset_ms': g['r_end'][:],
            'p_wave_count': g['p_wave_count'][:],
        })

        # Onset / offset of the last P wave of each beat (the one in the PR interval)
        count = g['p_wave_count'][:].astype(np.int64)
        has_p = count > 0
        last = np.cumsum(count)[has_p] - 1
        p_onset = np.zeros(len(count), dtype=np.int64)
        p_offset = np.zeros(len(count), dtype=np.int64)
        p_onset[has_p] = g['p_waves_start'][:][last]
        p_offset[has_p] = g['p_waves_end'][:][last]
        df['p_onset_ms'] = _missing_where(p_onset, ~has_p)
        df['p_offset_ms'] = _missing_where(p_offset, ~has_p)

        has_t = g['has_t'][:].astype(bool)
        df['has_t'] = has_t
        df['t_onset_ms'] = _missing_where(g['t_start'][:], ~has_t)
        df['t_offset_ms'] = _missing_where(g['t_end'][:], ~has_t)

        for name, ds in f['beat_table'].items():
            if ds.shape != ():
                df[name] = ds[:]

    df.index.name = 'beat'
    df['dominant_rhythm'] = np.array(RHYTHM_TYPES)[df['dominant_rhythm']]
    df['hr_band'] = np.array(HR_BANDS)[df['hr_band']]
    df['beat_class'] = beat_class(df['pac_score'], df['pvc_score'])
    for col in ['good_quality', 'qrs_wide', 'p_present', 'pr_drift_local',
                'rr_irregular_local', 'gap_flat_after_beat']:
        df[col] = df[col].astype(bool)

    # h5py lists datasets alphabetically; put the most used columns first
    first = [c for c in BEAT_TABLE_ORDER if c in df.columns]
    return df[first + [c for c in df.columns if c not in first]]


BEAT_TABLE_ORDER = [
    # Geometry
    'qrs_onset_ms', 'qrs_offset_ms', 'p_wave_count', 'p_onset_ms', 'p_offset_ms',
    'has_t', 't_onset_ms', 't_offset_ms',
    # Intervals
    'rr', 'hr', 'p_duration', 'pr', 'pr_segment', 'qrs_duration', 'st', 'qt', 'qtc',
    # Classification
    'beat_class', 'dominant_rhythm', 'good_quality', 'quality',
    'pac_score', 'pvc_score', 'nsr_score', 'stach_score', 'sbrad_score', 'af_score',
    'p_nsr', 'p_stach', 'p_sbrad', 'p_af', 'p_indeterminate',
    # Flags
    'hr_band', 'rr_irregularity', 'qrs_wide', 'p_present', 'pr_drift_local',
    'rr_irregular_local', 'gap_flat_after_beat',
]


#
# Events
#

def _read_table(group):
    return pd.DataFrame({name: ds[:] for name, ds in group.items()
                         if isinstance(ds, h5py.Dataset)})


def read_events(path):
    """The four event tables as DataFrames: rhythm, gap, ectopic and artifact."""
    with h5py.File(path, 'r') as f:
        rhythm = _read_table(f['rhythm_events'])
        payload = _read_table(f['rhythm_events/payload'])
        rhythm = pd.concat([rhythm, payload], axis=1)
        rhythm['type'] = np.array(RHYTHM_TYPES)[rhythm['type']]

        gap = _read_table(f['gap_events'])
        gap['type'] = np.array(GAP_TYPES)[gap['type']]
        gap['id'] = np.arange(len(gap))

        ectopic = _read_table(f['ectopic_events'])
        ectopic['type'] = np.array(ECTOPIC_TYPES)[ectopic['type']]
        ectopic['id'] = np.arange(len(ectopic))
        ectopic['kind'] = pd.cut(ectopic['beat_count'], [0, 1, 2, 3, np.inf],
                                 labels=['single', 'couplet', 'triplet', 'run']).astype(str)

        artifact = _read_table(f['events/artifact'])

    return {'rhythm': rhythm, 'gap': gap, 'ectopic': ectopic, 'artifact': artifact}


#
# Beat encoding and beat peaks (per lead)
#

def read_beat_encoding(path):
    """The /beat_encoding group as a dict, or None when the encoder did not run.

    encoding: (leads, beats, 16) unit vectors, NaN where status != 0
    status:   (leads, beats) ENCODING_STATUS code, 0 = encoded
    lead_ok:  (leads, beats) 1 when the lead's own quality was good at the beat
    """
    with h5py.File(path, 'r') as f:
        if 'beat_encoding' not in f:
            return None
        g = f['beat_encoding']
        out = {k: g[k][:] for k in g}
        out.update({k: v.item() if hasattr(v, 'item') else v
                    for k, v in g.attrs.items()})
    return out


def read_beat_peaks(path, lead):
    """The /beat_peaks columns for one lead (0-based, in report order) as a
    DataFrame, one row per beat, or None when beat peaks did not run.

    *_peak_ms are ms from the record start (-1 for none); *_amp, baseline and
    st_* are in mV relative to the baseline (NaN for none).
    """
    with h5py.File(path, 'r') as f:
        if 'beat_peaks' not in f:
            return None
        g = f['beat_peaks']
        df = pd.DataFrame({k: g[k][lead] for k in g if g[k].ndim == 2})
        for col in ['t_shape', 'qrs_shape']:
            names = g[col].attrs['names'].split(',')
            df[col] = np.array(names)[df[col]]
    df.index.name = 'beat'
    return df


def normal_centroid(encoding, keep=0.5):
    """The direction of the record's dominant beat shape.

    `encoding` is (beats, 16) unit vectors with no NaN rows. The mean of all
    beats is pulled toward ectopic or noisy beats, so this takes the mean, keeps
    the `keep` fraction of beats closest to it, and averages those again.
    """
    centroid = encoding.mean(axis=0)
    centroid /= np.linalg.norm(centroid)

    similarity = encoding @ centroid
    n_keep = max(1, int(len(encoding) * keep))
    closest = np.argsort(-similarity)[:n_keep]

    centroid = encoding[closest].mean(axis=0)
    return centroid / np.linalg.norm(centroid)


def encoded_beats(path, lead, good_quality_only=True):
    """Indices and encodings of the beats encoded on `lead`.

    With `good_quality_only`, beats whose lead was noisy (`lead_ok` = 0) or that
    the report marks as poor quality are left out.
    """
    be = read_beat_encoding(path)
    if be is None:
        raise SystemExit(f'{path} has no /beat_encoding group: '
                         'the beat encoder did not run for this report.')
    if lead >= be['encoding'].shape[0]:
        raise SystemExit(f'Lead {lead} is out of range: the report has '
                         f'{be["encoding"].shape[0]} lead(s).')

    ok = be['status'][lead] == 0
    if good_quality_only:
        with h5py.File(path, 'r') as f:
            good = f['beat_table/good_quality'][:].astype(bool)
        ok &= (be['lead_ok'][lead] == 1) & good

    index = np.flatnonzero(ok)
    return index, be['encoding'][lead, index]


#
# Signal
#

_MV_PER_UNIT = {'mv': 1.0, 'uv': 1e-3, 'µv': 1e-3, 'μv': 1e-3, 'v': 1e3, 'nv': 1e-6}


def load_lead(edf_path, lead):
    """One EDF signal (0-based signal number) resampled to 250 Hz.

    Returns (signal, mv_per_unit). mv_per_unit converts the signal to mV and is
    NaN when the EDF's physical dimension is not a known voltage unit.
    """
    with pyedflib.EdfReader(edf_path) as edf:
        fs = edf.getSampleFrequency(lead)
        signal = edf.readSignal(lead)
        unit = edf.getPhysicalDimension(lead).strip().lower()

    if fs != SAMPLING_RATE:
        t = np.arange(len(signal)) / fs
        t_new = np.arange(int(len(signal) * SAMPLING_RATE / fs)) / SAMPLING_RATE
        signal = np.interp(t_new, t, signal)

    return signal, _MV_PER_UNIT.get(unit, np.nan)


def edf_lead(leads, lead):
    """EDF signal number (0-based) of report lead `lead`.

    The report's leads are the leads that were analyzed, in order. `leads` is
    the 1-based list passed to the analysis (None for every lead).
    """
    if leads is None:
        return lead
    return leads[lead] - 1


def parse_leads(text):
    """'1,2,3' -> [1, 2, 3]; '' -> None (every lead)."""
    if not text:
        return None
    return [int(x) for x in text.split(',') if x.strip()]


def ms_to_sample(ms):
    return int(round(ms * SAMPLING_RATE / 1000))


def beat_baseline(signal, beat):
    """Isoelectric level of a beat: mean of the PQ segment, else the 40 ms before the QRS.

    The same definition as /beat_peaks/baseline.
    """
    onset = ms_to_sample(beat.qrs.start)
    p = beat.p
    if p is not None and 0 < onset - ms_to_sample(p.end) <= ms_to_sample(300):
        return float(np.mean(signal[ms_to_sample(p.end):onset]))
    start = max(0, onset - ms_to_sample(40))
    if start == onset:
        return float(signal[onset])
    return float(np.mean(signal[start:onset]))
