import pyvirtualcam
import numpy as np
import threading

def fun():
  with pyvirtualcam.Camera(width=1280, height=720, fps=20) as cam:
    print(f'Using virtual camera: {cam.device}')
    frame = np.zeros((cam.height, cam.width, 3), np.uint8)  # RGB
    # while True:
    for x in range(100):
      frame[:] = cam.frames_sent % 255  # grayscale animation
      cam.send(frame)
      cam.sleep_until_next_frame()

      print(cam._fps_counter.avg_fps, cam._extra_time_per_frame*20)

if __name__ == '__main__':
  thread = threading.Thread(target=fun)
  thread.start()
  thread.join()
  print('done')