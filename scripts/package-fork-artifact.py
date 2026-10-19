"""Package a clean fork checkout's frontend and runtime overrides for VPS build."""

import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import tarfile


root = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip()
frontend_root = root / "build"
assert (frontend_root / "index.html").exists(), "Build the frontend before packaging"
commit = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=root, text=True
).strip()
manifest = json.loads((root / "fork/upgrade.json").read_text())
manifest["canvasCommit"] = commit
frontend = {
    str(p.relative_to(frontend_root)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(frontend_root.rglob("*"))
    if p.is_file()
}
manifest["frontendTreeSha256"] = hashlib.sha256(
    json.dumps(frontend, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
with tarfile.open(args.output, "w:gz") as archive:
    archive.add(root / "docker/Dockerfile.fork-artifact", arcname="Dockerfile")
    archive.add(frontend_root, arcname="frontend")
    archive.add(root / "fork", arcname="fork")
    data = json.dumps(manifest, indent=2).encode()
    info = tarfile.TarInfo("artifact.json")
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))
print(
    json.dumps(
        {
            "artifact": str(args.output),
            "canvasCommit": commit,
            "frontendTreeSha256": manifest["frontendTreeSha256"],
            "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        }
    )
)
