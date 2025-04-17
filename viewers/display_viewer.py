import time
import cv2
from streaming.viewer import VideoStreamViewer
import threading

class DisplayViewer(VideoStreamViewer):
    def __init__(self):
        super().__init__()
        self._window_name = "Video Stream"
        self._lock = threading.Lock()
        cv2.namedWindow(self._window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self._window_name, 640, 480)
    
    def update(self, frame):
        with self._lock:
            if frame is not None:
                cv2.imshow(self._window_name, frame)
                cv2.waitKey(1)
    
    def cleanup(self):
        cv2.destroyWindow(self._window_name)