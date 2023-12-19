#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import shutil
import sys
import subprocess
import os
import platform
import bpy

blender_dependencies_directory = "lib/python3.10/site-packages"
blender_dependencies_path = os.path.join(sys.prefix, blender_dependencies_directory)

opencue_home = os.environ['OPENCUE_HOME']
pyoutline_directory = "pyoutline/outline"
filesequence_directory = "pycue/FileSequence"
opencue_directory = "pycue/opencue"

pyoutline_path = os.path.join(opencue_home, pyoutline_directory)
filesequence_path = os.path.join(opencue_home, filesequence_directory)
opencue_path = os.path.join(opencue_home, opencue_directory)

pyoutline_directory = "outline"
opencue_imported_directory = "opencue"
filesequence_directory = "FileSequence"
pyoutline_directory_path = os.path.join(sys.prefix, blender_dependencies_directory, pyoutline_directory)
opencue_directory_path = os.path.join(sys.prefix, blender_dependencies_directory, opencue_imported_directory)
filesequence_directory_path = os.path.join(sys.prefix, blender_dependencies_directory, filesequence_directory)

def isWindows():
    return os.name == 'nt'


def isMacOS():
    return os.name == 'posix' and platform.system() == "Darwin"


def isLinux():
    return os.name == 'posix' and platform.system() == "Linux"


def python_exec():
    if isWindows():
        return os.path.join(sys.prefix, 'bin', 'python.exe')
    elif isMacOS():
        try:
            # 2.92 and older
            path = bpy.app.binary_path_python
        except AttributeError:
            # 2.93 and later
            path = sys.executable
        return os.path.abspath(path)
    elif isLinux():
        return os.path.join(sys.prefix, 'bin', 'python3.10')  # Works on Blender 3.3.1 LTS
    else:
        print("sorry, still not implemented for ", os.name, " - ", platform.system)
        return os.path.join(sys.prefix, 'sys.prefix/bin', 'python')


def installModule():
    # Install OpenCue dependencies
    installOpencueModules()

    # installs External modules from requirements.txt file
    installExternalModules()

    print("\n----- OpenCue-Blender Installed Successfully -----")

def removeOpencueModules():
    # remove installed opencue dependencies
    shutil.rmtree(pyoutline_directory_path)
    shutil.rmtree(opencue_directory_path)
    shutil.rmtree(filesequence_directory_path)

def installExternalModules():
    # Get path of requirements file
    script_file = os.path.realpath(__file__)
    directory = os.path.dirname(script_file)
    file_name = "requirements.txt"
    requirements = os.path.join(directory, file_name)

    # identify for platform
    python_exe = python_exec()

    # upgrade pip
    print ("\n----- Installing External Dependencies -----")
    subprocess.call([python_exe, "-m", "ensurepip"])
    subprocess.call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    # install required external packages
    subprocess.call([python_exe, "-m", "pip", "install", "-r", requirements, "-t", blender_dependencies_path])
    print ("\n----- External Dependencies Installed Successfully -----")

def installOpencueModules():
    print ("----- Installing OpenCue Dependencies -----")
    shutil.copytree(pyoutline_path, pyoutline_directory_path)
    shutil.copytree(opencue_path, opencue_directory_path)
    shutil.copytree(pyoutline_path, filesequence_directory_path)
    print ("\n----- OpenCue Dependencies Installed Successfully -----")


