"""
Test module for verifying consistent resource file access patterns.

This module ensures all resource files are accessed using absolute paths
and follow consistent patterns to prevent production deployment issues.
"""

import unittest
from pathlib import Path
from typing import Any

from app.constants import (
    BRIDGE_DATA_PATH,
    CHANGELOG_PATH,
    CONCRETEQUALITY_CSV_PATH,
    CSS_PATH,
    OUTPUT_REPORT_PATH,
    PROJECT_PATH,
    README_PATH,
    REINFORCEMENT_PATH,
    SCIA_TEMPLATE_PATH,
)
from src.common.materials import (
    BENDING_RADIUS_PATH,
    CONCRETE_PATH,
    MATERIAL_DENSITY_PATH,
    MATERIALS_DIR,
    PRESTRESS_PATH,
    REINFORCEMENT_PATH as SRC_REINFORCEMENT_PATH,
)


class TestResourceFileAccessPatterns(unittest.TestCase):
    """Test cases for consistent resource file access patterns."""

    def test_all_constants_use_absolute_paths(self) -> None:
        """Test that all path constants in app.constants use absolute paths."""
        # Test app.constants paths
        constants_paths = [
            ("README_PATH", README_PATH),
            ("CHANGELOG_PATH", CHANGELOG_PATH),
            ("CSS_PATH", CSS_PATH),
            ("OUTPUT_REPORT_PATH", OUTPUT_REPORT_PATH),
            ("SCIA_TEMPLATE_PATH", SCIA_TEMPLATE_PATH),
            ("REINFORCEMENT_PATH", REINFORCEMENT_PATH),
            ("BRIDGE_DATA_PATH", BRIDGE_DATA_PATH),
            ("CONCRETEQUALITY_CSV_PATH", CONCRETEQUALITY_CSV_PATH),
        ]

        for name, path in constants_paths:
            with self.subTest(constant=name):
                self.assertIsInstance(path, Path, f"{name} should be a Path object")
                self.assertTrue(path.is_absolute(), f"{name} should be an absolute path, got: {path}")

    def test_all_material_paths_use_absolute_paths(self) -> None:
        """Test that all material paths in src.common.materials use absolute paths."""
        material_paths = [
            ("MATERIALS_DIR", MATERIALS_DIR),
            ("CONCRETE_PATH", CONCRETE_PATH),
            ("REINFORCEMENT_PATH", SRC_REINFORCEMENT_PATH),
            ("PRESTRESS_PATH", PRESTRESS_PATH),
            ("BENDING_RADIUS_PATH", BENDING_RADIUS_PATH),
            ("MATERIAL_DENSITY_PATH", MATERIAL_DENSITY_PATH),
        ]

        for name, path in material_paths:
            with self.subTest(material_path=name):
                self.assertIsInstance(path, Path, f"{name} should be a Path object")
                self.assertTrue(path.is_absolute(), f"{name} should be an absolute path, got: {path}")

    def test_critical_resource_files_exist(self) -> None:
        """Test that critical resource files actually exist in the repository."""
        critical_files = [
            ("SCIA Template", SCIA_TEMPLATE_PATH),
            ("Word Report Template", OUTPUT_REPORT_PATH),
            ("Bridge Data", BRIDGE_DATA_PATH),
            ("Concrete Quality CSV", CONCRETEQUALITY_CSV_PATH),
            ("Reinforcement CSV", REINFORCEMENT_PATH),
        ]

        for name, path in critical_files:
            with self.subTest(file=name):
                self.assertTrue(
                    path.exists(),
                    f"{name} file should exist at {path}. "
                    f"This file is critical for production functionality."
                )

    def test_material_csv_files_exist(self) -> None:
        """Test that all material CSV files exist."""
        material_files = [
            ("Concrete Quality", CONCRETE_PATH),
            ("Reinforcement Steel", SRC_REINFORCEMENT_PATH),
            ("Prestressing Steel", PRESTRESS_PATH),
            ("Bending Radius", BENDING_RADIUS_PATH),
            ("Material Density", MATERIAL_DENSITY_PATH),
        ]

        for name, path in material_files:
            with self.subTest(material_file=name):
                self.assertTrue(
                    path.exists(),
                    f"{name} CSV file should exist at {path}. "
                    f"This file is required for material calculations."
                )

    def test_path_construction_consistency(self) -> None:
        """Test that all paths are constructed consistently from PROJECT_PATH."""
        # All app.constants paths should start with PROJECT_PATH
        app_paths = [
            README_PATH,
            CHANGELOG_PATH,
            CSS_PATH,
            OUTPUT_REPORT_PATH,
            SCIA_TEMPLATE_PATH,
            REINFORCEMENT_PATH,
            BRIDGE_DATA_PATH,
            CONCRETEQUALITY_CSV_PATH,
        ]

        for path in app_paths:
            with self.subTest(path=str(path)):
                try:
                    # Check if path is relative to PROJECT_PATH
                    path.relative_to(PROJECT_PATH)
                except ValueError:
                    self.fail(f"Path {path} is not relative to PROJECT_PATH {PROJECT_PATH}")

    def test_no_relative_path_usage_in_controllers(self) -> None:
        """Test that controllers don't use relative paths for resource access."""
        # This is a static analysis test - we'll check the controller files
        from app.bridge.controller import BridgeController
        
        # Get the template path using the method
        controller = BridgeController()
        
        # Mock the path exists check since we're testing the path construction
        import unittest.mock
        with unittest.mock.patch.object(Path, 'exists', return_value=True):
            template_path = controller._get_scia_template_path()
        
        # Verify it's absolute
        self.assertTrue(
            template_path.is_absolute(),
            f"Controller should return absolute path, got: {template_path}"
        )
        
        # Verify it matches our constant
        self.assertEqual(
            template_path,
            SCIA_TEMPLATE_PATH,
            "Controller should use the SCIA_TEMPLATE_PATH constant"
        )

    def test_resource_directory_structure(self) -> None:
        """Test that the expected resource directory structure exists."""
        expected_dirs = [
            PROJECT_PATH / "resources",
            PROJECT_PATH / "resources" / "data",
            PROJECT_PATH / "resources" / "data" / "materials",
            PROJECT_PATH / "resources" / "data" / "bridges",
            PROJECT_PATH / "resources" / "templates",
            PROJECT_PATH / "resources" / "styles",
            PROJECT_PATH / "resources" / "gis",
        ]

        for directory in expected_dirs:
            with self.subTest(directory=str(directory)):
                self.assertTrue(
                    directory.exists() and directory.is_dir(),
                    f"Expected resource directory should exist: {directory}"
                )

    def test_path_separators_are_cross_platform(self) -> None:
        """Test that all paths use pathlib for cross-platform compatibility."""
        # All our constants should be Path objects, not strings with hardcoded separators
        all_paths = [
            README_PATH, CHANGELOG_PATH, CSS_PATH, OUTPUT_REPORT_PATH,
            SCIA_TEMPLATE_PATH, REINFORCEMENT_PATH, BRIDGE_DATA_PATH,
            CONCRETEQUALITY_CSV_PATH, MATERIALS_DIR, CONCRETE_PATH,
            SRC_REINFORCEMENT_PATH, PRESTRESS_PATH, BENDING_RADIUS_PATH,
            MATERIAL_DENSITY_PATH
        ]

        for path in all_paths:
            with self.subTest(path=str(path)):
                self.assertIsInstance(
                    path, Path,
                    f"Path should be a pathlib.Path object for cross-platform compatibility: {path}"
                )

    def test_template_file_is_binary_accessible(self) -> None:
        """Test that the SCIA template file can be accessed as binary (required for VIKTOR)."""
        self.assertTrue(SCIA_TEMPLATE_PATH.exists(), "SCIA template file must exist")
        
        # Test that we can read it as binary (this is how VIKTOR File.from_path works)
        try:
            with SCIA_TEMPLATE_PATH.open('rb') as f:
                content = f.read(100)  # Read first 100 bytes
                self.assertGreater(len(content), 0, "Template file should not be empty")
        except Exception as e:
            self.fail(f"Should be able to read SCIA template as binary: {e}")

    def test_csv_files_are_text_accessible(self) -> None:
        """Test that CSV files can be accessed as text with proper encoding."""
        csv_files = [
            ("Concrete Quality", CONCRETE_PATH),
            ("Reinforcement Steel", SRC_REINFORCEMENT_PATH),
            ("Prestressing Steel", PRESTRESS_PATH),
            ("Bending Radius", BENDING_RADIUS_PATH),
            ("Material Density", MATERIAL_DENSITY_PATH),
        ]

        for name, path in csv_files:
            with self.subTest(csv_file=name):
                self.assertTrue(path.exists(), f"{name} CSV file must exist")
                
                try:
                    with path.open('r', encoding='utf-8') as f:
                        first_line = f.readline()
                        self.assertGreater(len(first_line), 0, f"{name} CSV should not be empty")
                except Exception as e:
                    self.fail(f"Should be able to read {name} CSV as UTF-8 text: {e}")


if __name__ == "__main__":
    unittest.main()
