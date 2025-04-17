if __name__ == "__main__":
    import time
    import yaml
    import threading
    from streaming import VideoStream
    from viewers import DisplayViewer, MonitoringViewer

    # Start FastAPI in a background thread
    import uvicorn
    from server import app, fastapi_viewer

    config = yaml.safe_load(open("config.yml"))

    api_thread = threading.Thread(target=lambda: uvicorn.run(app, host=config['host'], port=int(config['port'])), daemon=True)

    with VideoStream("config.yml") as stream:
        display = DisplayViewer()
        recorder = MonitoringViewer(fps=30)
        stream.register_viewer(display)
        stream.register_viewer(fastapi_viewer)
        stream.register_viewer(recorder)
        monitoring_thread = threading.Thread(target=recorder.monitor, daemon=True)

        # import RPi.GPIO as GPIO
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # def gpio_callback(channel):
        #     print("[GPIO] Trigger event detected!")
        #     recorder.trigger()

        # GPIO.add_event_detect(17, GPIO.FALLING, callback=gpio_callback, bouncetime=300)

        try:
            monitoring_thread.start()
            api_thread.start()
            stream.start_stream()
        except KeyboardInterrupt:
            # GPIO.cleanup()
            print('error')
        finally:
            print("Stopping stream...")
            display.cleanup()
            api_thread.join(0.5)
            monitoring_thread.join(0.5)
            stream.unregister_viewer(display)
            stream.unregister_viewer(recorder)
            stream.unregister_viewer(fastapi_viewer)
            stream.stop_stream()
            print("Stream stopped.")

