#!/usr/bin/env python3
"""
Read and display all contents of a dependencies.db SQLite file.

Usage:
    python scripts/read_dependencies_db.py <path_to_dependencies.db>

Example:
    python scripts/read_dependencies_db.py output/my_project/dependencies.db
"""
import sqlite3
import sys
import os
from collections import defaultdict


def read_db(db_path: str):
    if not os.path.exists(db_path):
        print(f"ERROR: File not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # --- Summary ---
    cursor.execute("SELECT COUNT(*) FROM dependencies")
    total_edges = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT endpoint_id) FROM dependencies")
    total_endpoints = cursor.fetchone()[0]

    print("=" * 70)
    print(f"  Database : {db_path}")
    print(f"  Endpoints: {total_endpoints}")
    print(f"  Edges    : {total_edges}")
    print("=" * 70)

    # --- Group by endpoint ---
    cursor.execute(
        "SELECT endpoint_id, caller, target FROM dependencies ORDER BY endpoint_id, caller"
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("\n  (empty — no dependencies recorded)\n")
        return

    # Group: endpoint -> caller -> [targets]
    endpoints = defaultdict(lambda: defaultdict(list))
    for endpoint_id, caller, target in rows:
        endpoints[endpoint_id][caller].append(target)

    for endpoint_id, callers in endpoints.items():
        print(f"\n┌─ Endpoint: {endpoint_id}")
        print(f"│  Callers: {len(callers)}   Edges: {sum(len(t) for t in callers.values())}")
        print("│")

        for caller, targets in callers.items():
            print(f"│  {caller}")
            for i, target in enumerate(targets):
                connector = "└──▶" if i == len(targets) - 1 else "├──▶"
                print(f"│    {connector} {target}")

        print("└" + "─" * 69)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip())
        sys.exit(1)

    read_db(sys.argv[1])
