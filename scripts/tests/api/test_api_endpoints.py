import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api.api_endpoints import (
    app
)
from api.api_state import APIStateEnum
from sample_requests import ue_payload, ric_payload, ue_list_payload


class TestAPIEndpoints:
    """Test suite for FastAPI endpoints in api_endpoints.py"""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app"""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test the root landing page endpoint"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_health_status(self, client):
        """Test the health status endpoint"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "service" in data
        assert "timestamp" in data

    def test_get_status(self, client):
        """Test the status endpoint"""
        response = client.get("/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "timestamp" in data
        assert "repositories_checked_out" in data

    @pytest.mark.asyncio
    async def test_set_gnb_config(self, client):
        """Test setting gNB configuration"""

        gnb_payload = {
            "implementation": "srs",
            "repository": "https://github.com/srsran/srsRAN_Project.git",
            "commit": "11c9bbabb69873752500d676f55e0034f6caa5c5",
            "build_type": "docker",
            "ip_config": {
                "e2": "10.0.2.3",
                "ru_sdr": "10.45.1.1",
                "cu_cp": "10.53.1.3",
            },
            "srate": 11.52e6,
            "tx_gain": 75,
            "rx_gain": 75,
        }

        response = client.post("/gnb-config", json=gnb_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == APIStateEnum.OK.value

    @pytest.mark.asyncio
    async def test_set_5g_core_config(self, client):
        """Test setting 5G core configuration"""

        core_5g_payload = {
            "implementation": "open5gs",
            "repository": "https://github.com/open5gs/open5gs.git",
            "commit": "2b6369e9d997eb8eb158e3803e3ae4f4d207cd4d",
            "build_type": "docker",
            "network": {
                "ip": "10.53.1.2",
                "mongodb_ip": "10.53.1.5",
                "subnet": "10.53.1.0/24",
            },
        }

        response = client.put("/core5g-config", json=core_5g_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == APIStateEnum.OK.value

    @pytest.mark.asyncio
    async def test_set_near_rt_ric_config(self, client):
        """Test setting Near-RT RIC configuration"""

        response = client.post("/near-rt-ric-config", json=ric_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == APIStateEnum.OK.value

    @pytest.mark.asyncio
    async def test_set_ue_config_list_valid(self, client):
        """Test setting UE configuration list with valid data"""

        response = client.put("/ue-config-list", json=ue_list_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == APIStateEnum.OK.value

    @pytest.mark.asyncio
    async def test_set_ue_config(self, client):
        """First sets the UE list and then adds a UE."""

        response = client.put("/ue-config-list", json=ue_list_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == APIStateEnum.OK.value

        response = client.post("/ue-config", json=ue_payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == APIStateEnum.OK.value

    @pytest.mark.asyncio
    async def test_clear_errors(self, client):
        """Test clearing error cache"""
        response = client.delete("/clear-errors")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == APIStateEnum.OK.value
