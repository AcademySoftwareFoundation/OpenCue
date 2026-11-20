#!/usr/bin/env python3
"""DO NOT MERGE. Compares two local images: config, and every file's path, type, mode, owner,
size and sha256. Usage: compare_images.py <old image> <new image>"""
import hashlib
import json
import subprocess
import sys
import tarfile

CONFIG_KEYS = ["User", "ExposedPorts", "Env", "Cmd", "Entrypoint", "Volumes", "WorkingDir",
               "Healthcheck", "Labels", "StopSignal", "Shell", "OnBuild"]


def config(image):
    out = json.loads(subprocess.check_output(["docker", "image", "inspect", image]))[0]
    cfg = {k: out["Config"].get(k) for k in CONFIG_KEYS}
    cfg["Architecture"] = out["Architecture"]
    cfg["Os"] = out["Os"]
    return cfg, out["Size"]


def files(image):
    cid = subprocess.check_output(["docker", "create", image]).decode().strip()
    try:
        proc = subprocess.Popen(["docker", "export", cid], stdout=subprocess.PIPE)
        manifest = {}
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tar:
            for m in tar:
                entry = {"type": m.type.decode() if isinstance(m.type, bytes) else m.type,
                         "mode": oct(m.mode), "uid": m.uid, "gid": m.gid}
                if m.isfile():
                    entry["size"] = m.size
                    entry["sha256"] = hashlib.sha256(tar.extractfile(m).read()).hexdigest()
                elif m.issym() or m.islnk():
                    entry["link"] = m.linkname
                manifest["/" + m.name.rstrip("/")] = entry
        proc.wait()
        return manifest
    finally:
        subprocess.run(["docker", "rm", cid], check=True, capture_output=True)


def main(old, new):
    old_cfg, old_size = config(old)
    new_cfg, new_size = config(new)
    print(f"## {new}\n")
    print(f"Image size: {old_size / 1e6:.1f} MB before, {new_size / 1e6:.1f} MB after\n")
    if old_cfg == new_cfg:
        print("Config (user, ports, env, cmd, entrypoint, volumes, workdir, healthcheck, labels): identical\n")
    else:
        print("Config differs:")
        for k in old_cfg:
            if old_cfg[k] != new_cfg[k]:
                print(f"- {k}: {old_cfg[k]!r} -> {new_cfg[k]!r}")
        print()
    old_files, new_files = files(old), files(new)
    same = [p for p in old_files if new_files.get(p) == old_files[p]]
    removed = sorted(set(old_files) - set(new_files))
    added = sorted(set(new_files) - set(old_files))
    changed = sorted(p for p in set(old_files) & set(new_files) if old_files[p] != new_files[p])
    print(f"Files: {len(old_files)} before, {len(new_files)} after; {len(same)} identical "
          f"(path, type, mode, owner, size, sha256), {len(changed)} changed, "
          f"{len(removed)} removed, {len(added)} added\n")

    def show(title, paths, detail):
        if not paths:
            return
        # Collapse to the top directories so a removed cache shows as one line.
        groups = {}
        for p in paths:
            parts = p.split("/")
            key = "/".join(parts[:5]) if len(parts) > 5 else p
            groups.setdefault(key, []).append(p)
        print(f"{title}:")
        for key, members in sorted(groups.items())[:60]:
            if len(members) == 1:
                print(f"- {key} {detail(key)}")
            else:
                print(f"- {key}/... ({len(members)} entries)")
        print()

    show("Removed", removed, lambda p: old_files[p])
    show("Added", added, lambda p: new_files[p])
    show("Changed", changed, lambda p: f"{old_files[p]} -> {new_files[p]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
