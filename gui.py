#!/usr/bin/env python

import os
import json
import traceback
import threading
import time
import logging
logger = logging.getLogger(__name__)

import tkinter as tk
import tkinter.ttk

from matplotlib import cm
import matplotlib.pyplot as plt
import pyvirtualcam
import numpy as np
import cv2

class T3sCamera:
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
            dra_min += frame_min
            print(f'Min {frame_min} -> {dra_min}')
            frame_min = max(dra_min, frame_min)

          if self.data['clip_max_percent']:
            clip_max = (1-np.clip(self.data['clip_max'], 0, 1)) * 112128.0
            try:
              dra_max = next((idx for idx, val in np.ndenumerate(np.flip(cdf)) if val < clip_max))[0] + 1
            except StopIteration:
              dra_max = 0
            dra_max += frame_max
            print(f'Max {frame_max} -> {dra_max}')
            frame_max = min(dra_max, frame_max)

          # Just sanity check
          frame_max = max(frame_min+1, frame_max)

          frame = frame.astype(np.float32)

          # Sketchy auto-exposure
          frame -= frame_min
          frame /= frame_max
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

class T3sApp(tk.Tk, T3sCamera):
  def __init__(self):
    super().__init__()

    self.config_file = '~/.config/t3s_gui.json'

    self.title('T3S')
#     self.geometry('300x500')

    colormaps = [x for x in plt.colormaps() if not x.endswith('_r')]
    colormaps = ['gray', 'jet', 'hsv'] + [x for x in colormaps if x not in ['gray', 'jet', 'hsv']]

    self.colormap = tk.StringVar()
    self.colormap_reverse = tk.BooleanVar()
    self.clip_min = tk.DoubleVar()
    self.clip_min_percent = tk.BooleanVar()
    self.clip_max = tk.DoubleVar()
    self.clip_max_percent = tk.BooleanVar()
    self.gamma = tk.DoubleVar()

    self.colormap.trace_add('write', self.update_colormap)
    self.colormap_reverse.trace_add('write', self.update_colormap)
    self.clip_min.trace_add('write', self.update_clip_min)
    self.clip_max.trace_add('write', self.update_clip_max)
    self.gamma.trace_add('write', self.update_gamma)

    self.data = {}
    self.load()

    frame = tk.ttk.Frame(self)
    frame.pack()
    tk.Label(frame, text="Colormap").pack(side='left')
    self.colormap_widget = tk.ttk.Combobox(frame, textvariable=self.colormap)
    self.colormap_widget['values'] = colormaps
    self.colormap_widget.pack(side='left')
    self.colormap_reverse.set(False)
    self.colormap_reverse_widget = tk.ttk.Checkbutton(frame, text='Reverse',
        var=self.colormap_reverse)
    self.colormap_reverse_widget.pack(side='left')

    frame = tk.ttk.Frame(self)
    frame.pack()
    tk.Label(frame, text="Clip min").pack(side='left')
    self.clip_min_scale = tk.ttk.Scale(frame, variable=self.clip_min, to=0.1)
    self.clip_min_scale.pack(side='left')
    self.clip_min_entry = tk.ttk.Entry(frame, width=10,
                                       textvariable=self.clip_min)
    self.clip_min_entry.pack(side='left')
    self.clip_min_percent.set(True)
    self.clip_min_percent_widget = tk.ttk.Checkbutton(frame, text='%',
        var=self.clip_min_percent, command=self.update_clip_min_percent)
    self.clip_min_percent_widget.pack(side='left')

    frame = tk.ttk.Frame(self)
    frame.pack()
    tk.Label(frame, text="Clip max").pack(side='left')
    self.clip_max_scale = tk.ttk.Scale(frame, variable=self.clip_max, to=0.1)
    self.clip_max_scale.pack(side='left')
    self.clip_max_entry = tk.ttk.Entry(frame, width=10,
                                       textvariable=self.clip_max)
    self.clip_max_entry.pack(side='left')
    self.clip_max_percent.set(True)
    self.clip_max_percent_widget = tk.ttk.Checkbutton(frame, text='%',
        var=self.clip_max_percent, command=self.update_clip_max_percent)
    self.clip_max_percent_widget.pack(side='left')

    frame = tk.ttk.Frame(self)
    frame.pack()
    tk.Label(frame, text="Gamma").pack(side='left')
    self.gamma_scale = tk.ttk.Scale(frame, variable=self.gamma, from_=0.5,
                                    to=5)
    self.gamma_scale.pack(side='left')

    self.gamma_entry = tk.ttk.Entry(frame, width=10, textvariable=self.gamma)
    self.gamma_entry.pack(side='left')

    self.bind('<Return>', self.return_handler)
    self.bind('<Escape>', self.esc_handler)
    self.start_capture()

  def esc_handler(self, event):
    self.destroy()

  def return_handler(self, event):
    logger.info("You hit return.")
    self.update_clip_min(self.clip_min_scale.get())
    self.update_clip_max(self.clip_max_scale.get())

  def update_gamma(self, var=None, idx=None, mode=None):
    self.data['gamma'] = self.gamma.get()

  def update_colormap(self, var=None, idx=None, mode=None):
    colormap = self.colormap.get()
    if self.colormap_reverse.get():
      colormap += '_r'
    if colormap in plt.colormaps():
      self.data['colormap'] = colormap
    print(self.data)

  def update_clip_min(self, var=None, idx=None, mode=None):
    self.data['clip_min'] = self.clip_min.get()

  def update_clip_min_percent(self, data):
    self.data['clip_min_percent'] = data
    self.update_clip_min()

  def update_clip_max(self, var=None, idx=None, mode=None):
    self.data['clip_max'] = self.clip_max.get()

  def update_clip_max_percent(self, data):
    self.data['clip_max_percent'] = data
    self.update_clip_max()

  def update(self):
    self.update_clip_min_percent(self.clip_min_percent.get())
    self.update_clip_max_percent(self.clip_max_percent.get())
    self.update_colormap()
    self.update_gamma()

  def destroy(self, *args, **kwargs):
    try:
      self.save()
    except Exception as e:
      logger.critical('Failed to save')
      logger.critical(traceback.format_exc())
    self.stop_capture()
    return super().destroy(*args, **kwargs)

  def save(self):
    os.makedirs(os.path.dirname(os.path.expanduser(self.config_file)), exist_ok=True)
    with open(os.path.expanduser(self.config_file), 'w') as fid:
      json.dump(self.data, fid)

  def load(self):
    options = {}
    if os.path.exists(os.path.expanduser(self.config_file)):
      with open(os.path.expanduser(self.config_file), 'r') as fid:
        options = json.load(fid)

    self.colormap.set(options.get('colormap', 'gray'))
    self.colormap_reverse.set(options.get('colormap_reverse', False))
    self.clip_min.set(options.get('clip_min', 0.04))
    self.clip_min_percent.set(options.get('clip_min_percent', True))
    self.clip_max.set(options.get('clip_max', 0.04))
    self.clip_max_percent.set(options.get('clip_max_percent', True))
    self.gamma.set(options.get('gamma', 2.2))

    self.update()

def test_cam():
  import signal

  class Var:
    def __init__(self, value):
      self.value = value
    def get(self):
      return self.value

  cam = T3sCamera()
  cam.colormap = Var('jet')
  cam.colormap_reverse = Var(False)
  cam.clip_min = Var(0.04)
  cam.clip_min_percent = Var(True)
  cam.clip_max = Var(0.04)
  cam.clip_max_percent = Var(True)
  cam.gamma = Var(2.2)
  cam.running = True

  def handler(signum, frame):
    cam.running = False
  signal.signal(signal.SIGINT, handler)

  cam.camera_capture()

if __name__ == "__main__":
  logging.basicConfig(level=logging.DEBUG)
  # test_cam()
  app = T3sApp()
  app.mainloop()
