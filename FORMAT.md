# JSON Format

## Sections

### beats

This is a list of all the beats.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| p | List[Wave] | Yes | All P Waves for the beat. |
| qrs | Wave | Yes | QRS for the beat |
| t | Wave | No | T Wave for the beat. |
| pac | boolean | No | True if PAC detected for the beat. |
| pvc | boolean | No | True if PVC detected for the beat. |
| w_qrs | boolean | No | True if QRS is greater than 120 ms. |
| rr | integer | No | RR interval in milliseconds. |
| pr | integer | No | PR interval in milliseconds. |
| prs | integer | No | PR segment in milliseconds. |
| st | integer | No | ST segment in milliseconds. |
| qt | integer | No | QT interval in milliseconds. |
| qtc | integer | No | QTc interval in milliseconds. |
| p_qtc | boolean | No | True if QTc is greater than 460 ms. |

#### Wave

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| s | integer | Yes | Start of wave in milliseconds. |
| e | integer | Yes | End of wave in milliseconds. |
| d | integer | Yes | Duration of wave in milliseconds. |

### events

#### afib

List of AFIB/AFlutter events.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| bs | integer | Yes | Index of first beat in event. |
| be | integer | Yes | Index of last beat in event. |
| s | integer | Yes | Start of event in milliseconds. |
| e | integer | Yes | End of event in milliseconds. |

#### pac

List of PAC events.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| b | integer | Yes | Index of beat. |
| s | integer | Yes | Start of event in milliseconds. |
| e | integer | Yes | End of event in milliseconds. |

#### pvc

List of PVC events.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| b | integer | Yes | Index of beat. |
| s | integer | Yes | Start of event in milliseconds. |
| e | integer | Yes | End of event in milliseconds. |

#### av

List of AV-Block first degree events.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| bs | integer | Yes | Index of first beat in event. |
| be | integer | Yes | Index of last beat in event. |
| s | integer | Yes | Start of event in milliseconds. |
| e | integer | Yes | End of event in milliseconds. |

#### bradycardia

List of bradycardia events.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| bs | integer | Yes | Index of first beat in event. |
| be | integer | Yes | Index of last beat in event. |
| s | integer | Yes | Start of event in milliseconds. |
| e | integer | Yes | End of event in milliseconds. |
| hr | float | Yes | Average heart rate in BPM. |

#### tachycardia

List of tachycardia events.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| bs | integer | Yes | Index of first beat in event. |
| be | integer | Yes | Index of last beat in event. |
| s | integer | Yes | Start of event in milliseconds. |
| e | integer | Yes | End of event in milliseconds. |
| hr | float | Yes | Average heart rate in BPM. |

#### pauses

List of pauses events.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| s | integer | Yes | Start of event in milliseconds. |
| e | integer | Yes | End of event in milliseconds. |
| d | integer | Yes | Duration of pause in milliseconds. |

#### lowest_hr

List of regions with the lowest heart rate. Sorted in ascending order based on heart rate. 

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| bs | integer | Yes | Index of first beat in event. |
| be | integer | Yes | Index of last beat in event. |
| s | integer | Yes | Start of event in milliseconds. |
| e | integer | Yes | End of event in milliseconds. |
| hr | float | Yes | Average heart rate in BPM. |

#### highest_hr

List of regions with the highest heart rate. Sorted in descending order based on heart rate.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| bs | integer | Yes | Index of first beat in event. |
| be | integer | Yes | Index of last beat in event. |
| s | integer | Yes | Start of event in milliseconds. |
| e | integer | Yes | End of event in milliseconds. |
| hr | float | Yes | Average heart rate in BPM. |


### stats

#### rr_histogram

Histogram of RR intervals.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| s | integer | Yes | Value of first bin. |
| e | integer | Yes | Value of last bin. |
| bins | List[integer] | Yes | Count of beats with RR interval of i. |

Example:

Finding number of RR intervals of 400 ms.
```
s = 200
rr_400_count = bins[400 - s]
```

#### qtc_histogram

Histogram of QTc intervals.

| Object | Type | Required    | Description |
|--------|------|-------------|-------------|
| s | integer | Yes | Value of first bin. |
| e | integer | Yes | Value of last bin. |
| bins | List[integer] | Yes | Count of beats with QTc interval of i. |