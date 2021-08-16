import subprocess
import os

import obspython as obs

glob = {}

def script_description():
  return """
  <center><h2>Auto start T3S camera gui</h2></center>
  <p>Auto starts T3S gui on OBS start</p>
  """

def script_properties():
  # set up the controls for the Program Output
  p = obs.obs_properties_create()
  gp = obs.obs_properties_create()
  obs.obs_properties_add_bool(p, "ts3_gui_autostart", "Autostart")
  obs.obs_properties_add_path(p, "ts3_python_path",
                              "Path to python executable (pythonw.exe)",
                              obs.OBS_PATH_FILE, '*.exe', None)
  obs.obs_properties_add_path(p, "ts3_obs_path", "Path to gui",
                              obs.OBS_PATH_DIRECTORY, '', None)

  return p

# def script_update(settings):
#   pass

def script_load(settings):
  pythonw = obs.obs_data_get_string(settings, "ts3_python_path")
  t3s_dir = obs.obs_data_get_string(settings, "ts3_obs_path")

  if obs.obs_data_get_bool(settings, "ts3_gui_autostart") and \
     os.path.isdir(t3s_dir) and os.path.exists(pythonw) and \
     not os.path.isdir(pythonw):
    pid = subprocess.Popen([pythonw, 't3s_gui.py'], cwd=t3s_dir)
    glob['pid'] = pid

def script_unload():
  try:
    glob['pid'].terminate()
  except:
    print("Error terminatinate")
