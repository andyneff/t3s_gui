#!/usr/bin/env python

import os
import json
import traceback

import tkinter as tk
import tkinter.ttk

import logging
logger = logging.getLogger(__name__)

import matplotlib.pyplot as plt

from t3s import T3sCamera, special_colormaps
from twitch import IrcBot, ColormapCommand


class T3sApp(tk.Tk):
  def __init__(self):
    super().__init__()

    self.iconbitmap(os.path.join(os.path.dirname(__file__), 'power.ico'))

    self.config_file = os.path.expanduser('~/.config/t3s_gui.json')

    self.title('T3S')

    colormaps = [x for x in plt.colormaps() if not x.endswith('_r')]
    favorite_colormaps = ['gray', 'jet', 'hsv', 'gnuplot2'] + special_colormaps
    colormaps = favorite_colormaps + [x for x in colormaps if x not in favorite_colormaps]

    self.colormap = tk.StringVar()
    self.colormap_reverse = tk.BooleanVar()
    self.clip_min = tk.DoubleVar()
    self.clip_min_percent = tk.BooleanVar()
    self.clip_max = tk.DoubleVar()
    self.clip_max_percent = tk.BooleanVar()
    self.gamma = tk.DoubleVar()
    self.histogram_equalization = tk.BooleanVar()
    self.irc_channel = tk.StringVar()
    self.irc_username = tk.StringVar()
    self.irc_oauth = tk.StringVar()

    self.colormap.trace_add('write', self.update_colormap)
    self.colormap_reverse.trace_add('write', self.update_colormap)
    self.clip_min.trace_add('write', self.update_clip_min)
    self.clip_max.trace_add('write', self.update_clip_max)
    self.gamma.trace_add('write', self.update_gamma)
    self.histogram_equalization.trace_add('write', self.update_gamma)
    self.irc_channel.trace_add('write', self.update_irc)
    self.irc_username.trace_add('write', self.update_irc)
    self.irc_oauth.trace_add('write', self.update_irc)

    self.irc = None
    self.data = {}
    self.load()

    frame = tk.ttk.Frame(self)
    frame.pack()
    tk.Label(frame, text="Colormap").pack(side='left')
    self.colormap_widget = tk.ttk.Combobox(frame, textvariable=self.colormap)
    self.colormap_widget['values'] = colormaps
    self.colormap_widget.pack(side='left')
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

    self.histogram_equalization_widget = tk.ttk.Checkbutton(frame, text='eq',
        var=self.histogram_equalization, command=self.update_gamma)
    self.histogram_equalization_widget.pack(side='left')

    frame = tk.ttk.Frame(self)
    frame.pack()
    tk.Label(frame, text="IRC Channel").pack(side='left')
    self.irc_channel_entry = tk.ttk.Entry(frame,
                                           textvariable=self.irc_channel)
    self.irc_channel_entry.pack(side='left')

    frame = tk.ttk.Frame(self)
    frame.pack()
    tk.Label(frame, text="IRC Username").pack(side='left')
    self.irc_username_entry = tk.ttk.Entry(frame,
                                           textvariable=self.irc_username)
    self.irc_username_entry.pack(side='left')

    frame = tk.ttk.Frame(self)
    frame.pack()
    tk.Label(frame, text="IRC OAuth").pack(side='left')
    self.irc_oauth_entry = tk.ttk.Entry(frame, show='*',
                                        textvariable=self.irc_oauth)
    self.irc_oauth_entry.pack(side='left')

    self.bind('<Return>', self.return_handler)
    self.bind('<Escape>', self.esc_handler)

    self.bind('<Up>', self.scroll_colormap_handler)
    self.bind('<Down>', self.scroll_colormap_handler)

    self.cam = T3sCamera(self.data)
    self.cam.start_capture()

    if self.data['irc_channel'] and self.data['irc_username'] and self.data['irc_oauth']:
      self.irc = IrcBot(self.data)
      self.irc.spawn()

  def esc_handler(self, event):
    self.destroy()

  def return_handler(self, event):
    logger.info("You hit return.")
    colormap = ColormapCommand.process_colormap_args(*self.colormap_widget.get().split())
    if colormap == 'custom':
      self.data['colormap'] = colormap
      self.data['colormap_reverse'] = False

  def scroll_colormap_handler(self, event):
    current = self.colormap_widget.current()
    if event.keysym == 'Up':
      current = current - 1
    elif event.keysym == 'Down':
      current = current + 1
    if current < 0:
      current = len(self.colormap_widget['values'])-1
    if current >= len(self.colormap_widget['values']):
      current = 0
    self.colormap_widget.current(current)

  def update_gamma(self, var=None, idx=None, mode=None):
    self.data['gamma'] = self.gamma.get()
    self.data['histogram_equalization'] = self.histogram_equalization.get()

  def update_colormap(self, var=None, idx=None, mode=None):
    colormap = self.colormap.get()
    self.data['colormap_reverse'] = self.colormap_reverse.get()
    if colormap in plt.colormaps():
      self.data['colormap'] = colormap
    elif colormap in special_colormaps:
      self.data['colormap'] = colormap
    else:
      # attempt custom here
      # see return handler...
      pass

  def update_clip_min(self, var=None, idx=None, mode=None):
    self.data['clip_min'] = self.clip_min.get()

  def update_clip_min_percent(self):
    self.data['clip_min_percent'] = self.clip_min_percent.get()
    if hasattr(self, 'cam'):
      if self.data['clip_min_percent']:
        # percent mode turned on
        self.clip_min_scale.configure(from_=0)
        self.clip_min_scale.configure(to=0.1)
        self.clip_min.set(((self.cam.last_frame <= self.cam.last_frame_min).sum())/self.cam.last_frame.size)
      else:
        # percent mode turns off
        self.clip_min_scale.configure(from_=self.cam.last_frame.min()-100)
        self.clip_min_scale.configure(to=self.cam.last_frame.max()+100)
        self.clip_min.set(self.cam.last_frame_min)

    self.update_clip_min()

  def update_clip_max(self, var=None, idx=None, mode=None):
    self.data['clip_max'] = self.clip_max.get()

  def update_clip_max_percent(self):
    self.data['clip_max_percent'] = self.clip_max_percent.get()

    if hasattr(self, 'cam'):
      if self.data['clip_max_percent']:
        # percent mode turned on
        self.clip_max_scale.configure(from_=0)
        self.clip_max_scale.configure(to=0.1)
        self.clip_max.set((self.cam.last_frame >= self.cam.last_frame_max).sum()/self.cam.last_frame.size)
      else:
        # percent mode turns off
        self.clip_max_scale.configure(from_=self.cam.last_frame.min()-100)
        self.clip_max_scale.configure(to=self.cam.last_frame.max()+100)
        self.clip_max.set(self.cam.last_frame_max)
    self.update_clip_max()

  def update_irc(self, var=None, idx=None, mode=None):
    self.data['irc_channel'] = self.irc_channel.get()
    self.data['irc_username'] = self.irc_username.get()
    self.data['irc_oauth'] = self.irc_oauth.get()

  def update(self):
    self.update_clip_min_percent()
    self.update_clip_max_percent()
    self.update_colormap()
    self.update_gamma()
    self.update_irc()

  def destroy(self, *args, **kwargs):
    try:
      self.save()
    except Exception as e:
      logger.critical('Failed to save')
      logger.critical(traceback.format_exc())
    self.cam.stop_capture()
    if self.irc:
      self.irc.unspawn()
    return super().destroy(*args, **kwargs)

  def save(self):
    os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
    with open(self.config_file, 'w') as fid:
      json.dump(self.data, fid)

  def load(self):
    options = {}
    if os.path.exists(self.config_file):
      with open(self.config_file, 'r') as fid:
        options = json.load(fid)

    colormap = options.get('colormap', 'gray')
    if colormap not in plt.colormaps():
      colormap = 'gray'
    self.colormap.set(colormap)
    self.colormap_reverse.set(options.get('colormap_reverse', False))
    self.clip_min.set(options.get('clip_min', 0.04))
    self.clip_min_percent.set(options.get('clip_min_percent', True))
    self.clip_max.set(options.get('clip_max', 0.04))
    self.clip_max_percent.set(options.get('clip_max_percent', True))
    self.gamma.set(options.get('gamma', 2.2))
    self.histogram_equalization.set(options.get('histogram_equalization', False))

    self.irc_channel.set(options.get('irc_channel', ''))
    self.irc_username.set(options.get('irc_username', ''))
    self.irc_oauth.set(options.get('irc_oauth', ''))

    self.update()

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  # test_cam()
  app = T3sApp()
  app.mainloop()
