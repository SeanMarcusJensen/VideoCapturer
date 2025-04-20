import os 
import cv2
import yaml
import requests
import threading
from gpiozero import Button, LED
from collections import deque
from typing import List
from streaming.viewer import VideoStreamViewer

class MonitoringViewer(VideoStreamViewer):
    def __init__(self, config_file):
        super().__init__()
        config = yaml.safe_load(open(config_file))
        self._secret_file = config["secrets_file"]
        self._settings = config["monitoring"]
        self._is_enabled = bool(self._settings["enabled"])

        self._fps = int(self._settings["fps"])
        self._buffer = deque(maxlen=self._fps * int(self._settings["buffered_video_in_seconds"]))
        self._max_video_length_sec = int(self._settings["max_video_length_seconds"])
        self._recording = False
        self._lock = threading.Lock()
        self._frames = []

        self._notification_url = self._settings["notification_url"]

        self._monitoring_led = LED(int(self._settings["monitoring_led"]))
        if self._monitoring_led:
            print("[Recorder] Monitoring LED is enabled.")

        self._monitoring_button = Button(int(self._settings["monitoring_button"]))
        if self._monitoring_button:
            print("[Recorder] Monitoring button is enabled.")
            self._monitoring_button.when_pressed = self.trigger
            print("[Recorder] Monitoring button is enabled.")
            

    def monitor(self):
        """ Monitor the stream and trigger recording when needed.

        TODO: READ GPIO PINs.
        """
        while self._is_enabled:
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
                    threading.Thread(target=self._save_and_send_clip).start()

    def trigger(self):
        with self._lock:
            if not self._recording:
                if self._monitoring_led:
                    self._monitoring_led.on()
                print("[Recorder] Triggered event!")
                self._recording = True
                self._frames = list(self._buffer.copy())

    def _blink_led_while_active(self, stop_event):
        import time 
        while not stop_event.is_set():
            self._monitoring_led.toggle()
            time.sleep(0.3)  # Blink speed
        self._monitoring_led.off()

    def _save_and_send_clip(self):
        stop_event = threading.Event()
        blinking_thread = threading.Thread(target=self._blink_led_while_active, args=(stop_event,))
        blinking_thread.start()
        frames = self._frames.copy()
        self._frames = []

        print("[Recorder] Preparing to stream clip to server...")

        filename = os.path.join(self._settings["output_dir"], f"monitoring_clip.mp4")
        if not os.path.exists(self._settings["output_dir"]):
            os.makedirs(self._settings["output_dir"])
        if os.path.exists(filename):
            os.remove(filename)
        print(f"[Recorder] Saving clip to {filename}")

        with open(self._secret_file, 'r') as file:
            secrets = yaml.safe_load(file)
            device_id = secrets["device_id"]
            if "device_id" not in secrets:
                print("[Recorder] Device ID not found in secrets file.")
                return

        try:
            height, width, _ = frames[0].shape
            out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), self._fps, (width, height))
            for frame in frames:
                out.write(frame)
            out.release()

            with open(filename, 'rb') as f:
                files = {
                    'video': (filename, f, 'video/mp4')
                }
                response = requests.post(f"{self._notification_url}/{device_id}/", files=files)
                print(f"[Recorder] Uploaded clip: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"[Recorder] Upload failed: {e}")
        finally:
            stop_event.set()
            blinking_thread.join()

            if self._monitoring_led:
                self._monitoring_led.off()

            if os.path.exists(filename):
                os.remove(filename)
