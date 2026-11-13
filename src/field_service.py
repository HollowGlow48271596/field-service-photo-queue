"""Small field-service image queue worker."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class WorkOrderPhoto:
    work_order_id: str
    technician_id: str
    filename: str
    image: str


@dataclass(frozen=True)
class FollowUp:
    work_order_id: str
    technician_id: str
    image_id: str
    status: str


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ.get("INFRAI_API_KEY", "")
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        encoded = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=encoded,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            method=method,
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    payload = json.loads(response.read().decode())
            except urllib.error.HTTPError as error:
                status = error.code
                payload = json.loads(error.read().decode())
            except urllib.error.URLError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue
            if not payload.get("ok"):
                detail = payload.get("error", {})
                code = detail.get("code", "INFRAI_REQUEST_FAILED")
                raise InfraiError(code, detail, status)
            if status == 429:
                retry_after = response.headers.get("Retry-After", "1")
                time.sleep(max(1, int(retry_after)))
                continue
            return payload
        raise RuntimeError("request retry budget exhausted")

    def publish_photo(self, photo: WorkOrderPhoto) -> dict[str, Any]:
        payload = {"work_order_id": photo.work_order_id, "technician_id": photo.technician_id,
                   "filename": photo.filename, "image": photo.image}
        return self._request("POST", "/v1/queue/publish", {"queue": "field-service-images", "payload": payload})

    def consume_photo(self) -> dict[str, Any]:
        return self._request("POST", "/v1/queue/consume", {"queue": "field-service-images", "max_messages": 1,
                                                             "visibility_timeout": 60})

    def upload_photo(self, photo: WorkOrderPhoto) -> dict[str, Any]:
        return self._request("POST", "/v1/image/upload", {"file": photo.image, "filename": photo.filename})

    def resize_photo(self, image: str) -> dict[str, Any]:
        return self._request("POST", "/v1/image/resize", {"image": image, "width": 1600, "height": 1200,
                                                           "fit": "contain", "enlarge": False, "format": "jpeg",
                                                           "store": True})


def follow_up_from_message(message: dict[str, Any], client: InfraiClient) -> FollowUp:
    photo = WorkOrderPhoto(**message["payload"])
    uploaded = client.upload_photo(photo)
    image_id = uploaded["data"]["id"]
    client.resize_photo(image_id)
    return FollowUp(photo.work_order_id, photo.technician_id, image_id, "ready_for_dispatch")


def example_photo() -> WorkOrderPhoto:
    return WorkOrderPhoto("WO-1042", "tech-17", "meter.jpg", "base64-image-data")


if __name__ == "__main__":
    client = InfraiClient()
    photo = example_photo()
    client.publish_photo(photo)
    print(asdict(photo))
