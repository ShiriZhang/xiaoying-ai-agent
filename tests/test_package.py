"""Check the installed distribution, without adding src to the import path."""

import importlib.metadata
import pathlib
import sys
import unittest

import enterprise_knowledge_qa


class PackageTests(unittest.TestCase):
    def test_installed_package_in_isolated_environment(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix)
        package = pathlib.Path(enterprise_knowledge_qa.__file__).resolve()
        self.assertTrue(package.is_relative_to(pathlib.Path(sys.prefix).resolve()))
        self.assertEqual(
            importlib.metadata.version("enterprise-knowledge-qa"),
            enterprise_knowledge_qa.__version__,
        )


if __name__ == "__main__":
    unittest.main()
