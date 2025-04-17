import yaml
import cv2
from typing import List
import time
from .viewer import VideoStreamViewer

class VideoStream:
    def __init__(self, config_file):
        config = yaml.safe_load(open(config_file))
        device = config["capture"]
        self._cap = cv2.VideoCapture(int(device["device"]))
        self._bootstrap_camera(device)
        self._viewer: List[VideoStreamViewer] = []
        self._should_stream = False
    
    def is_streaming(self):
        return self._should_stream and len(self._viewer) > 0

    def register_viewer(self, viewer: VideoStreamViewer):
        """ Register a viewer to the stream.
        """
        self._viewer.append(viewer)
    
    def unregister_viewer(self, viewer: VideoStreamViewer):
        """ Unregister a viewer from the stream.
        """
        self._viewer.remove(viewer)
        if len(self._viewer) == 0:
            self._should_stream = False

    def start_stream(self):
        """ Start the stream.
        """
        self._should_stream = True
        self.stream()

    def stop_stream(self):
        """ Stop the stream.
        """
        self._should_stream = False

        for viewer in self._viewer:
            viewer.update(None)

        self._cap.release()

    def stream(self):
        """ Stream will run in a loop and read frames from the camera.
        """
        while self._should_stream:
            if len(self._viewer) <= 0:
                print("No viewers registered")
                break

            if not self._cap.isOpened():
                print("Camera not opened")
                break

            if not self._should_stream:
                print("Streaming stopped")
                break

            ret, frame = self._cap.read()
            if not ret:
                break

            for viewer in self._viewer:
                viewer.update(frame)

    def _bootstrap_camera(self, config):
        self._cap.set(cv2.CAP_PROP_FPS, int(config["fps"]))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(config["width"]))
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(config["height"]))
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_stream()
        if exc_type is not None:
            print(f"Exception: {exc_type}, {exc_val}, {exc_tb}")
            return False
        return True