"""Explicit local operator bootstrap; never called by HTTP."""
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from jackline.storage import private_dir
from .service import ROOT, BoundaryError

DEFAULT_HOME = Path.home() / '.local/share/dealforce'
DEFAULT_KEY = Path.home() / '.config/dealforce-reviewer/reviewer.key'


def initialize(home=DEFAULT_HOME, key_path=DEFAULT_KEY):
    home, key_path = Path(home).expanduser().resolve(), Path(key_path).expanduser().resolve()
    if home == ROOT or ROOT in home.parents or ROOT in key_path.parents or home in key_path.parents or key_path == home:
        raise BoundaryError('Store runtime and reviewer key separately, outside the repository')
    if (home / 'policy.toml').exists() or key_path.exists():
        raise BoundaryError('Initialization refuses to overwrite an existing policy or reviewer key')
    private_dir(home)
    private_dir(key_path.parent)
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(private.hex() + '\n')
        f.flush()
        os.fsync(f.fileno())
    policy = f'''[jackline]
name = "dealforce-release"
default = "deny"

[budget]
max_tool_calls = 4
max_wall_time = "15m"

[approvals]
timeout = "5m"
[approvals.public_keys]
reviewer = "{public}"

[[rule]]
id = "release-needs-review"
tools = ["brief.release"]
effect = "approve"
approvers = ["reviewer"]
'''
    fd = os.open(home / 'policy.toml', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(policy)
    return home, key_path
