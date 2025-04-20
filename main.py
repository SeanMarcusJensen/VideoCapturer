if __name__ == "__main__":
    import yaml
    import threading
    from streaming import VideoStream
    from viewers import DisplayViewer, MonitoringViewer

    import uvicorn
    from server import app, fastapi_viewer

    config = yaml.safe_load(open("config.yml"))

    api_thread = threading.Thread(target=lambda: uvicorn.run(app, host=config['host'], port=int(config['port'])), daemon=True)

    with VideoStream("config.yml") as stream:
        display = DisplayViewer("config.yml")
        recorder = MonitoringViewer("config.yml")
        stream.register_viewer(display)
        stream.register_viewer(fastapi_viewer)
        stream.register_viewer(recorder)
        monitoring_thread = threading.Thread(target=recorder.monitor, daemon=True)

        try:
            monitoring_thread.start()
            api_thread.start()
            stream.start_stream()
        except KeyboardInterrupt:
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

