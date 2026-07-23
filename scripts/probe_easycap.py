"""Probe easierCAP capture modes for non-black frames."""
from __future__ import annotations

import cv2
import numpy as np

from app.device.capture import _open_capture

idx, be = 1, cv2.CAP_DSHOW
modes = [
    (720, 480, None),
    (640, 480, None),
    (640, 480, "YUY2"),
    (640, 480, "MJPG"),
    (720, 576, None),
    (320, 240, None),
    (1280, 720, None),
    (720, 480, "YUY2"),
    (720, 480, "MJPG"),
    (800, 600, None),
]

for w, h, four in modes:
    cap = _open_capture(idx, be)
    if not cap.isOpened():
        print("fail open")
        break
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass
    if four:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*four))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    means = []
    shape = None
    for _ in range(20):
        ok, frame = cap.read()
        if ok:
            means.append(float(np.mean(frame)))
            shape = frame.shape
    aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    avg = sum(means) / len(means) if means else -1.0
    mx = max(means) if means else 0.0
    label = four or "default"
    print(f"req {w}x{h} {label:7} -> got {aw}x{ah} shape={shape} avg={avg:.2f} max={mx:.1f}")
