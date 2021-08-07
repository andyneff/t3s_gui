#!/usr/bin/env python

import os
import json
import traceback

import tkinter as tk
import tkinter.ttk

import logging
logger = logging.getLogger(__name__)

import matplotlib.pyplot as plt

from t3s import T3sCamera

class T3sApp(tk.Tk):
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

    self.cam = T3sCamera(self.data)
    self.cam.start_capture()

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
    self.cam.stop_capture()
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
  cam.data['colormap'] = Var('jet')
  cam.data['colormap_reverse'] = Var(False)
  cam.data['clip_min'] = Var(0.04)
  cam.data['clip_min_percent'] = Var(True)
  cam.data['clip_max'] = Var(0.04)
  cam.data['clip_max_percent'] = Var(True)
  cam.data['gamma'] = Var(2.2)
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
