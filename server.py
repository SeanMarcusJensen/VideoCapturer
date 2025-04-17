import yaml
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from streaming.viewer import VideoStreamViewer
import cv2
import threading
import time

class FastAPIStreamViewer(VideoStreamViewer):
    def __init__(self):
        super().__init__()
        self._current_viewer_count = 0
        self._should_stream = False
        self._latest_frame = None
        self._new_frame = False
        self._lock = threading.Lock()
    
    def start_stream(self):
        """ Start the stream.
        """
        self._current_viewer_count += 1
        self._should_stream = self._current_viewer_count > 0
    
    def stop_stream(self):
        """ Stop the stream.
        """
        self._should_stream = self._current_viewer_count > 0
        self._latest_frame = None
        self._current_viewer_count -= 1
        if self._current_viewer_count < 0:
            self._current_viewer_count = 0
    
    def update(self, frame):
        with self._lock:
            self._latest_frame = frame
            self._new_frame = True

    def get_mjpeg_stream(self):
        MAX_VIEWERS = 5
        if self._current_viewer_count >= MAX_VIEWERS:
            raise RuntimeError("Too many connections")

        def generate():
            try:
                self.start_stream()
                while self._should_stream:
                    if not self._new_frame:
                        time.sleep(0.1)
                        continue

                    with self._lock:
                        if self._latest_frame is not None:
                            ret, jpeg = cv2.imencode('.jpg', self._latest_frame)
                            if ret:
                                yield (b'--frame\r\n'
                                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                        else:
                            yield (b'--frame\r\n'
                                b'Content-Type: image/jpeg\r\n\r\n' + b'\r\n')
                    self._new_frame = False
            except Exception as e:
                print(f"Error in stream: {e}")
            finally:
                print("[MJPEG Stream] Client disconnected, stream stopped.")
                self.stop_stream()

        return generate

# --- FastAPI app ---
app = FastAPI()
fastapi_viewer = FastAPIStreamViewer()
viewers = 0

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/stream")
async def video_feed():
    try:
        return StreamingResponse(fastapi_viewer.get_mjpeg_stream()(),
                                media_type='multipart/x-mixed-replace; boundary=frame')
    except RuntimeError as e:
        print(f"Runtime error: {e}")
        return Response(status_code=500)

@app.post("/stream/stop")
async def stop_stream():
    global fastapi_viewer
    fastapi_viewer.stop_stream()
    return Response(status_code=200)

@app.post("/stream/start")
async def stop_stream():
    global fastapi_viewer
    fastapi_viewer.start_stream()
    return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    import yaml
    config = yaml.safe_load(open("config.yml"))
    host = config["host"]
    port = config["port"]
    uvicorn.run(app, host=host, port=port)
    should_steam = False


