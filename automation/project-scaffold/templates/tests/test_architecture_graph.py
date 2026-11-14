import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from architecture_graph import (
    extract_python_imports,
    extract_js_ts_imports,
    build_dependency_graph,
    detect_cycles,
    detect_orphans,
    generate_mermaid_diagram,
    generate_html_diagram,
    run_architecture_analysis,
    main,
)


class ArchitectureGraphExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_python_imports(self):
        py_file = self.root / "example.py"
        py_file.write_text(
            "import os\nfrom pathlib import Path\nfrom .sub import helper\n",
            encoding="utf-8",
        )
        imports = extract_python_imports(py_file, self.root)
        self.assertIn("os", imports)
        self.assertIn("pathlib", imports)
        self.assertIn(".sub", imports)

    def test_extract_js_ts_imports(self):
        ts_file = self.root / "app.ts"
        ts_file.write_text(
            "import { foo } from './utils/foo';\nconst bar = require('../core/bar');\n",
            encoding="utf-8",
        )
        imports = extract_js_ts_imports(ts_file)
        self.assertIn("./utils/foo", imports)
        self.assertIn("../core/bar", imports)


class ArchitectureGraphTopologyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.src = self.root / "src"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_dependency_graph_and_cycles(self):
        # Create circular dependency: a imports b, b imports a
        (self.src / "mod_a.py").write_text("from .mod_b import b\n", encoding="utf-8")
        (self.src / "mod_b.py").write_text("from .mod_a import a\n", encoding="utf-8")
        (self.src / "mod_c.py").write_text("from .mod_a import a\n", encoding="utf-8")

        graph = build_dependency_graph(self.root, self.src)
        self.assertIn("src/mod_b.py", graph["src/mod_a.py"])
        self.assertIn("src/mod_a.py", graph["src/mod_b.py"])

        cycles = detect_cycles(graph)
        self.assertEqual(1, len(cycles))
        self.assertTrue("src/mod_a.py" in cycles[0] and "src/mod_b.py" in cycles[0])

    def test_detect_orphans(self):
        (self.src / "connected_a.py").write_text("from .connected_b import b\n", encoding="utf-8")
        (self.src / "connected_b.py").write_text("x = 1\n", encoding="utf-8")
        (self.src / "orphan_island.py").write_text("val = 42\n", encoding="utf-8")

        graph = build_dependency_graph(self.root, self.src)
        orphans = detect_orphans(graph)
        self.assertIn("src/orphan_island.py", orphans)
        self.assertNotIn("src/connected_a.py", orphans)
        self.assertNotIn("src/connected_b.py", orphans)


class ArchitectureGraphVisualizationAndCLITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        self.src = self.root / "src"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_mermaid_diagram(self):
        graph = {
            "src/controller.py": {"src/service.py"},
            "src/service.py": {"src/db.py"},
            "src/db.py": set(),
        }
        mermaid = generate_mermaid_diagram(graph, cycles=[])
        self.assertTrue(mermaid.startswith("```mermaid\nflowchart TD"))
        self.assertIn("controller.py", mermaid)
        self.assertIn("service.py", mermaid)
        self.assertIn("-->", mermaid)

    def test_generate_html_diagram(self):
        graph = {"src/app.py": set()}
        html = generate_html_diagram(graph, cycles=[])
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("mermaid.initialize", html)

    def test_cli_check_fails_on_cycle(self):
        (self.src / "mod_x.py").write_text("from .mod_y import y\n", encoding="utf-8")
        (self.src / "mod_y.py").write_text("from .mod_x import x\n", encoding="utf-8")

        with patch.object(sys, "argv", ["architecture_graph.py", "--root", str(self.root), "--check"]):
            rc = main()
            self.assertEqual(1, rc)

    def test_cli_check_passes_when_clean(self):
        (self.src / "mod_x.py").write_text("from .mod_y import y\n", encoding="utf-8")
        (self.src / "mod_y.py").write_text("y = 1\n", encoding="utf-8")

        with patch.object(sys, "argv", ["architecture_graph.py", "--root", str(self.root), "--check"]):
            rc = main()
            self.assertEqual(0, rc)

    def test_cli_output_file(self):
        (self.src / "main.py").write_text("x = 1\n", encoding="utf-8")
        out_file = self.root / "arch.json"
        with patch.object(sys, "argv", ["architecture_graph.py", "--root", str(self.root), "--format", "json", "-o", str(out_file)]):
            rc = main()
            self.assertEqual(0, rc)
            self.assertTrue(out_file.is_file())
            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertIn("total_modules", data)


if __name__ == "__main__":
    unittest.main()
