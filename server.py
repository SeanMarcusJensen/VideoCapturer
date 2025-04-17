import asyncio
from pydantic import BaseModel
import yaml
from fastapi import FastAPI, Response, WebSocket
from fastapi.responses import StreamingResponse
from streaming.viewer import VideoStreamViewer
import cv2
import threading
import os

class FastAPIStreamViewer(VideoStreamViewer):
    def __init__(self):
        super().__init__()
        self._current_viewer_count = 0
        self._latest_frame = None
        self._new_frame = False
        self._lock = threading.Lock()
    
    def update(self, frame):
        with self._lock:
            self._latest_frame = frame

    def get_mjpeg_stream(self):
        MAX_VIEWERS = 5
        if self._current_viewer_count >= MAX_VIEWERS:
            raise RuntimeError("Too many connections")

        def generate():
            self._current_viewer_count += 1
            try:
                while True:
                    with self._lock:
                        frame = self._latest_frame

                    if frame is None:
                        yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + b'\r\n')

                    ret, jpeg = cv2.imencode('.jpg', self._latest_frame)
                    if ret:
                        yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

            except GeneratorExit:
                print("[MJPEG Stream] Client disconnected, stream stopped.")
                self._current_viewer_count -= 1
                return
            except Exception as e:
                print(f"Error in stream: {e}")
            finally:
                print("[MJPEG Stream] Client disconnected, stream stopped.")
                self._current_viewer_count -= 1

        return generate


# --- FastAPI app ---
app = FastAPI()
fastapi_viewer = FastAPIStreamViewer()
config = yaml.safe_load(open("config.yml"))

class RegisterDeviceModel(BaseModel):
    device_id: int
    device_name: str


@app.get("/health")
def read_root():
    return Response(content="OK", media_type="text/plain", status_code=200)

@app.post("/register")
async def register_device(model: RegisterDeviceModel):
    if os.path.exists(config["secrets_file"]):
        return Response(content="Secret file already exists", status_code=400)
    
    text = "device_id: " + str(model.device_id)
    with open(config["secrets_file"], 'w') as file:
        file.write(text)
    print(f"Device ID {model.device_id} registered successfully.")
    
    return Response(content="Device ID registered successfully", status_code=201)

@app.get("/stream")
async def video_feed():
    try:
        return StreamingResponse(fastapi_viewer.get_mjpeg_stream()(),
                                media_type='multipart/x-mixed-replace; boundary=frame')
    except RuntimeError as e:
        print(f"Runtime error: {e}")
        return Response(status_code=500)

@app.websocket("/stream/ws")
async def websocket_endpoint(ws: WebSocket):
    try:
        await ws.accept()
        while True:
            # grab the latest frame from your viewer
            frame = fastapi_viewer._latest_frame  # expose .latest_frame via a property
            if frame is None:
                await asyncio.sleep(0.01)
                continue

            # JPEG‐encode
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue

            # send raw bytes
            await ws.send_bytes(jpeg.tobytes())

            # throttle to your desired FPS
            await asyncio.sleep(1.0 / 30) # 30 FPS

    except asyncio.CancelledError:
        # client disconnected
        print("[WebSocket] Client disconnected, stream stopped.")
        await ws.close()
    except RuntimeError as e:
        print(f"[WebSocket] Runtime error: {e}")
        await ws.close()
    except KeyboardInterrupt:
        # server shutdown
        print("[WebSocket] Server shutting down.")
        await ws.close()
    except ConnectionResetError:
        # client disconnected
        print("[WebSocket] Connection reset by peer.")
        await ws.close()
    except Exception as e:
        # client disconnected
        print(f"[WebSocket] Exception: {e}")
        await ws.close()

if __name__ == "__main__":
    import uvicorn
    import yaml
    config = yaml.safe_load(open("config.yml"))
    host = config["host"]
    port = config["port"]
    uvicorn.run(app, host=host, port=port)
    should_steam = False


