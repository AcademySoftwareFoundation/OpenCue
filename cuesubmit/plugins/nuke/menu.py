import nuke
import CueNukeSubmitLauncher
menubar = nuke.menu('Nuke')
menu = menubar.addMenu('&Render')
menu.addCommand('Render on OpenCue', 'CueNukeSubmitLauncher.launchSubmitter()')

