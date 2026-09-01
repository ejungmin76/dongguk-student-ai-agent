import importlib
import unittest


class PackageArchitectureTests(unittest.TestCase):
    def test_stable_architecture_packages_are_importable(self):
        packages = [
            "agent.schemas",
            "agent.planners",
            "agent.executors",
            "agent.responders",
            "agent.validators",
            "tools.academic",
            "tools.knowledge",
            "tools.university_service",
        ]

        for package in packages:
            with self.subTest(package=package):
                importlib.import_module(package)
