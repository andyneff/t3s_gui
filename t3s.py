import threading
import time
import traceback

import logging
logger = logging.getLogger(__name__)

import pyvirtualcam
import numpy as np
import cv2
from matplotlib import cm

class T3sCamera:
  def __init__(self, data={}):
    self.data = data

  def camera_capture(self):
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
    # Use raw mode
    cap.set(cv2.CAP_PROP_ZOOM, 0x8004)

    with pyvirtualcam.Camera(width=384, height=288, fps=25, print_fps=True) as cam:
      logger.debug(f'Using virtual camera: {cam.device}')
      frame = np.zeros((cam.height, cam.width, 3), np.uint8)  # RGB

      t0 = time.time()-9

      # cam.send(np.zeros((288, 384, 3), dtype=np.uint8))
      # cam.sleep_until_next_frame()

      while self.running:
        try:
          ret, frame = cap.read() # Needs to be pipelines
          frame = frame.view(np.uint16).reshape([292, 384])
          frame = frame[:288,...]

          use_percent = self.data['clip_min_percent'] or self.data['clip_max_percent']

          if self.data['clip_min_percent']:
            frame_min = frame.min()
          else:
            frame_min = self.data['clip_min']

          if self.data['clip_max_percent']:
            frame_max = frame.max()
          else:
            frame_max = self.data['clip_max']

          # DRA
          if use_percent:
            histogram, bin_edges = np.histogram(frame, bins=range(frame_min, frame_max+2))
            cdf = np.cumsum(histogram)

          if self.data['clip_min_percent']:
            clip_min = np.clip(self.data['clip_min'], 0, 1) * 112128.0
            dra_min = next((idx for idx, val in np.ndenumerate(cdf) if val > clip_min))[0] - 1
            # i1 = np.clip(dra_min-5, 0, len(cdf))
            # i2 = np.clip(dra_min+5, 0, len(cdf))

            # print(f'{clip_min} @ {cdf[i1:dra_min]/112128.0} |{cdf[dra_min]/112128.0}| {cdf[dra_min+1:i2]/112128.0}')
            # # print(f'Min {frame_min} -> {dra_min}')

            dra_min += frame_min

            # frame_min = max(dra_min, frame_min)

          if self.data['clip_max_percent']:
            clip_max = (1-np.clip(self.data['clip_max'], 0, 1)) * 112128.0
            try:
              dra_max = next((idx for idx, val in np.ndenumerate(np.flip(cdf)) if val < clip_max))[0]
            except StopIteration:
              dra_max = 0
            dra_max = len(cdf) - dra_max - 1

            i1 = np.clip(dra_max-5, 0, len(cdf))
            i2 = np.clip(dra_max+5, 0, len(cdf))
            print(f'{clip_max} @ {cdf[i1:dra_max]/112128.0} |{cdf[dra_max]/112128.0}| {cdf[dra_max+1:i2]/112128.0}')

            dra_max += frame_min

          # Just sanity check
          dra_max = max(dra_min+1, dra_max)
          print(f'{frame_min}-{frame_max} : {dra_min}-{dra_max}')

          frame = frame.astype(np.float32)

          # Sketchy auto-exposure
          frame -= dra_min
          frame /= (dra_max-dra_min)
          frame = np.clip(frame, 0, 1)
          if self.data['gamma'] != 1:
            frame = frame ** (1/self.data['gamma'])

          frame = cm.ScalarMappable(cmap=self.data['colormap']).to_rgba(frame, bytes=True)

          cam.send(frame[:,:,0:3])

          # t1 = time.time()
          # if t1 - t0 > 1:
          #   t0 = t1
          #   logger.debug(f'{cam.current_fps:.1f} fps | {100*(cam._extra_time_per_frame * cam._fps):.0f} %')

          cam.sleep_until_next_frame()
        except:
          logger.critical(traceback.format_exc())
          time.sleep(0.01)

    cap.release()

  def start_capture(self):
    self.running = True
    self.camera_thread = threading.Thread(target=self.camera_capture)
    self.camera_thread.start()

  def stop_capture(self):
    self.running = False
    self.camera_thread.join(1)
    if self.camera_thread.is_alive():
      logging.error('Thread did not end')
