from __future__ import annotations

import io
import time

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from app.config import Settings
from app.inference.prefilter import (
    CameraGateState,
    PersonResult,
    detect_motion,
    detect_person_hog,
    should_send_frame,
)
from app.quantization.llama_server_runtime import LlamaServerRuntime


def _normalize_fall_label(text: str) -> str:
    t = text.lower().strip()
    if not t:
        raise RuntimeError("empty model output")
    compact = t.replace(" ", "").replace("-", "_")
    if "no_fall" in compact or "nofall" in compact:
        return "no_fall"
    if "fall_detected" in compact or "falldetected" in compact:
        return "fall_detected"
    if "yes" in t.split()[:3] or t.strip() == "yes":
        return "fall_detected"
    if t.strip() == "no" or t.startswith("no "):
        return "no_fall"
    return "no_fall"


class InferencePipeline:
    def __init__(self, settings: Settings, runtime: LlamaServerRuntime):
        self.settings = settings
        self.runtime = runtime
        self._camera_gate_states: dict[str, CameraGateState] = {}
        self._global_skip_no_camera_id = 0
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    @staticmethod
    def _normalize_yes_no(text: str) -> str:
        t = text.lower().strip()
        if not t:
            return "no"
        words = t.split()
        if words and words[0] in {"yes", "no"}:
            return words[0]
        if "yes" in t and "no" not in t:
            return "yes"
        if "no" in t:
            return "no"
        if "fall_detected" in t:
            return "yes"
        if "no_fall" in t:
            return "no"
        return "no"

    @staticmethod
    def _make_crops(image_bytes: bytes) -> list[bytes]:
        with Image.open(io.BytesIO(image_bytes)) as img:
            image = img.convert("RGB")
            w, h = image.size
            m = min(w, h)

            crops: list[Image.Image] = [image]

            l = (w - m) // 2
            t = (h - m) // 2
            crops.append(image.crop((l, t, l + m, t + m)))

            s = max(1, int(m * 0.8))
            l2 = max(0, (w - s) // 2)
            t2 = max(0, (h - s) // 2)
            crops.append(image.crop((l2, t2, l2 + s, t2 + s)))
            crops.append(ImageOps.mirror(image))
            # crops.append(ImageEnhance.Contrast(image).enhance(1.25))

            out: list[bytes] = []
            for c in crops:
                buf = io.BytesIO()
                c.save(buf, format="JPEG", quality=95)
                out.append(buf.getvalue())
            return out

    async def _ask_yes_no(self, image_bytes: bytes, question: str) -> tuple[str, str, int]:
        result = await self.runtime.infer_vision(
            image_bytes=image_bytes,
            mime_type="image/jpeg",
            user_text=f"{question} Reply with exactly one word: Yes or No.",
            prepend_classifier_instruction=False,
        )
        yn = self._normalize_yes_no(result.text)
        return yn, result.text, result.latency_ms

    def _get_or_create_gate_state(self, camera_id: str) -> CameraGateState:
        state = self._camera_gate_states.get(camera_id)
        if state is None:
            state = CameraGateState(warmup_remaining=max(0, self.settings.prefilter_motion_warmup_frames))
            self._camera_gate_states[camera_id] = state
        return state

    def _should_skip_by_prefilter(self, image_bytes: bytes, camera_id: str | None) -> bool:
        if not self.settings.prefilter_enabled:
            return False
        if camera_id is None:
            self._global_skip_no_camera_id += 1
            return False

        gate = self._get_or_create_gate_state(camera_id)
        gate.frame_index += 1

        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            gate.skipped_no_motion += 1
            return True

        small = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        if gate.warmup_remaining > 0:
            gate.prev_gray = gray
            gate.warmup_remaining -= 1
            gate.skipped_no_motion += 1
            return True

        motion = detect_motion(
            prev_gray=gate.prev_gray,
            curr_gray=gray,
            motion_diff_threshold=self.settings.prefilter_motion_diff_threshold,
            motion_min_area=self.settings.prefilter_motion_min_area,
        )
        gate.prev_gray = gray

        person_every = max(1, self.settings.prefilter_person_check_every_n_frames)
        if gate.frame_index % person_every == 0:
            person = detect_person_hog(
                frame_bgr=small,
                hog=self._hog,
                min_bbox_area=self.settings.prefilter_person_min_bbox_area,
            )
            gate.last_person_result = person.has_person
        else:
            person = PersonResult(has_person=gate.last_person_result, bbox_count=0)

        now_ms = int(time.time() * 1000)
        return not should_send_frame(
            state=gate,
            motion_result=motion,
            person_result=person,
            now_ms=now_ms,
            send_cooldown_ms=self.settings.prefilter_send_cooldown_ms,
        )

    def get_prefilter_summary(self) -> dict:
        total_sent = 0
        total_skip_motion = 0
        total_skip_person = 0
        total_skip_cooldown = 0
        per_camera: dict[str, dict[str, int]] = {}

        for camera_id, st in self._camera_gate_states.items():
            total_sent += st.sent_count
            total_skip_motion += st.skipped_no_motion
            total_skip_person += st.skipped_no_person
            total_skip_cooldown += st.skipped_cooldown
            per_camera[camera_id] = {
                "sent_count": st.sent_count,
                "skipped_no_motion": st.skipped_no_motion,
                "skipped_no_person": st.skipped_no_person,
                "skipped_cooldown": st.skipped_cooldown,
            }

        return {
            "enabled": self.settings.prefilter_enabled,
            "camera_state_count": len(self._camera_gate_states),
            "requests_without_camera_id": self._global_skip_no_camera_id,
            "total_sent": total_sent,
            "total_skipped_no_motion": total_skip_motion,
            "total_skipped_no_person": total_skip_person,
            "total_skipped_cooldown": total_skip_cooldown,
            "per_camera": per_camera,
        }

    async def infer_fall(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str | None = None,
        camera_id: str | None = None,
    ) -> dict:
        if self._should_skip_by_prefilter(image_bytes=image_bytes, camera_id=camera_id):
            return {
                "result": "no_fall",
                "model": self.settings.model_name,
                "runtime": "llama-server-persistent-vision",
                "latency_ms": 0,
                "raw_output": "skipped_by_prefilter",
                "skipped_by_prefilter": True,
                "camera_id": camera_id,
                "votes": {
                    "yes": 0,
                    "no": 0,
                    "total_crops": 0,
                    "questions_per_crop": 0,
                },
            }

        fall_questions = [
            prompt or "Is falling person in picture?",
            "Is a person collapsed or fallen in this image?",
            "Is someone on the ground as if they fell?",
            "Did a person likely fall in this image?",
            # "Is there any fall incident visible in this picture?",
        ]

        crops = self._make_crops(image_bytes)
        yes_votes = 0
        no_votes = 0
        last_raw_output = ""
        total_latency = 0

        for crop in crops:
            crop_yes = False
            for question in fall_questions:
                fallen, fall_raw, fall_latency = await self._ask_yes_no(crop, question)
                total_latency += fall_latency
                last_raw_output = fall_raw
                if fallen == "yes":
                    crop_yes = True
                    break
            if crop_yes:
                yes_votes += 1
            else:
                no_votes += 1

        final_text = "fall_detected" if yes_votes >= 1 else "no_fall"
        normalized = _normalize_fall_label(final_text)
        return {
            "result": normalized,
            "model": self.settings.model_name,
            "runtime": "llama-server-persistent-vision",
            "latency_ms": total_latency,
            "raw_output": last_raw_output[:400],
            "skipped_by_prefilter": False,
            "camera_id": camera_id,
            "votes": {
                "yes": yes_votes,
                "no": no_votes,
                "total_crops": len(crops),
                "questions_per_crop": len(fall_questions),
            },
        }
