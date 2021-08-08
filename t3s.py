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
  frame_min = frame.min()
  frame_max = frame.max()

  histogram, bin_edges = np.histogram(frame, bins=range(frame_min, frame_max+2))
  cdf = np.cumsum(histogram)

  if min is not None:
    dra_min = np.clip(min, 0, 1) * frame.size
    try:
      dra_min = next((idx for idx, val in np.ndenumerate(cdf) if val > dra_min))[0] - 1
    except StopIteration:
      dra_min = len(cdf) - 1
    dra_min += frame_min
  else:
    dra_min = frame_min

  if max is not None:
    dra_max = (1-np.clip(max, 0, 1)) * frame.size
    try:
      dra_max = next((idx for idx, val in np.ndenumerate(np.flip(cdf)) if val < dra_max))[0]
    except StopIteration:
      dra_max = len(cdf) - 1
    dra_max = len(cdf) - dra_max - 1
    dra_max += frame_min
  else:
    dra_max = frame_max

  return (dra_min, dra_max)

class T3sCamera:
  def __init__(self, data={}, camera_index=0, capture_mode=0x8004):
    self.data = data

    self.cap = cv2.VideoCapture(camera_index)
    self.cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
    # Use raw mode
    self.cap.set(cv2.CAP_PROP_ZOOM, capture_mode)

  def __del__(self):
    self.cap.release()

  def grab_frame(self):
    ret, frame = self.cap.read()
    frame = frame.view(np.uint16).reshape([292, 384])
    frame = frame[:288,...]

    return frame

  def camera_capture(self):

    # cap.read()
    with pyvirtualcam.Camera(width=384, height=288, fps=25) as cam:
      logger.debug(f'Using virtual camera: {cam.device}')
      frame = np.zeros((cam.height, cam.width, 3), np.uint8)  # RGB

      t0 = time.time()-29

      while self.running:
        try:
          frame = self.grab_frame()
          self.last_frame = frame # Save copy for async calcs

          use_percent = self.data['clip_min_percent'] or self.data['clip_max_percent']
          if use_percent:
            dra_min, dra_max = dra_frame(frame,
              self.data['clip_min'] if self.data['clip_min_percent'] else None,
              self.data['clip_max'] if self.data['clip_max_percent'] else None)

          if self.data['clip_min_percent']:
            frame_min = dra_min
          else:
            frame_min = self.data['clip_min']

          if self.data['clip_max_percent']:
            frame_max = dra_max
          else:
            frame_max = self.data['clip_max']

          # Just sanity check
          frame_max = max(frame_min+1, frame_max)
          self.last_frame_min = frame_min
          self.last_frame_max = frame_max

          # Sketchy auto-exposure
          frame = frame.astype(np.float32)
          frame -= frame_min
          frame /= (frame_max-frame_min)
          frame = np.clip(frame, 0, 1)
          if self.data['gamma'] != 1:
            frame = frame ** (1/self.data['gamma'])

          mapper = cm.ScalarMappable(cmap=self.data['colormap'] +
                  ('_r' if self.data['colormap_reverse'] else ''))
          mapper.set_clim(0, 1)
          frame = mapper.to_rgba(frame, bytes=True)

          cam.send(frame[:,:,0:3])

          t1 = time.time()
          if t1 - t0 > 30:
            logger.debug(f'{cam.current_fps:.1f} fps')
            t0 = t1
        except:
          logger.critical(traceback.format_exc())
          time.sleep(0.01)

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