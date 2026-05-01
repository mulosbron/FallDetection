from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class MotionResult:
    has_motion: bool
    changed_area: int


@dataclass
class PersonResult:
    has_person: bool
    bbox_count: int


@dataclass
class CameraGateState:
    prev_gray: np.ndarray | None = None
    frame_index: int = 0
    warmup_remaining: int = 0
    last_person_result: bool = False
    last_sent_at_ms: int = 0
    sent_count: int = 0
    skipped_no_motion: int = 0
    skipped_no_person: int = 0
    skipped_cooldown: int = 0


def detect_motion(
    prev_gray: np.ndarray | None,
    curr_gray: np.ndarray,
    motion_diff_threshold: int,
    motion_min_area: int,
) -> MotionResult:
    if prev_gray is None:
        return MotionResult(has_motion=False, changed_area=0)

    diff = cv2.absdiff(prev_gray, curr_gray)
    _, th = cv2.threshold(diff, motion_diff_threshold, 255, cv2.THRESH_BINARY)
    th = cv2.dilate(th, None, iterations=2)
    changed_area = int(cv2.countNonZero(th))
    return MotionResult(has_motion=changed_area >= motion_min_area, changed_area=changed_area)


def detect_person_hog(
    frame_bgr: np.ndarray,
    hog: cv2.HOGDescriptor,
    min_bbox_area: int,
) -> PersonResult:
    rects, _ = hog.detectMultiScale(
        frame_bgr,
        winStride=(8, 8),
        padding=(8, 8),
        scale=1.05,
    )
    valid = 0
    for x, y, w, h in rects:
        if int(w * h) >= min_bbox_area:
            valid += 1
    return PersonResult(has_person=valid > 0, bbox_count=valid)


def should_send_frame(
    state: CameraGateState,
    motion_result: MotionResult,
    person_result: PersonResult,
    now_ms: int,
    send_cooldown_ms: int,
) -> bool:
    if not motion_result.has_motion:
        state.skipped_no_motion += 1
        return False

    if not person_result.has_person:
        state.skipped_no_person += 1
        return False

    if state.last_sent_at_ms > 0 and (now_ms - state.last_sent_at_ms) < send_cooldown_ms:
        state.skipped_cooldown += 1
        return False

    state.last_sent_at_ms = now_ms
    state.sent_count += 1
    return True
