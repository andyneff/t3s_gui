import signal
import threading
from subprocess import Popen
import logging
logger = logging.getLogger(__name__)

import matplotlib.pyplot as plt
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
      if is_command(event.arguments[0], ['cmap','colormap', 'colourmap'], True):
        colormap = event.arguments[0].split(' ')[1]
        if colormap in plt.colormaps():
          message = f'Changing colormap to {colormap}'
          connection.privmsg(event.target, message)
          logger.info(message)
          self.config['colormap'] = colormap
        else:
          connection.privmsg(event.target, f'{colormap} is not a valid colormap name. See: https://matplotlib.org/stable/tutorials/colors/colormaps.html')
      elif is_command(event.arguments[0], ['dc']):
        logger.critical('DC!')
        self.disconnect()
        logger.critical('dced...')
      else:
        Popen(['powershell', '-NoProfile', '-Command',
               '''$w=New-Object System.Media.SoundPlayer
               $filename = (Get-ItemProperty -Path HKCU:\\AppEvents\\Schemes\\Apps\\.Default\\Notification.IM\\.Current).'(default)'
               $w.SoundLocation = $filename
               $w.playsync()'''])

if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG)

  import json, os
  with open(os.path.expanduser('~/.config/t3s_gui.json'), 'r') as fid:
    config = json.load(fid)
  bot = The1OutOf0(config)

  def ctrl_c(signum, frame):
    logger.info(f"Disconnecting IRC")
    bot.stop()
  signal.signal(signal.SIGINT, ctrl_c)

  bot.start()
