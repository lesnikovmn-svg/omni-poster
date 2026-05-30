from __future__ import annotations
import time
import base64
import requests
import cloudinary
import cloudinary.uploader
from pathlib import Path


class InstagramPublisher:
    BASE_URL = "https://graph.instagram.com/v21.0"

    def __init__(self, *, access_token: str, account_id: str, imgbb_api_key: str, cloudinary_cloud: str | None = None, cloudinary_key: str | None = None, cloudinary_secret: str | None = None):
        self.token = access_token
        self.account_id = account_id
        self.imgbb_api_key = imgbb_api_key
        if cloudinary_cloud and cloudinary_key and cloudinary_secret:
            cloudinary.config(cloud_name=cloudinary_cloud, api_key=cloudinary_key, api_secret=cloudinary_secret)

    def _url(self, path: str) -> str:
        return f"{self.BASE_URL}/{path}"

    def _upload_to_imgbb(self, path: Path) -> str:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": self.imgbb_api_key, "image": data},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["data"]["url"]

    def _wait_for_container(self, container_id: str, max_wait: int = 120) -> bool:
        for _ in range(max_wait // 5):
            r = requests.get(
                self._url(container_id),
                params={"fields": "status_code", "access_token": self.token},
                timeout=30,
            )
            r.raise_for_status()
            status = r.json().get("status_code")
            print(f"[Instagram] container {container_id} status: {status}")
            if status == "FINISHED":
                return True
            if status == "ERROR":
                return False
            time.sleep(5)
        return False

    def _publish(self, container_id: str) -> None:
        r = requests.post(
            self._url(f"{self.account_id}/media_publish"),
            params={"access_token": self.token},
            json={"creation_id": container_id},
            timeout=30,
        )
        r.raise_for_status()
        print(f"[Instagram] published: {r.json()}")

    def post_photos(self, *, image_paths: list[Path], text: str) -> None:
        if not image_paths:
            return
        print(f"[Instagram] uploading {len(image_paths)} photos to imgbb...")
        urls = [self._upload_to_imgbb(p) for p in image_paths]

        if len(urls) == 1:
            r = requests.post(
                self._url(f"{self.account_id}/media"),
                params={"access_token": self.token},
                json={"image_url": urls[0], "caption": text},
                timeout=30,
            )
            r.raise_for_status()
            container_id = r.json()["id"]
        else:
            children = []
            for url in urls:
                r = requests.post(
                    self._url(f"{self.account_id}/media"),
                    params={"access_token": self.token},
                    json={"image_url": url, "is_carousel_item": True},
                    timeout=30,
                )
                r.raise_for_status()
                children.append(r.json()["id"])
            r = requests.post(
                self._url(f"{self.account_id}/media"),
                params={"access_token": self.token},
                json={"media_type": "CAROUSEL", "children": ",".join(children), "caption": text},
                timeout=30,
            )
            r.raise_for_status()
            container_id = r.json()["id"]

        if self._wait_for_container(container_id):
            self._publish(container_id)
        else:
            print(f"[Instagram] container {container_id} failed or timed out")

    def _upload_to_cloudinary(self, path: Path) -> str:
        result = cloudinary.uploader.upload(str(path), resource_type="video")
        return result["secure_url"]

    def post_video(self, *, video_path: Path, text: str) -> None:
        print(f"[Instagram] uploading video to cloudinary...")
        video_url = self._upload_to_cloudinary(video_path)
        r = requests.post(
            self._url(f"{self.account_id}/media"),
            params={"access_token": self.token},
            json={"media_type": "REELS", "video_url": video_url, "caption": text},
            timeout=30,
        )
        r.raise_for_status()
        container_id = r.json()["id"]
        if self._wait_for_container(container_id):
            self._publish(container_id)
        else:
            print(f"[Instagram] Reels container {container_id} failed")

    def post_text(self, *, text: str) -> None:
        pass
