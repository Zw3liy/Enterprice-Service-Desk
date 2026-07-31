from django.test import TestCase
from apps.assignment_engine.services import AssignmentService
class AsgTests(TestCase):
    def test_import(self):
        self.assertTrue(hasattr(AssignmentService, "auto_assign"))
