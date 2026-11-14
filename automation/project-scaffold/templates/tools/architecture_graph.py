"""Source code dependency topology and architecture graph analyzer.

Extracts real code imports (Python AST, TypeScript/JavaScript imports, C# namespaces),
detects circular dependencies and orphan modules, and generates Mermaid/JSON/HTML diagrams.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_SOURCE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".cs",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".github",
    ".agent",
    ".vscode",
    ".idea",
    "node_modules",
    "bin",
    "obj",
    "__pycache__",
    "dist",
    "build",
    "out",
    "target",
    ".pytest_cache",
    ".ruff_cache",
    "tests",
    "tools",
    "scripts",
    "docs",
}


def find_source_files(
    repo_root: Path,
    target_dir: Path | None = None,
    extensions: set[str] | None = None,
    exclude_dirs: set[str] | None = None,
) -> list[Path]:
    """Find all relevant source files in target directory."""
    resolved_root = repo_root.resolve()
    base_dir = (target_dir or resolved_root).resolve()
    exts = extensions or DEFAULT_SOURCE_EXTENSIONS
    excludes = exclude_dirs or DEFAULT_EXCLUDE_DIRS

    found = []
    if not base_dir.is_dir():
        return found

    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [d for d in dirnames if d not in excludes and not d.startswith(".")]
        current = Path(dirpath)
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in exts:
                found.append(current / fname)

    return sorted(found)


def extract_python_imports(file_path: Path, repo_root: Path) -> list[str]:
    """Extract imported module names and relative module paths from Python AST."""
    imports = []
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except Exception:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod_prefix = ""
            if node.level > 0:
                # Relative import
                mod_prefix = "." * node.level
            if node.module:
                imports.append(f"{mod_prefix}{node.module}")
            else:
                for alias in node.names:
                    imports.append(f"{mod_prefix}{alias.name}")
    return imports


def extract_js_ts_imports(file_path: Path) -> list[str]:
    """Extract imported paths from TypeScript and JavaScript code."""
    imports = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return imports

    # Match import ... from 'path' and require('path')
    import_pat = re.compile(r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\))""")
    for m in import_pat.finditer(content):
        imported = m.group(1) or m.group(2)
        if imported:
            imports.append(imported)
    return imports


def extract_csharp_usings(file_path: Path) -> list[str]:
    """Extract using namespaces from C# source code."""
    usings = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return usings

    using_pat = re.compile(r"""^\s*using\s+(?:static\s+)?([A-Za-z0-9_.]+)\s*;""", re.MULTILINE)
    for m in using_pat.finditer(content):
        usings.append(m.group(1))
    return usings


def resolve_python_dependency(
    source_file: Path,
    import_stmt: str,
    all_files: dict[str, Path],
    repo_root: Path,
) -> str | None:
    """Resolve Python import statement to an internal relative file path if matches."""
    # Check if relative import
    if import_stmt.startswith("."):
        dots = len(import_stmt) - len(import_stmt.lstrip("."))
        target_name = import_stmt.lstrip(".")
        current_dir = source_file.parent
        for _ in range(dots - 1):
            current_dir = current_dir.parent

        rel_dir = target_name.replace(".", "/")
        candidates = [
            current_dir / f"{rel_dir}.py",
            current_dir / rel_dir / "__init__.py",
        ]
        for c in candidates:
            try:
                rel = c.resolve().relative_to(repo_root.resolve()).as_posix()
                if rel in all_files:
                    return rel
            except Exception:
                pass
        return None

    # Absolute / module import
    parts = import_stmt.split(".")
    for i in range(len(parts), 0, -1):
        sub_path = "/".join(parts[:i])
        for rel_posix, abs_path in all_files.items():
            if rel_posix.endswith(f"/{sub_path}.py") or rel_posix == f"{sub_path}.py":
                return rel_posix
            if rel_posix.endswith(f"/{sub_path}/__init__.py") or rel_posix == f"{sub_path}/__init__.py":
                return rel_posix

    return None


def resolve_js_dependency(
    source_file: Path,
    import_stmt: str,
    all_files: dict[str, Path],
    repo_root: Path,
) -> str | None:
    """Resolve JS/TS import path to internal file."""
    if not (import_stmt.startswith("./") or import_stmt.startswith("../")):
        return None

    target = (source_file.parent / import_stmt).resolve()
    candidates = [
        target,
        target.with_suffix(".ts"),
        target.with_suffix(".tsx"),
        target.with_suffix(".js"),
        target.with_suffix(".jsx"),
        target / "index.ts",
        target / "index.js",
    ]

    for c in candidates:
        try:
            rel = c.relative_to(repo_root.resolve()).as_posix()
            if rel in all_files:
                return rel
        except Exception:
            pass
    return None


def build_dependency_graph(
    repo_root: Path,
    target_dir: Path | None = None,
) -> dict[str, set[str]]:
    """Build directed adjacency list {source_file: {target_file, ...}}."""
    resolved_root = repo_root.resolve()
    files = find_source_files(resolved_root, target_dir)
    file_map = {f.relative_to(resolved_root).as_posix(): f for f in files}

    graph: dict[str, set[str]] = {rel: set() for rel in file_map}

    for rel_path, abs_path in file_map.items():
        ext = abs_path.suffix.lower()
        if ext == ".py":
            raw_imports = extract_python_imports(abs_path, resolved_root)
            for raw in raw_imports:
                target = resolve_python_dependency(abs_path, raw, file_map, resolved_root)
                if target and target != rel_path:
                    graph[rel_path].add(target)
        elif ext in {".ts", ".tsx", ".js", ".jsx"}:
            raw_imports = extract_js_ts_imports(abs_path)
            for raw in raw_imports:
                target = resolve_js_dependency(abs_path, raw, file_map, resolved_root)
                if target and target != rel_path:
                    graph[rel_path].add(target)

    return graph


def detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Detect circular dependency cycles in graph using DFS."""
    cycles = []
    visited: set[str] = set()
    rec_stack: list[str] = []

    def dfs(node: str):
        visited.add(node)
        rec_stack.append(node)

        for neighbor in sorted(graph.get(node, [])):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                cycle_start = rec_stack.index(neighbor)
                cycle = rec_stack[cycle_start:] + [neighbor]
                # Avoid duplicate representations of same cycle
                canonical = min(cycle[:-1])
                c_idx = cycle[:-1].index(canonical)
                rotated = cycle[:-1][c_idx:] + cycle[:-1][:c_idx] + [canonical]
                if rotated not in cycles:
                    cycles.append(rotated)

        rec_stack.pop()

    for node in sorted(graph.keys()):
        if node not in visited:
            dfs(node)

    return cycles


def detect_orphans(graph: dict[str, set[str]]) -> list[str]:
    """Detect orphan modules with 0 callers and 0 internal outgoing calls."""
    incoming_counts = defaultdict(int)
    for src, targets in graph.items():
        for tgt in targets:
            incoming_counts[tgt] += 1

    orphans = [
        node for node in graph
        if len(graph[node]) == 0 and incoming_counts[node] == 0
    ]
    return sorted(orphans)


def generate_mermaid_diagram(
    graph: dict[str, set[str]],
    cycles: list[list[str]] | None = None,
    group_by_dir: bool = True,
) -> str:
    """Generate Mermaid flowchart TD representation."""
    lines = ["```mermaid", "flowchart TD"]

    # Sanitize node names for Mermaid IDs
    def node_id(path: str) -> str:
        return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", path)

    cycle_edges = set()
    if cycles:
        for c in cycles:
            for i in range(len(c) - 1):
                cycle_edges.add((c[i], c[i + 1]))

    if group_by_dir:
        groups: dict[str, list[str]] = defaultdict(list)
        for node in sorted(graph.keys()):
            parts = node.split("/")
            group_name = parts[0] if len(parts) > 1 else "root"
            groups[group_name].append(node)

        for group_name, members in sorted(groups.items()):
            sub_id = "sub_" + re.sub(r"[^A-Za-z0-9_]", "_", group_name)
            lines.append(f'    subgraph {sub_id}["{group_name}/"]')
            for m in members:
                base = m.split("/")[-1]
                lines.append(f'        {node_id(m)}["{base}"]')
            lines.append("    end")
    else:
        for node in sorted(graph.keys()):
            base = node.split("/")[-1]
            lines.append(f'    {node_id(node)}["{base}"]')

    lines.append("")
    # Add edges
    for src in sorted(graph.keys()):
        for tgt in sorted(graph[src]):
            src_id = node_id(src)
            tgt_id = node_id(tgt)
            if (src, tgt) in cycle_edges:
                lines.append(f"    {src_id} -.->|cycle!| {tgt_id}")
            else:
                lines.append(f"    {src_id} --> {tgt_id}")

    lines.append("```")
    return "\n".join(lines)


def generate_html_diagram(graph: dict[str, set[str]], cycles: list[list[str]]) -> str:
    """Generate interactive HTML viewer for the architecture graph."""
    mermaid_code = generate_mermaid_diagram(graph, cycles).replace("```mermaid\n", "").replace("\n```", "")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Architecture Dependency Graph</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      margin: 20px;
      background: #f8fafc;
      color: #0f172a;
    }}
    .header {{
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid #e2e8f0;
    }}
    .card {{
      background: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      margin-right: 8px;
    }}
    .badge-ok {{ background: #dcfce7; color: #15803d; }}
    .badge-warn {{ background: #fee2e2; color: #b91c1c; }}
  </style>
</head>
<body>
  <div class="header">
    <h2>📐 Architecture Dependency Topology</h2>
    <div>
      <span class="badge badge-ok">{len(graph)} Modules</span>
      <span class="badge {'badge-warn' if cycles else 'badge-ok'}">{len(cycles)} Circular Cycles</span>
    </div>
  </div>
  <div class="card">
    <pre class="mermaid">
{mermaid_code}
    </pre>
  </div>
  <script>
    mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
  </script>
</body>
</html>"""
    return html


def run_architecture_analysis(repo_root: Path, target_dir: Path | None = None) -> dict:
    """Run full graph analysis and return structured report."""
    resolved_root = repo_root.resolve()
    graph = build_dependency_graph(resolved_root, target_dir)
    cycles = detect_cycles(graph)
    orphans = detect_orphans(graph)

    serializable_graph = {src: sorted(list(tgts)) for src, tgts in graph.items()}
    edge_count = sum(len(tgts) for tgts in graph.values())

    return {
        "total_modules": len(graph),
        "total_dependencies": edge_count,
        "cycles": cycles,
        "orphans": orphans,
        "graph": serializable_graph,
        "clean": len(cycles) == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Source code dependency topology and architecture graph analyzer."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root directory (default: current working directory).",
    )
    parser.add_argument(
        "--dir",
        help="Subdirectory to analyze (e.g. src). If omitted, analyzes entire repository source.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "mermaid", "json", "html"],
        default="text",
        help="Output visualization format (default: text).",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path to write diagram or JSON.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Quality gate: exit 1 if circular dependencies are detected.",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    target_dir = (repo_root / args.dir).resolve() if args.dir else None

    report = run_architecture_analysis(repo_root, target_dir)
    graph = {k: set(v) for k, v in report["graph"].items()}
    cycles = report["cycles"]

    if args.format == "json":
        output = json.dumps(report, indent=2, ensure_ascii=False)
    elif args.format == "mermaid":
        output = generate_mermaid_diagram(graph, cycles)
    elif args.format == "html":
        output = generate_html_diagram(graph, cycles)
    else:
        # text summary
        lines = [
            f"[architecture_graph] Analyzed {report['total_modules']} modules with {report['total_dependencies']} dependencies.",
        ]
        if cycles:
            lines.append(f"\n⚠️  Detected {len(cycles)} circular dependency loop(s):")
            for c in cycles:
                lines.append(f"   ❌ {' -> '.join(c)}")
        else:
            lines.append("✅ No circular dependencies detected.")

        if report["orphans"]:
            lines.append(f"\nℹ️  Detected {len(report['orphans'])} orphan module(s):")
            for o in report["orphans"][:10]:
                lines.append(f"   - {o}")
            if len(report["orphans"]) > 10:
                lines.append(f"   ... ({len(report['orphans']) - 10} more)")
        output = "\n".join(lines)

    if args.output:
        out_p = Path(args.output)
        if not out_p.is_absolute():
            out_p = repo_root / out_p
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output, encoding="utf-8")
        print(f"[architecture_graph] Architecture output written to: {out_p}")
    else:
        print(output)

    if args.check and not report["clean"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
