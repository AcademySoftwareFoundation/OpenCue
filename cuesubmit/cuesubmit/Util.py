
import Cue3


def getServices():
    """Return a list of service names from cuebot."""
    return [service.name for service in Cue3.api.getDefaultServices()]


def getShows():
    """Return a list of show names from cuebot."""
    return [show.name() for show in Cue3.api.getShows()]
