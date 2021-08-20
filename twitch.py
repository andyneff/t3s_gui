import threading
from subprocess import Popen
from functools import partial

import logging
logger = logging.getLogger(__name__)

import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap
import irc.bot

from t3s import special_colormaps

colormaps = plt.colormaps()


class Command:
  def __init__(self):
    self.commands = None
    self.min_args = None
    self.max_args = None

  def check_command(self, event, connection, bot):
    parsed = event.arguments[0].split(' ')
    word = parsed[0].lower()
    for command in self.commands:
      if word == f'!{command}':
        if self.min_args is not None and len(parsed) - 1 < self.min_args:
          self.not_enough_args(event, connection, word)
        elif self.max_args is not None and len(parsed) - 1 > self.max_args:
          self.too_many_args(event, connection, word)
        else:
          self.process(event, connection, bot, *parsed[1:])
        return True
    return False

  def not_enough_args(self, event, connection, word):
    connection.privmsg(event.target, f'{word} needs at least {self.min_args} argument{"s" if self.min_args>1 else ""}')

  def too_many_args(self, event, connection, word):
    connection.privmsg(event.target, f"{word} can't have more than {self.max_args} argument{'s' if self.min_args>1 else ''}")

  def process(self, event, connection, bot, *args):
    pass

  def help_text(self, command_name):
    return f"Todo. Write help for {command_name}"


class HelpCommand(Command):
  def __init__(self, supported_commands):
    super().__init__()
    self.commands = ['help']
    self.supported_commands = supported_commands
    self.max_args = 1

  def process(self, event, connection, bot, *args):
    if args:
      word = args[0].lower()
      for command in self.supported_commands:
        if word in command.commands:
          connection.privmsg(event.target, command.help_text(word))
          return
      connection.privmsg(event.target, f"I don't know how to help you with !{word}")
    else:
      commands = []
      for command in self.supported_commands:
        commands += command.commands
      connection.privmsg(event.target,
          f'Current commands: {"/".join(commands)}. Try "!help cmap"')

  def help_text(self, command_name):
    return f"Usage: !{command_name} <command>, to get more information " + \
           f"about a specific command. Try: \"!{command_name} cmap\""


class ColormapCommand(Command):
  def __init__(self):
    super().__init__()
    self.commands = ['cmap','colormap', 'colourmap']
    self.nargs = 1

  @staticmethod
  def get_colormap_i(colormap):
    try:
      return colormaps[[x.lower() for x in colormaps].index(colormap.lower())]
    except ValueError:
      return None

  @staticmethod
  def get_special_colormap_i(colormap):
    try:
      return special_colormaps[[x.lower() for x in special_colormaps].index(colormap.lower())]
    except ValueError:
      return None

  @staticmethod
  def cat_maps(map_name, *args):
    colormaps=[ColormapCommand.get_colormap_i(x) for x in args]
    if None in colormaps:
      return None
    def band(points, color):
      idx = (int(x*len(args)) if x != 1 else len(args)-1 for x in points)
      return [cm.get_cmap(colormaps[i])(x*len(args) - i)[color] for x,i in zip(points, idx)]
    cat_segment_data = {'red': partial(band, color=0),
                        'green': partial(band, color=1),
                        'blue': partial(band, color=2)}
    return LinearSegmentedColormap(map_name, cat_segment_data)

  @staticmethod
  def process_colormap_args(*args):
    colormap = ColormapCommand.get_colormap_i(args[0])

    if colormap is not None:
      if len(args) > 1:
        if len(args) > 100 or 'custom' in args:
          # max to prevent someone trying to eat my RAM
          # auto Ban?
          return
        custom = ColormapCommand.cat_maps('custom', *args)
        if custom is not None:
          colormap = 'custom'
          cm.register_cmap(cmap=custom)
        else:
          colormap = None
      return colormap

    colormap = ColormapCommand.get_special_colormap_i(args[0])
    if colormap is not None:
      return colormap + ' '.join(args[1:])
    return None

  def process(self, event, connection, bot, *args):
    colormap = ColormapCommand.process_colormap_args(*args)
    if colormap is None:
      message = f'That was not a valid colormap name. See: https://matplotlib.org/stable/tutorials/colors/colormaps.html'
      connection.privmsg(event.target, message)
      return
    elif colormap in special_colormaps:
      message = "Changing colormap to a special colormap"
    elif colormap == "custom":
      message = 'Changing colormap to a custom colormap'
    else:
      message = f'Changing colormap to {colormap}'
    connection.privmsg(event.target, message)
    bot.config['colormap'] = colormap

  def help_text(self, command_name):
    return f'The !{command_name} command can be used to change the colors ' + \
           f'of the camera. Usage: !{command_name} <colormapname> ' + \
           f'[<colormapname> ...]. Try "!{command_name} gray hsv"'


class IrcBot(irc.bot.SingleServerIRCBot):
  def __init__(self, config):
    self.config = config
    self.commands = []
    super().__init__([('irc.twitch.tv', 6667, self.config['irc_oauth'])],
                     self.config['irc_username'],
                     self.config['irc_username'])

    self.commands.append(ColormapCommand())
    self.commands.append(HelpCommand(self.commands))

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
      for command in self.commands:
        if command.check_command(event, connection, self):
          return
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
