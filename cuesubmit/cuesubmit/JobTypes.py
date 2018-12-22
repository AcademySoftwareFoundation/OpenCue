

from cuesubmit.ui import SettingsWidgets


class JobTypes(object):
    """Base Job Types available in the UI.
    Plugin apps can subclass this to change out the mapping
    to enable customized settings widgets.
    """

    SHELL = 'Shell'
    MAYA = 'Maya'
    NUKE = 'Nuke'

    SETTINGS_MAP = {
        SHELL: SettingsWidgets.ShellSettings,
        MAYA: SettingsWidgets.BaseMayaSettings,
        NUKE: SettingsWidgets.ShellSettings
    }

    def __init__(self):
        pass

    @classmethod
    def build(cls, jobType, *args, **kwargs):
        """Factory method for creating a settings widget."""
        return cls.SETTINGS_MAP[jobType](*args, **kwargs)

    @classmethod
    def types(cls):
        """return a list of types available."""
        return [cls.SHELL, cls.MAYA, cls.NUKE]
