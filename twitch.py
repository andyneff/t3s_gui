import signal
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

    signal.signal(signal.SIGINT, self.ctrl_c)

  def on_welcome(self, connection, event):
    connection.join(self.config['irc_channel'])
    logger.info(f"Joined channel {self.config['irc_channel']}")

  def on_pubmsg(self, connection, event):
    if event.target == self.config['irc_channel']:
      if is_command(event.arguments[0], ['cmap','colormap', 'colourmap'], True):
        colormap = event.arguments[0].split(' ')[1]
        if colormap in plt.colormaps():
          connection.privmsg(event.target, f'Changing colormap to {colormap}')
        else:
          connection.privmsg(event.target, f'{colormap} is not a valid colormap name. See: https://matplotlib.org/stable/tutorials/colors/colormaps.html')

  def ctrl_c(self, signum, frame):
    logger.info(f"Disconnecting IRC")
    self.die(msg="")

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)

  import json, os
  with open(os.path.expanduser('~/.config/t3s_gui.json'), 'r') as fid:
    config = json.load(fid)
  bot = The1OutOf0(config)
  bot.start()
