"""Create a public commit without changing the complete local branch or index."""

import argparse
import os
from pathlib import PurePosixPath
import subprocess
import sys
import tempfile


def git(*args, **kwargs):
    return subprocess.check_output(["git", *args], **kwargs)


def local_only(path):
    return (
        path.startswith(("docs/", "tests/"))
        or path == "CONTEXT.md"
        or PurePosixPath(path).name.lower() == "agents.md"
        or (path.startswith(".agents/skills/")
            and not path.startswith(".agents/skills/ladybug-tools-mcp-use/"))
    )


def export(parent, branch, message):
    git("check-ref-format", "--branch", branch)
    if f"branch refs/heads/{branch}".encode() in git("worktree", "list", "--porcelain").splitlines():
        raise ValueError("The public branch must not be checked out in a worktree.")
    git("diff", "--exit-code", "HEAD", "--")
    parent = git("rev-parse", f"{parent}^{{commit}}").decode().strip()
    with tempfile.TemporaryDirectory(prefix="lbt-public-index-") as temporary:
        environment = {**os.environ, "GIT_INDEX_FILE": os.path.join(temporary, "index")}
        git("read-tree", "HEAD", env=environment)
        names = git("ls-files", "-z", env=environment).split(b"\0")
        private = [name for name in names if name and local_only(name.decode("utf-8"))]
        if private:
            git("update-index", "--force-remove", "-z", "--stdin",
                input=b"\0".join(private) + b"\0", env=environment)
        tree = git("write-tree", env=environment).decode().strip()
    if tree == git("rev-parse", f"{parent}^{{tree}}").decode().strip():
        commit = parent
    else:
        commit = git("commit-tree", tree, "-p", parent, "-m", message).decode().strip()
    git("update-ref", f"refs/heads/{branch}", commit)
    return commit


def check_push():
    for line in sys.stdin:
        _, local_oid, _, _ = line.split()
        if not local_oid.strip("0"):
            continue
        commits = set(git("rev-list", local_oid, "--not", "--remotes").splitlines())
        commits.add(git("rev-parse", f"{local_oid}^{{commit}}").strip())
        for commit in commits:
            names = git("ls-tree", "-r", "--name-only", "-z", commit.decode()).split(b"\0")
            private = [name.decode("utf-8") for name in names if name and local_only(name.decode("utf-8"))]
            if private:
                raise SystemExit("Push blocked: local-only paths in " + commit.decode() + ": "
                                 + ", ".join(private[:5]) + ". Export a public branch first.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-push", action="store_true", help="Validate Git pre-push input.")
    parser.add_argument("--parent", default="origin/main")
    parser.add_argument("--branch", default="codex/publish")
    parser.add_argument("--message")
    args = parser.parse_args()
    if args.check_push:
        check_push()
    elif args.message:
        print(export(args.parent, args.branch, args.message))
    else:
        parser.error("--message is required when exporting")
