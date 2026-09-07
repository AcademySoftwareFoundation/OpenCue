
import os
import logging

from xml.dom.minidom import parseString
from xml.etree import ElementTree as Et
from packaging.version import Version

import outline
import FileSequence

logger = logging.getLogger("outline.backend._common")

def _serialize(launcher, use_pycuerun):
    """
    Serialize the outline part of the given L{OutlineLauncher} into a
    opencue job specification.

    :type launcher: L{OutlineLauncher}
    :param launcher: The outline launcher being used to launch the job.

    :rtype: str
    :return: A opencue job specification.
    """
    ol = launcher.get_outline()

    spec_version = Version(outline.config.get("outline", "spec_version"))

    root = Et.Element("spec")
    depends = Et.Element("depends")

    sub_element(root, "facility", launcher.get("facility"))
    sub_element(root, "show", launcher.get("show"))
    sub_element(root, "shot", launcher.get("shot"))
    user = launcher.get_flag("user")
    if not user:
        user = outline.util.get_user()
    sub_element(root, "user", user)
    if not launcher.get("nomail"):
        sub_element(root, "email", "%s@%s" % (user,
                                              outline.config.get("outline", "domain")))
    sub_element(root, "uid", str(outline.util.get_uid()))

    j = Et.SubElement(root, "job", {"name": ol.get_name()})
    sub_element(j, "paused", str(launcher.get("pause")))
    if spec_version >= Version("1.11"):
        sub_element(j, "priority", str(launcher.get("priority")))
    elif launcher.get("priority"):
        _warning_spec_version(spec_version, "priority")
    sub_element(j, "maxretries", str(launcher.get("maxretries")))
    if spec_version >= Version("1.13"):
        if ol.get_maxcores():
            sub_element(j, "maxcores", str(ol.get_maxcores()))
        if ol.get_maxgpus():
            sub_element(j, "maxgpus", str(ol.get_maxgpus()))
    else:
        if ol.get_maxcores():
            _warning_spec_version(spec_version, "maxcores")
        if ol.get_maxgpus():
            _warning_spec_version(spec_version, "maxgpus")
    sub_element(j, "autoeat", str(launcher.get("autoeat")))

    if ol.get_arg("localbook"):
        Et.SubElement(j, "localbook", ol.get_arg("localbook"))

    if launcher.get("os"):
        sub_element(j, "os", launcher.get("os"))
    elif os.environ.get("OL_OS", False):
        sub_element(j, "os", os.environ.get("OL_OS"))

    env = Et.SubElement(j, "env")
    for env_k, env_v in ol.get_env().items():
        # Only pre-setshot environment variables are
        # passed up to the cue.
        if env_v[1]:
            pair = Et.SubElement(env, "key", {"name": env_k})
            pair.text = env_v[0]

    layers = Et.SubElement(j, "layers")
    for layer in ol.get_layers():

        # Unregistered layers are in the job but don't show up on the cue.
        if not layer.get_arg("register"):
            continue

        # Don't register child layers with opencue.
        if layer.get_parent():
            continue

        # The layer will return a valid range if its range and
        # the job's range are compatible.  If not, skip launching
        # that layer.
        frame_range = layer.get_frame_range()
        if not frame_range:
            logger.info("Skipping layer %s, its range (%s) does not intersect "
                        "with ol range %s", layer, layer.get_arg("range"), ol.get_frame_range())
            continue

        spec_layer = Et.SubElement(layers, "layer",
                                   {"name": layer.get_name(),
                                    "type": layer.get_type()})
        if use_pycuerun:
            sub_element(spec_layer, "cmd",
                        " ".join(build_command(launcher, layer)))
        else:
            cmd = layer.get_arg("command")
            if cmd is None:
                raise TypeError(
                    "Layer '%s' has no command set. Set a 'command' argument on "
                    "the layer or enable use_pycuerun." % layer.get_name())
            if isinstance(cmd, str):
                sub_element(spec_layer, "cmd", cmd)
            else:
                sub_element(spec_layer, "cmd", " ".join(cmd))
        sub_element(spec_layer, "range", str(frame_range))
        sub_element(spec_layer, "chunk", str(layer.get_chunk_size()))

        # opencue specific options
        # Keeping 'threads' for backward compatibility
        cores = None
        if layer.is_arg_set("cores"):
            cores = layer.get_arg("cores")
        elif layer.is_arg_set("threads"):
            cores = layer.get_arg("threads")
        if cores is None:
            logger.debug("%s will use service cores.", layer.get_name())
        else:
            logger.debug("%s is set to override service cores.", layer.get_name())
            if layer.is_arg_set("cores") and layer.is_arg_set("threads"):
                logger.warning("%s has both cores and threads. Use cores.", layer.get_name())
            sub_element(spec_layer, "cores", "%0.1f" % float(cores))

        if layer.is_arg_set("threadable"):
            sub_element(spec_layer, "threadable",
                        bool_to_str(layer.get_arg("threadable")))

        if layer.get_arg("memory"):
            sub_element(spec_layer, "memory", "%s" % (layer.get_arg("memory")))

        gpus = None
        if layer.get_arg("gpus"):
            if spec_version >= Version("1.12"):
                gpus = layer.get_arg("gpus")
            else:
                _warning_spec_version(spec_version, "gpus")

        gpu_memory = None
        if layer.get_arg("gpu_memory"):
            if spec_version >= Version("1.12"):
                gpu_memory = layer.get_arg("gpu_memory")
            else:
                _warning_spec_version(spec_version, "gpu_memory")

        if gpus or gpu_memory:
            # Cuebot expects non-zero positive value on gpus and gpu_memory
            if gpus is None:
                gpus = 1
            if gpu_memory is None:
                gpu_memory = "1g"

            sub_element(spec_layer, "gpus", "%d" % gpus)
            sub_element(spec_layer, "gpu_memory", "%s" % gpu_memory)

        if layer.get_arg("timeout"):
            if spec_version >= Version("1.10"):
                sub_element(spec_layer, "timeout", "%s" % (layer.get_arg("timeout")))
            else:
                _warning_spec_version(spec_version, "timeout")

        if layer.get_arg("timeout_llu"):
            if spec_version >= Version("1.10"):
                sub_element(spec_layer, "timeout_llu", "%s" % (layer.get_arg("timeout_llu")))
            else:
                _warning_spec_version(spec_version, "timeout_llu")

        if os.environ.get("OL_TAG_OVERRIDE", False):
            sub_element(spec_layer, "tags",
                        scrub_tags(os.environ["OL_TAG_OVERRIDE"]))
        elif layer.get_arg("tags"):
            sub_element(spec_layer, "tags", scrub_tags(layer.get_arg("tags")))

        layer_limits = layer.get_limits()
        if layer_limits:
            limits = Et.SubElement(spec_layer, "limits")
            for limit_name in layer_limits:
                limit = Et.SubElement(limits, "limit")
                limit.text = limit_name

        layer_env = Et.SubElement(spec_layer, "env")
        for env_k, env_v in layer.get_envs().items():
            pair = Et.SubElement(layer_env, "key", {"name": "{}".format(env_k)})
            pair.text = env_v

        services = Et.SubElement(spec_layer, "services")
        service = Et.SubElement(services, "service")
        try:
            service.text = layer.get_service().split(",")[0].strip()
        except (AttributeError, IndexError):
            service.text = "default"

        if spec_version >= Version("1.15"):
            layer_outputs = Et.SubElement(spec_layer, "outputs")
            outputs = layer.get_outputs()
            for output_name in outputs:
                output_path = outputs[output_name]
                output = Et.SubElement(layer_outputs, "output", {"name": output_name})
                output.text = output_path.get_path()

        build_dependencies(ol, layer, depends)

    if not layers:
        raise outline.exception.OutlineException(
            "Failed to launch job. There are no layers with frame "
            "ranges that intersect the job's frame range: %s" % ol.get_frame_range())

    # Dependencies go after all of the layers
    root.append(depends)

    xml = [
        '<?xml version="1.0"?>',
        '<!DOCTYPE spec PUBLIC "SPI Cue  Specification Language" '
        '"http://localhost:8080/spcue/dtd/cjsl-%s.dtd">' % spec_version,
        Et.tostring(root).decode()
    ]

    result = "".join(xml)
    logger.debug(parseString(result).toprettyxml())
    return result

def sub_element(root, tag, text):
    """Convenience method to create a sub element with text"""
    e = Et.SubElement(root, tag)
    e.text = text
    return e

def build_dependencies(ol, layer, all_depends):
    """
    Iterate through all the layer's dependencies and
    add them to the job spec.
    """
    for dep in layer.get_depends():

        depend = Et.SubElement(all_depends, "depend",
                               type=dep.get_type(),
                               anyframe=bool_to_str(dep.is_any_frame()))

        if dep.get_type() == outline.depend.DependType.LayerOnSimFrame:

            frame_range = dep.get_depend_on_layer().get_frame_range()
            first_frame = FileSequence.FrameSet(frame_range)[0]

            sub_element(depend, "depjob", ol.get_name())
            sub_element(depend, "deplayer", layer.get_name())
            sub_element(depend, "onjob", ol.get_name())
            sub_element(depend, "onframe", "%04d-%s"
                        % (first_frame, dep.get_depend_on_layer().get_name()))
        else:
            sub_element(depend, "depjob", ol.get_name())
            sub_element(depend, "deplayer", layer.get_name())
            sub_element(depend, "onjob", ol.get_name())
            sub_element(depend, "onlayer", dep.get_depend_on_layer().get_name())


def scrub_tags(tags):
    """
    Ensure that layer tags pass in as a string are formatted properly.
    """
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split("|")
                if tag.strip().isalnum()]
    return " | ".join(tags)


def bool_to_str(value):
    """
    If the given value evaluates to True, return
    "True", else return "False"
    """
    if value:
        return "True"
    return "False"



def serialize(launcher):
    """
    Serialize the outline part of the given L{OutlineLauncher} into an OpenCue job specification,
    using pycuerun to wrap the job commands.

    :type launcher: L{OutlineLauncher}
    :param launcher: The outline launcher being used to launch the job.

    :rtype: str
    :return: A opencue job specification.
    """
    return _serialize(launcher, use_pycuerun=True)


def serialize_simple(launcher):
    """
    Serialize the outline part of the given L{OutlineLauncher} into an OpenCue job specification,
    skipping the pycuerun wrapper in favor of launching the job commands directly.

    :type launcher: L{OutlineLauncher}
    :param launcher: The outline launcher being used to launch the job.

    :rtype: str
    :return: A opencue job specification.
    """
    return _serialize(launcher, use_pycuerun=False)


def _warning_spec_version(spec_version, feature):
    logger.warning("spec_version=%s doesn't support %s", spec_version, feature)

def build_command(launcher, layer):
    """
    Build and return a pycuerun shell command for the given layer.

    :type  launcher : outline.cuerun.OutlineLauncher
    :param launcher : The outline launcher.

    :type  layer : Layer
    :param layer : The layer to build a command for.

    :rtype: list
    :return: The shell command to run for a the given layer.
    """
    command = []

    if layer.get_arg("strace"):
        command.append("strace")
        command.append("-ttt")
        command.append("-T")
        command.append("-e")
        command.append("open,stat")
        command.append("-f")
        command.append("-o")
        command.append("%s/strace.log" % layer.get_path())

    if layer.get_arg("wrapper"):
        wrapper = layer.get_arg("wrapper")
    elif layer.get_arg("setshot", True):
        wrapper = "%s/opencue_wrap_frame" % outline.config.get("outline", "wrapper_dir")
    else:
        wrapper = "%s/opencue_wrap_frame_no_ss" % outline.config.get(
            "outline", "wrapper_dir")

    command.append(wrapper)
    command.append(outline.config.get("outline", "user_dir"))
    command.append("%s/pycuerun" % outline.config.get("outline", "bin_dir"))
    command.append("%s -e #IFRAME#-%s" % (launcher.get_outline().get_path(),
                                          layer.get_name()))
    command.append("--version %s" % outline.versions.get_version("outline"))
    repos = outline.versions.get_repos()
    if repos and repos.strip():
        command.append("--repos %s" % repos.strip())
    command.append("--debug")

    if launcher.get("dev"):
        command.append("--dev")

    if launcher.get("devuser"):
        command.append("--dev-user %s" % launcher.get("devuser"))

    return command
