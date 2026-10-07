#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import PurePosixPath

MAX_FILES = 50

# Target file extensions to include
TARGET_EXTENSIONS = (
    ".py",
    ".java",
    ".go",
    ".js",
    ".ts",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".rb",
    ".php",
    ".aspx",
    ".cshtml",
    ".vbhtml",
    ".vue",
    ".sql",
    ".pkh",
    ".pkb",
    ".tsql",
    ".abap",
    ".acds",
    ".abdl",
    ".cls",
    ".trigger",
    ".ipynb",
    ".pl",
    ".pm",
    ".sh",
    ".vb",
    ".vbp",
    ".frm",
    ".bas",
    ".cls-meta.xml",
    ".pls",
)


def is_target_file(file_path: str) -> bool:
    """Check if the file matches any of the target extensions (case-insensitive)."""
    return file_path.lower().endswith(TARGET_EXTENSIONS)


def get_tracked_files() -> list[str]:
    """Retrieve tracked files using git ls-files and filter by target extensions."""
    result = subprocess.run(
        ["git", "ls-files"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    all_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [f for f in all_files if is_target_file(f)]


def build_tree(files: list[str]):
    """
    Builds the directory tree structures:
    - total_counts: recursive count of matching files
    - direct_files: matching files located directly in each directory
    - dir_all_files: all matching files under each directory recursively
    - subdirs: direct child directories of each directory
    """
    total_counts = defaultdict(int)
    direct_files = defaultdict(list)
    dir_all_files = defaultdict(list)
    subdirs = defaultdict(set)

    for file_path in files:
        parts = PurePosixPath(file_path).parts
        direct_dir = str(PurePosixPath(*parts[:-1])) if len(parts) > 1 else "."
        direct_files[direct_dir].append(file_path)

        # Track matching files for all ancestor paths
        for i in range(len(parts)):
            ancestor = str(PurePosixPath(*parts[:i])) if i > 0 else "."
            total_counts[ancestor] += 1
            dir_all_files[ancestor].append(file_path)
            if i > 0:
                parent = str(PurePosixPath(*parts[: i - 1])) if i > 1 else "."
                subdirs[parent].add(ancestor)

    return total_counts, direct_files, dir_all_files, subdirs


def split_tree(curr_dir: str, total_counts, direct_files, dir_all_files, subdirs, max_files: int):
    """
    Recursively finds the highest-level directories with <= max_files matching files.
    Batches loose matching files if a directory exceeds max_files.
    """
    # If the directory has 0 matching files, omit it completely
    if total_counts.get(curr_dir, 0) == 0:
        return []

    # If the directory subtree has <= max_files matching files, return as a single chunk
    if total_counts[curr_dir] <= max_files:
        return [{
            "type": "directory",
            "path": curr_dir,
            "count": total_counts[curr_dir],
            "files": dir_all_files[curr_dir],
        }]

    chunks = []

    # Recurse into child subdirectories containing matching files
    for child in sorted(subdirs.get(curr_dir, [])):
        chunks.extend(split_tree(child, total_counts, direct_files, dir_all_files, subdirs, max_files))

    # Batch any loose matching files directly inside curr_dir
    loose = direct_files.get(curr_dir, [])
    for i in range(0, len(loose), max_files):
        batch = loose[i : i + max_files]
        chunks.append({
            "type": "files",
            "path": curr_dir,
            "count": len(batch),
            "files": batch,
        })

    return chunks


def main():
    max_files = int(os.environ.get("MAX_FILES", MAX_FILES))
    matching_files = get_tracked_files()

    if not matching_files:
        print(json.dumps([]))
        return

    total_counts, direct_files, dir_all_files, subdirs = build_tree(matching_files)
    chunks = split_tree(".", total_counts, direct_files, dir_all_files, subdirs, max_files)

    print(json.dumps(chunks))


if __name__ == "__main__":
    main()
