import threading
from subprocess import Popen
from functools import partial

import logging
logger = logging.getLogger(__name__)

import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap
import irc.bot

def is_command(message, commands=[], required_argument=False):
  for command in commands:
    if message.startswith(f'!{command}{" " if required_argument else ""}'):
      return True
  return False

# def cat_maps(*args):
#   cat_segment_data = {'red': (), 'blue': (), 'green': ()}
#   offset = 0
#   for arg in args:
#     segment_data = cm.get_cmap(arg)._segmentdata
#     for color in ['red', 'blue', 'green']:
#       cat_segment_data[color] = cat_segment_data[color] + tuple(((x[0]+offset)/len(args), x[1], x[2]) for x in segment_data[color])
#     offset+=1
#   return LinearSegmentedColormap('custom', cat_segment_data)

def get_colormap_i(colormap):
  colormaps = plt.colormaps()
  try:
    return colormaps[[x.lower() for x in colormaps].index(colormap.lower())]
  except ValueError:
    return None

def cat_maps(map_name, *args):
  colormaps=[get_colormap_i(x) for x in args]
  def band(points, color):
    idx = (int(x*len(args)) if x != 1 else len(args)-1 for x in points)
    return [cm.get_cmap(colormaps[i])(x*len(args) - i)[color] for x,i in zip(points, idx)]
  cat_segment_data = {'red': partial(band, color=0),
                      'green': partial(band, color=1),
                      'blue': partial(band, color=2)}
  return LinearSegmentedColormap(map_name, cat_segment_data)

class IrcBot(irc.bot.SingleServerIRCBot):
  def __init__(self, config):
    self.config = config

    super().__init__([('irc.twitch.tv', 6667, self.config['irc_oauth'])],
                     self.config['irc_username'],
                     self.config['irc_username'])

    self.thread = None

  def start(self):
    self._connect()
    self.running = True
    while self.running:
      self.reactor.process_once(timeout=0.2)

  def stop(self):
    self.running = False

  def spawn(self):
    self.thread = threading.Thread(target=self.start)
    self.thread.start()

  def unspawn(self):
    self.stop()
    self.disconnect()
    if self.thread:
      self.thread.join(1)
      if self.thread.is_alive():
        logging.error('IRC thread did not end')

  def on_welcome(self, connection, event):
    connection.join(self.config['irc_channel'])
    logger.info(f"Joined channel {self.config['irc_channel']}")

  def on_pubmsg(self, connection, event):
    if event.target == self.config['irc_channel']:
      if is_command(event.arguments[0], ['help']):
        args = event.arguments[0].split(' ')
        if len(args) > 1:
          if args[1] in ['cmap', 'colormap', 'colourmap']:
            connection.privmsg(event.target,
              f'The !{args[1]} command can be used to change the colors of the camera. Usage: !{args[1]} <colormapname> [<colormapname> ...]. Try "!{args[1]} gray hsv"')
          # elif args[1] in []:
          else:
            connection.privmsg(event.target, "I don't have that command")
        else:
          connection.privmsg(event.target, 'Current commands: cmap/colormap/colourmap. Usage: !help <command>, to get more information about a specific command. Try "!help cmap"')

      elif is_command(event.arguments[0], ['cmap','colormap', 'colourmap'], True):
        parsed = event.arguments[0].split(' ')
        colormap = get_colormap_i(parsed[1])

        if colormap is not None:
          if len(parsed) > 2:
            if len(parsed) > 100 or 'custom' in parsed:
              # max to prevent someone trying to eat my RAM
              # auto Ban?
              return
            colormap = 'custom'
            custom = cat_maps(colormap, *parsed[1:])
            cm.register_cmap(cmap=custom)
            message = f'Changing colormap to a custom colormap'
          else:
            message = f'Changing colormap to {colormap}'
          connection.privmsg(event.target, message)
          logger.info(message)
          self.config['colormap'] = colormap
        else:
          connection.privmsg(event.target, f'That was not a valid colormap name. See: https://matplotlib.org/stable/tutorials/colors/colormaps.html')
      else:
        Popen(['powershell', '-NoProfile', '-Command',
               '''$w=New-Object System.Media.SoundPlayer
               $filename = (Get-ItemProperty -Path HKCU:\\AppEvents\\Schemes\\Apps\\.Default\\Notification.IM\\.Current).'(default)'
               $w.SoundLocation = $filename
               $w.playsync()'''])

if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)

  import json, os, signal
  with open(os.path.expanduser('~/.config/t3s_gui.json'), 'r') as fid:
    config = json.load(fid)
  bot = IrcBot(config)

  def ctrl_c(signum, frame):
    logger.info(f"Disconnecting IRC")
    bot.stop()
  signal.signal(signal.SIGINT, ctrl_c)

  bot.start()
