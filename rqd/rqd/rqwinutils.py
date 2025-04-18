"""
This module provides functionality to retrieve and display information about the logical processors in a Windows system.
It uses Windows API calls to gather details about processor groups, their affinities, and the number of logical cores.
Classes:
    GROUP_AFFINITY (Structure): Represents the affinity of a group of processors.
    PROCESSOR_RELATIONSHIP (Structure): Represents information about affinity within a processor group.
    DUMMYUNIONNAME (Union): A union of possible information to get about a processor.
    SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX (Structure): Contains information about the relationships of logical processors and related hardware.
Functions:
    get_logical_processor_information_ex(): Retrieves information about all the logical processors in the system.

Note:
    This is tailored for the needs of OpenCue, especially for hybrid CPUs
    TODO: Maybe we should contribute this back to psutils ?
"""
from ctypes import c_size_t, c_ulonglong, c_int, Structure, Union, WinDLL
from ctypes import POINTER, sizeof, WinError, byref, get_last_error
from ctypes import wintypes

# pylint: disable=line-too-long

class GROUP_AFFINITY(Structure):
    """ A structure that represents the affinity of a group of processors.
    Attributes:
        Mask (c_ulonglong): A bitmask that specifies the affinity of processors in the group.
        Group (wintypes.WORD): The processor group number.
    Reference:
        https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-group_affinity
    """
    _fields_ = [("Mask", c_ulonglong),
                ("Group", wintypes.WORD),
                ("Reserved", wintypes.WORD * 3)]


class PROCESSOR_RELATIONSHIP(Structure):
    """ Represents information about affinity within a processor group.
    Attributes:
        Flags (BYTE): Flags that provide additional information about the processor.
        EfficiencyClass (BYTE): The efficiency class of the processor.
        GroupCount (WORD): The number of processor groups.
        GroupMask (GROUP_AFFINITY * 1): The affinity mask for the processor group.
    Reference:
        - https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-processor_relationship
    """
    _fields_ = [("Flags", wintypes.BYTE),
                ("EfficiencyClass", wintypes.BYTE),
                ("Reserved", wintypes.BYTE * 20),
                ("GroupCount", wintypes.WORD),
                ("GroupMask", GROUP_AFFINITY * 1)]


class DUMMYUNIONNAME(Union):
    """ A union of possible information to get about a processor.
    Here we only get the processor relationship.
    Attributes:
        Processor (PROCESSOR_RELATIONSHIP): Represents the processor relationship.
    Reference:
        - https://learn.microsoft.com/fr-fr/windows/win32/api/winnt/ns-winnt-system_logical_processor_information_ex
    """
    _fields_ = [("Processor", PROCESSOR_RELATIONSHIP)]


class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX(Structure):
    """ Contains information about the relationships of logical processors and related hardware.
    Attributes:
        Relationship: The type of relationship between the logical processors.
        Size: The size of the structure.
        DUMMYUNIONNAME: see the class doc.
    Reference:
        - https://learn.microsoft.com/fr-fr/windows/win32/api/sysinfoapi/nf-sysinfoapi-getlogicalprocessorinformationex
    """
    _fields_ = [("Relationship", wintypes.DWORD),
                ("Size", wintypes.DWORD),
                ("DUMMYUNIONNAME", DUMMYUNIONNAME)]


def get_logical_processor_information_ex():
    """ Retrieves information about all the logical processors in the system.
    Usage:
        Used in rqmachine.Machine.__initStatsWindows()
    Returns:
        List of tuples for each thread (logical core):
            - group (int): Its processor group ID. (we can't detect different CPUS directly)
            - core_id (int): Its physical core ID.
            - thread_id (int): Its logical core ID.
    Raises:
        WinError: If there is an error in retrieving the processor information.
    References:
        https://learn.microsoft.com/fr-fr/windows/win32/api/sysinfoapi/nf-sysinfoapi-getlogicalprocessorinformationex
    """

    kernel32 = WinDLL('kernel32', use_last_error=True)
    GetLogicalProcessorInformationEx = kernel32.GetLogicalProcessorInformationEx
    GetLogicalProcessorInformationEx.argtypes = [wintypes.DWORD,
                                                 POINTER(SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX),
                                                 POINTER(wintypes.DWORD)]
    GetLogicalProcessorInformationEx.restype = wintypes.BOOL

    RelationProcessorCore = 0  # RelationProcessorCore constant
    ERROR_INSUFFICIENT_BUFFER = 122

    # Get required buffer size by calling the function with a null buffer
    buffer_size = wintypes.DWORD(0)
    if not GetLogicalProcessorInformationEx(RelationProcessorCore, None, byref(buffer_size)):
        if get_last_error() != ERROR_INSUFFICIENT_BUFFER:
            raise WinError(get_last_error())

    # Get information about all the logical processors
    buffer = (SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX * (
                buffer_size.value // sizeof(SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX)))()
    if not GetLogicalProcessorInformationEx(RelationProcessorCore, buffer, byref(buffer_size)):
        raise WinError(get_last_error())

    # Extract information
    cores_info = []
    core_id = 0
    _thread_id_inc = 0
    for item in buffer:
        if item.Relationship == RelationProcessorCore:
            mask = item.DUMMYUNIONNAME.Processor.GroupMask[0].Mask
            group = item.DUMMYUNIONNAME.Processor.GroupMask[0].Group
            logical_cores = bin(mask).count('1')
            thread_ids = [_thread_id_inc + i for i in range(logical_cores)]
            for thread_id in thread_ids:
                cores_info.append((group, core_id, thread_id))
            _thread_id_inc += logical_cores
            core_id += 1

    return cores_info
