import yaml
import cv2
import requests
from collections import deque
from typing import List
import threading
from streaming.viewer import VideoStreamViewer

class MonitoringViewer(VideoStreamViewer):
    # TODO: Add a config file for the recorder
    def __init__(self, fps=30, buffer_seconds=20, post_trigger_seconds=40):
        super().__init__()
        self._buffer = deque(maxlen=fps * buffer_seconds)
        self._fps = fps
        self._max_video_length_sec = post_trigger_seconds + buffer_seconds
        self._recording = False
        self._lock = threading.Lock()
        self._frames = []

    def monitor(self):
        """ Monitor the stream and trigger recording when needed.

        TODO: READ GPIO PINs.
        """
        while True:
            key = input()
            if key == "t":
                print("[Recorder] Trigger event detected!")
                self.trigger()
            elif key == "q":
                print("[Recorder] Quitting...")
                break

    def update(self, frame):
        with self._lock:
            if frame is None:
                return

            self._buffer.append(frame)

            if self._recording:
                self._frames.append(frame)
                if len(self._frames) >= self._fps * self._max_video_length_sec:
                    self._recording = False
                    self._save_and_send_clip()

    def trigger(self):
        with self._lock:
            if not self._recording:
                print("[Recorder] Triggered event!")
                self._recording = True
                self._frames = list(self._buffer)

    def _save_and_send_clip(self):
        filename = "triggered_clip.mp4"
        try:
            height, width, _ = self._frames[0].shape
            out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), self._fps, (width, height))
            for frame in self._frames:
                out.write(frame)
            out.release()

            response = requests.post("http://192.168.32.10:8080/videos/", files={"video": open(filename, 'rb')})
            print(f"[Recorder] Uploaded clip: {response.status_code}")
        except Exception as e:
            print(f"[Recorder] Upload failed: {e}")
        finally:
            import os 
            if os.path.exists(filename):
                os.remove(filename)

