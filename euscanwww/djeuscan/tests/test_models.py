"""
tests for models
"""

from datetime import datetime

from django.utils import unittest
from django.db import IntegrityError

from djeuscan.models import EuscanResult
from djeuscan.tests.euscan_factory import VersionFactory, PackageFactory, \
    EuscanResultFactory


class VersionModelTests(unittest.TestCase):
    def test_creation(self):
        package = PackageFactory.build()
        version = VersionFactory.build(package=package)
        self.assertEqual(version.package, package)

    def test_not_allowed_creation(self):
        package = PackageFactory.create()
        VersionFactory.create(package=package)

        with self.assertRaises(IntegrityError):
            VersionFactory.create(package=package)


class PackageModelTests(unittest.TestCase):
    def test_homepages(self):
        homepage = "http://gentoo.org http://mypackage.com"
        package = PackageFactory.build(homepage=homepage)
        self.assertEqual(package.homepages,
                         ["http://gentoo.org", "http://mypackage.com"])


class EuscanResultModelTests(unittest.TestCase):
    def test_lastest(self):
        result1 = EuscanResultFactory.create(datetime=datetime(2012, 04, 01))
        result2 = EuscanResultFactory.create(datetime=datetime(2012, 01, 01))
        self.assertEqual(result1, EuscanResult.objects.latest())
