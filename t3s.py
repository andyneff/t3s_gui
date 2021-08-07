import threading
import time
import traceback

import logging
logger = logging.getLogger(__name__)

import pyvirtualcam
import numpy as np
import cv2
from matplotlib import cm

def dra_frame(frame, min=None, max=None):
  histogram, bin_edges = np.histogram(frame, bins=range(frame_min, frame_max+2))
  cdf = np.cumsum(histogram)

  # Process max before min, cause it uses frame_min
  if max is not None:
    frame_max = (1-np.clip(max, 0, 1)) * 112128.0
    try:
      frame_max = next((idx for idx, val in np.ndenumerate(np.flip(cdf)) if val < frame_max))[0]
    except StopIteration:
      frame_max = len(cdf) - 1
    frame_max = len(cdf) - frame_max - 1
    frame_max += frame_min

    self.dra_frame_max = frame_max

  if min is not None:
    clip_min = np.clip(min, 0, 1) * frame.size
    try:
      clip_min = next((idx for idx, val in np.ndenumerate(cdf) if val > clip_min))[0] - 1
    except StopIteration:
      clip_min = len(cdf) - 1
    frame_min += clip_min

    self.dra_frame_min = frame_min


class T3sCamera:
  def __init__(self, data={}):
    self.data = data

  def camera_capture(self):
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
    # Use raw mode
    cap.set(cv2.CAP_PROP_ZOOM, 0x8004)

    # cap.read()
    with pyvirtualcam.Camera(width=384, height=288, fps=25) as cam:
      logger.debug(f'Using virtual camera: {cam.device}')
      frame = np.zeros((cam.height, cam.width, 3), np.uint8)  # RGB

      t0 = time.time()-29

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

          # Process max before min, cause it uses frame_min
          if self.data['clip_max_percent']:
            frame_max = (1-np.clip(self.data['clip_max'], 0, 1)) * 112128.0
            try:
              frame_max = next((idx for idx, val in np.ndenumerate(np.flip(cdf)) if val < frame_max))[0]
            except StopIteration:
              frame_max = len(cdf) - 1
            frame_max = len(cdf) - frame_max - 1
            frame_max += frame_min

            self.dra_frame_max = frame_max

          if self.data['clip_min_percent']:
            clip_min = np.clip(self.data['clip_min'], 0, 1) * frame.size
            try:
              clip_min = next((idx for idx, val in np.ndenumerate(cdf) if val > clip_min))[0] - 1
            except StopIteration:
              clip_min = len(cdf) - 1
            frame_min += clip_min

            self.dra_frame_min = frame_min

          # Just sanity check
          frame_max = max(frame_min+1, frame_max)

          frame = frame.astype(np.float32)

          # Sketchy auto-exposure
          frame -= frame_min
          frame /= (frame_max-frame_min)
          frame = np.clip(frame, 0, 1)
          if self.data['gamma'] != 1:
            frame = frame ** (1/self.data['gamma'])

          frame = cm.ScalarMappable(cmap=self.data['colormap']).to_rgba(frame, bytes=True)

          cam.send(frame[:,:,0:3])

          t1 = time.time()
          if t1 - t0 > 30:
            logger.info(f'{cam.current_fps:.1f} fps')
            t0 = t1

          # This isn't needed, the read takes care of this
          # cam.sleep_until_next_frame()
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
      logging.error('T3S thread did not end')

def test_cam():
  import signal

  cam = T3sCamera()
  cam.data['colormap'] = 'jet'
  cam.data['colormap_reverse'] = False
  cam.data['clip_min'] = 0.04
  cam.data['clip_min_percent'] = True
  cam.data['clip_max'] = 0.04
  cam.data['clip_max_percent'] = True
  cam.data['gamma'] = 2.2
  cam.running = True

  def handler(signum, frame):
    cam.running = False
  signal.signal(signal.SIGINT, handler)

  cam.camera_capture()

if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)
  test_cam()