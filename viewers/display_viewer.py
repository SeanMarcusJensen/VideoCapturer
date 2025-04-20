import time
import yaml
import cv2
from streaming.viewer import VideoStreamViewer
import threading

class DisplayViewer(VideoStreamViewer):
    def __init__(self, config_file=None):
        super().__init__()
        self._window_name = "Video Stream"
        self._lock = threading.Lock()
        self._enabled = True
        if config_file:
            with open(config_file, 'r') as file:
                config = yaml.safe_load(file)
                self._enabled = bool(config.get("local_display_enabled", True))

        if self._enabled:
            cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self._window_name, 640, 480)
    
    def update(self, frame):
        with self._lock:
            if not self._enabled:
                return

            if frame is not None:
                cv2.imshow(self._window_name, frame)
                cv2.waitKey(1)
    
    def cleanup(self):
        if self._enabled:
            cv2.destroyWindow(self._window_name)