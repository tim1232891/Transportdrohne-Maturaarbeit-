from picamera2 import Picamera2, Preview
from libcamera import controls
import time
import apriltag
import cv2
import numpy as np
import asyncio 


async def camera_loop(queue_find: asyncio.Queue, stop_event: asyncio.Event):
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"format": "BGR888", "size": (1536, 864)})
    picam2.configure(config)
    picam2.start()
    detector = Detector()

    loop = asyncio.get_running_loop()

    try:
        while not stop_event.is_set():
            frame = await loop.run_in_executor(None, picam2.capture_array)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            results = detector.detect(gray)
            if results:

                corners = results[0].corners
                print(corners)
                pts = np.array(corners, np.int32)
                pts = pts.reshape((-1, 1, 2))
                conf = picam2.camera_configuration()
                size = conf["main"]["size"]  
                center = np.array(size)/2
                print(center)
                print(center.dtype)
                await queue_find.put((corners, size))
                await asyncio.sleep(0.5)
            await asyncio.sleep(0.1)
    finally:
        picam2.stop()
