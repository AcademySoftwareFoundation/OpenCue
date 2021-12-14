/*
 *  Copyright Contributors to the OpenCue Project
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <Windows.h>
// TlHelp32.h should be included after Windows.h
#include <TlHelp32.h>
#include <psapi.h>

#include <cstdint>
#include <map>
#include <utility>
#include <vector>

namespace {

// Process stat history
struct Snapshot {
  uint64_t creationTimeInFiletime;
  uint64_t totalTimeInFiletime;
  uint64_t wallTimeInFiletime;
  double pidPcpu;
};
std::map<DWORD, Snapshot> history;

// FILETIME -> uint64_t, in 100-nanosecond unit
uint64_t convertFiletime(const FILETIME& ft) {
  union TimeUnion {
    FILETIME ft;
    ULARGE_INTEGER ul;
  };
  TimeUnion tu;
  tu.ft = ft;
  return tu.ul.QuadPart;
}

void traverse(
    const std::map<DWORD, std::vector<DWORD>>& parentChildrenMap,
    DWORD pid,
    uint64_t& rss,
    double& pcpu) {
  HANDLE hProcess =
      OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, false, pid);
  if (hProcess != nullptr) {
    // RSS
    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(hProcess, &pmc, sizeof(pmc))) {
      rss += pmc.WorkingSetSize;
    }

    // %CPU
    FILETIME creationTime;
    FILETIME exitTime;
    FILETIME kernelTime;
    FILETIME userTime;
    if (GetProcessTimes(
            hProcess, &creationTime, &exitTime, &kernelTime, &userTime)) {
      // Current time in FILETIME
      FILETIME now;
      GetSystemTimeAsFileTime(&now);

      // Process start time
      uint64_t creationTimeInFiletime = convertFiletime(creationTime);

      // Total time of kernel and user mode on this process
      uint64_t totalTimeInFiletime =
          convertFiletime(kernelTime) + convertFiletime(userTime);

      // Walltime of this process
      uint64_t wallTimeInFiletime =
          convertFiletime(now) - creationTimeInFiletime;

      if (wallTimeInFiletime > 0) {
        auto it = history.find(pid);
        if (it != history.end() &&
            it->second.creationTimeInFiletime == creationTimeInFiletime) {
          // Percent cpu using decaying average, 50% from 10 seconds ago,
          // 50% from last 10 seconds:
          const auto& last = it->second;
          double pidPcpu = static_cast<double>(
                               totalTimeInFiletime - last.totalTimeInFiletime) /
              static_cast<double>(wallTimeInFiletime - last.wallTimeInFiletime);
          pcpu += (last.pidPcpu + pidPcpu) / 2.0; // %cpu
          history[pid] = Snapshot{
              creationTimeInFiletime,
              totalTimeInFiletime,
              wallTimeInFiletime,
              pidPcpu};
        } else {
          double pidPcpu = static_cast<double>(totalTimeInFiletime) /
              static_cast<double>(wallTimeInFiletime);
          pcpu += pidPcpu;

          history[pid] = Snapshot{
              creationTimeInFiletime,
              totalTimeInFiletime,
              wallTimeInFiletime,
              pidPcpu};
        }
      }
    }
  }

  const auto it = parentChildrenMap.find(pid);
  if (it != parentChildrenMap.end()) {
    for (const auto childPid : it->second) {
      traverse(parentChildrenMap, childPid, rss, pcpu);
    }
  }
}

PyObject* winpsUpdate(PyObject* self, PyObject* args) {
  /*
   * :param list pids: a list of pid(int) to look into
   * :return: RSS and %CPU dict, or None if invalid inputs or error occurred
   * :rtype: dict (key=pid, value={rss:uint64_t, pcpu:double})
   */
  PyObject* list;
  if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &list)) {
    return nullptr;
  }

  // Take a snapshot of all processes and create parent-children process map
  std::map<DWORD, std::vector<DWORD>> parentChildrenMap;
  HANDLE snapshotHandle = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
  PROCESSENTRY32 processEntry = {};
  processEntry.dwSize = sizeof(PROCESSENTRY32);
  if (Process32First(snapshotHandle, &processEntry)) {
    do {
      if (processEntry.th32ProcessID != 0) {
        parentChildrenMap[processEntry.th32ParentProcessID].push_back(
            processEntry.th32ProcessID);
      }
    } while (Process32Next(snapshotHandle, &processEntry));
  }
  CloseHandle(snapshotHandle);

  // output = {}
  PyObject* output = PyDict_New();
  if (output == nullptr) {
    return nullptr;
  }

  // Iterate the pids list
  Py_ssize_t listSize = PyList_Size(list);
  for (Py_ssize_t i = 0; i < listSize; i++) {
    PyObject* pidObject = PyList_GetItem(list, i);
    if (pidObject == nullptr) {
      return nullptr;
    }
    DWORD pid = PyLong_AsUnsignedLong(pidObject);
    if (PyErr_Occurred()) {
      return nullptr;
    }

    // Traverse process tree to add up RSS and %CPU from the pid
    uint64_t rss = 0;
    double pcpu = 0;
    traverse(parentChildrenMap, pid, rss, pcpu);

    // stat = {}
    PyObject* stat = PyDict_New();
    if (stat == nullptr) {
      return nullptr;
    }

    // stat["rss"] = rss
    PyObject* rssObject = PyLong_FromUnsignedLongLong(rss);
    if (rssObject == nullptr) {
      return nullptr;
    }
    if (PyDict_SetItemString(stat, "rss", rssObject) != 0) {
      return nullptr;
    }

    // stat["pcpu"] = pcpu
    PyObject* pcpuObject = PyFloat_FromDouble(pcpu);
    if (pcpuObject == nullptr) {
      return nullptr;
    }
    if (PyDict_SetItemString(stat, "pcpu", pcpuObject) != 0) {
      return nullptr;
    }

    // output[pid] = stat
    if (PyDict_SetItem(output, pidObject, stat) != 0) {
      return nullptr;
    }
  }

  return output;
}

PyMethodDef winpsMethods[] = {
    {"update",
     winpsUpdate,
     METH_VARARGS,
     "Updates internal state and returns rss and pcpu"},
    {NULL, NULL, 0, NULL}};

PyModuleDef winpsModule = {
    PyModuleDef_HEAD_INIT,
    "winps",
    nullptr,
    -1,
    winpsMethods,
};

} // namespace

PyMODINIT_FUNC PyInit_winps() {
  return PyModule_Create(&winpsModule);
}
