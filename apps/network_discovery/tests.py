from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.network_discovery.models import DiscoveryScan
from apps.network_discovery.services import NetworkDiscoveryService
from apps.service_desk.models import Company

User = get_user_model()


class NetworkDiscoveryTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="NetCo", slug="net-co")
        self.user = User.objects.create_user(
            username="netops", password="pass12345", is_staff=True
        )

    def test_run_scan_sim(self):
        scan = NetworkDiscoveryService.create_scan(
            self.company, name="DC sweep", cidr="10.10.0.0/29", created_by=self.user
        )
        NetworkDiscoveryService.run_scan(scan)
        scan.refresh_from_db()
        self.assertEqual(scan.state, DiscoveryScan.State.COMPLETED)
        self.assertGreater(scan.hosts_found, 0)
        self.assertEqual(scan.hosts.count(), scan.hosts_found)
