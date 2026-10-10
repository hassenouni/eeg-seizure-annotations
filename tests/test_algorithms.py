import numpy as np
import pytest
from eeg_annotations.intervals import Interval, parse_chbmit, parse_siena, window_labels, segment


def test_chb_multiple_and_empty():
    text = "File Name: a.edf\nNumber of Seizures in File: 2\nSeizure 1 Start Time: 2 seconds\nSeizure 1 End Time: 3 seconds\nSeizure 2 Start Time: 7 seconds\nSeizure 2 End Time: 8 seconds\nFile Name: b.edf\nNumber of Seizures in File: 0"
    parsed = parse_chbmit(text)
    assert parsed["a.edf"] == [Interval(2, 3), Interval(7, 8)]
    assert parsed["b.edf"] == []
    with pytest.raises(ValueError):
        parse_chbmit(text.replace("File: 2", "File: 3"))


def test_siena_midnight_rollover():
    text = "Seizure n 1\nFile name: a.edf\nRegistration start time: 23.59.00\nRegistration end time: 00.05.00\nSeizure start time: 23.59.50\nSeizure end time: 00.00.10"
    assert parse_siena(text) == {"a.edf": [Interval(50, 70)]}
    with pytest.raises(ValueError):
        parse_siena(text.replace("00.05.00", "00.00.00"))


def test_half_open_boundaries_and_fraction():
    starts = np.array([0.0, 1.0, 2.0, 3.0])
    assert window_labels(starts, 1, [Interval(1, 3)]).tolist() == [False, True, True, False]
    assert window_labels(np.array([0.0]), 2, [Interval(0.5, 1.5)], 0.5).item()
    assert not window_labels(np.array([0.0]), 2, [Interval(0.5, 1.5)], 0.6).item()


def test_overlapping_annotations_rejected():
    with pytest.raises(ValueError):
        window_labels(np.array([0.0]), 2, [Interval(0, 2), Interval(1, 3)])


def test_segment_drops_tail_and_returns_seconds():
    x = np.arange(22).reshape(2, 11)
    windows, times = segment(x, 2, 2, 1.5)
    assert windows.shape == (3, 2, 4)
    np.testing.assert_array_equal(times, [0, 1.5, 3])
    np.testing.assert_array_equal(windows[-1], x[:, 6:10])


def test_siena_shared_header_and_repeated_context():
    text = """File name: PN01.edf
Registration start time: 23.59.00
Registration end time: 00.05.00
Seizure n 1
Start time: 23:59.50
End time: 00.00.10
Seizure n 2
Start time: 00.02.00
End time: 00.02.10
"""
    assert parse_siena(text)["PN01.edf"] == [Interval(50, 70), Interval(180, 190)]


def test_siena_ambiguous_event_is_quarantined():
    from eeg_annotations.intervals import audit_siena

    text = """Seizure n 1
File name: a.edf
Registration start time: 12.00.00
Registration end time: 13.00.00
Seizure start time: 12.01.00 (CLINICAL); 12.01.06 (ELECTRIC)
Seizure end time: 12.02.00
Seizure n 2
File name: a.edf
Seizure start time: 12.05.00
Seizure end time: 12.06.00
"""
    audit = audit_siena(text)
    assert audit.events == {"a.edf": [Interval(300, 360)]}
    assert len(audit.issues) == 1 and "ambiguous" in audit.issues[0]["error"]
    with pytest.raises(ValueError, match="ambiguous"):
        parse_siena(text)


def test_siena_split_hour_whitespace():
    text = """Seizure n 1
File name: a.edf
Registration start time:1 6.49.25
Registration end time: 17.00.00
Seizure start time: 16.50.25
Seizure end time: 16.51.25
"""
    assert parse_siena(text)["a.edf"] == [Interval(60, 120)]
