import threading
from subprocess import Popen
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

class The1OutOf0(irc.bot.SingleServerIRCBot):
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
              '!cmap <colormapname> [<colormapname> ...]')
          # elif args[1] in []:
          else:
            connection.privmsg(event.target, "I don't have that command")
        else:
          connection.privmsg(event.target, "Current commands: cmap/colormap/colourmap")

      elif is_command(event.arguments[0], ['cmap','colormap', 'colourmap'], True):
        parsed = event.arguments[0].split(' ')
        colormap = parsed[1]
        colormaps = plt.colormaps()

        if colormap in colormaps:
          if len(parsed) > 2:
            if len(parsed) > 100:
              # max to prevent someone trying to eat my RAM
              # auto Ban?
              return

            cat_segment_data = {'red': (), 'blue': (), 'green': ()}
            offset = 0
            for next_colormap in parsed[1:]:
              if next_colormap not in colormaps:
                return
              if next_colormap == 'the1outof0':
                # Auto ban?
                return

              segment_data = cm.get_cmap(next_colormap)._segmentdata
              for color in ['red', 'blue', 'green']:
                cat_segment_data[color] += tuple(((x[0]+offset)/(len(parsed)-1),
                                                   x[1],
                                                   x[2])
                                                  for x in segment_data[color])
              offset+=1

            custom = LinearSegmentedColormap('the1outof0',
                                             segmentdata=cat_segment_data)
            cm.register_cmap(cmap=custom)
            colormap = 'the1outof0'
            message = f'Changing colormap to a custom colormap'
          else:
            message = f'Changing colormap to {colormap}'
          connection.privmsg(event.target, message)
          logger.info(message)
          self.config['colormap'] = colormap
        else:
          connection.privmsg(event.target, f'{colormap} is not a valid colormap name. See: https://matplotlib.org/stable/tutorials/colors/colormaps.html')
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
  bot = The1OutOf0(config)

  def ctrl_c(signum, frame):
    logger.info(f"Disconnecting IRC")
    bot.stop()
  signal.signal(signal.SIGINT, ctrl_c)

  bot.start()
