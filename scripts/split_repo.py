#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import PurePosixPath

MAX_FILES = 50

def get_tracked_files() -> list[str]:
    """Retrieve all tracked files using git ls-files."""
    result = subprocess.run(
        ["git", "ls-files"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]

def build_tree(files: list[str]):
    """
    Builds a tree structure:
    - total_counts: recursive file count for each directory
    - direct_files: files located directly in each directory
    - subdirs: direct child directories of each directory
    """
    total_counts = defaultdict(int)
    direct_files = defaultdict(list)
    subdirs = defaultdict(set)

    for file_path in files:
        parts = PurePosixPath(file_path).parts
        direct_files_dir = str(PurePosixPath(*parts[:-1])) if len(parts) > 1 else "."
        direct_files[direct_files_dir].append(file_path)

        # Increment recursive counts for all ancestor directories
        for i in range(len(parts)):
            ancestor = str(PurePosixPath(*parts[:i])) if i > 0 else "."
            total_counts[ancestor] += 1
            if i > 0:
                parent = str(PurePosixPath(*parts[: i - 1])) if i > 1 else "."
                subdirs[parent].add(ancestor)

    return total_counts, direct_files, subdirs

def split_tree(curr_dir: str, total_counts, direct_files, subdirs, max_files: int):
    """
    Recursively finds the highest-level directories with <= max_files.
    Batches loose files if a directory exceeds max_files.
    """
    chunks = []

    # If the entire directory subtree fits within the limit, return as a whole directory chunk
    if total_counts[curr_dir] <= max_files:
        return [{
            "type": "directory",
            "path": curr_dir,
            "count": total_counts[curr_dir],
        }]

    # Otherwise, explore child subdirectories
    for child in sorted(subdirs.get(curr_dir, [])):
        chunks.extend(split_tree(child, total_counts, direct_files, subdirs, max_files))

    # Any files sitting directly in curr_dir need to be grouped
    loose = direct_files.get(curr_dir, [])
    for i in range(0, len(loose), max_files):
        batch = loose[i : i + max_files]
        chunks.append({
            "type": "files",
            "path": curr_dir,
            "files": batch,
            "count": len(batch),
        })

    return chunks

def main():
    max_files = int(os.environ.get("MAX_FILES", MAX_FILES))
    files = get_tracked_files()

    if not files:
        print(json.dumps([]))
        return

    total_counts, direct_files, subdirs = build_tree(files)
    chunks = split_tree(".", total_counts, direct_files, subdirs, max_files)

    # Output formatted JSON
    print(json.dumps(chunks))

if __name__ == "__main__":
    main()
