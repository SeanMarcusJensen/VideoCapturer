from abc import ABC, abstractmethod

class VideoStreamViewer(ABC):
    @abstractmethod
    def update(self, frame):
        raise NotImplementedError("Subclasses must implement this method")