"""Tests for the pgmq.fastapi module."""

from datetime import timedelta
from unittest.mock import AsyncMock

import httpx2
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from postgres_task_queue._broker import Broker
from postgres_task_queue._queue import ArchiveOptions, Queue, DEFAULT_ARCHIVE_OPTIONS
from postgres_task_queue.pgmq.fastapi import (
    ArchiveOptionsModel,
    QueueInfo,
    create_router,
)


# Unit tests - no database required
class TestArchiveOptionsModel:
    """Tests for ArchiveOptionsModel.from_options method."""

    def test_from_options_with_ttl_and_limit(self):
        opts: ArchiveOptions = {"ttl": timedelta(days=30), "limit": 1000}
        model = ArchiveOptionsModel.from_options(opts)

        assert model.ttl == 30 * 24 * 60 * 60  # 30 days in seconds
        assert model.limit == 1000

    def test_from_options_with_only_ttl(self):
        opts: ArchiveOptions = {"ttl": timedelta(hours=2)}
        model = ArchiveOptionsModel.from_options(opts)

        assert model.ttl == 2 * 60 * 60  # 2 hours in seconds
        assert model.limit is None

    def test_from_options_with_only_limit(self):
        opts: ArchiveOptions = {"limit": 500}
        model = ArchiveOptionsModel.from_options(opts)

        assert model.ttl is None
        assert model.limit == 500

    def test_from_options_empty(self):
        opts: ArchiveOptions = {}
        model = ArchiveOptionsModel.from_options(opts)

        assert model.ttl is None
        assert model.limit is None


# Fixtures for mock brokers (used by unit tests that don't need real DB)
@pytest.fixture
def mock_broker():
    """Create a mock Broker for testing without DLQ."""
    mock = AsyncMock(spec=Broker)
    mock.queue_name = "test_queue"
    mock.dlq = None
    return mock


@pytest.fixture
def mock_broker_with_dlq():
    """Create a mock Broker with DLQ for testing."""
    mock = AsyncMock(spec=Broker)
    mock.queue_name = "test_queue"
    dlq_mock = AsyncMock(spec=Broker)
    dlq_mock.queue_name = "test_queue_dlq"
    mock.dlq = dlq_mock
    return mock


class TestQueueInfo:
    """Tests for QueueInfo.from_queue method."""

    def test_from_queue_with_archive_and_dlq(self, mock_broker_with_dlq):
        queue = Queue(mock_broker_with_dlq, archive=True, dlq_archive=True)
        info = QueueInfo.from_queue(queue)

        assert info.name == "test_queue"
        assert info.archive is not None
        assert info.archive.ttl == DEFAULT_ARCHIVE_OPTIONS["ttl"].total_seconds()
        assert info.archive.limit == DEFAULT_ARCHIVE_OPTIONS["limit"]
        assert info.dlq is not None
        assert info.dlq.name == "test_queue_dlq"
        assert info.dlq.archive is not None

    def test_from_queue_without_archive_and_dlq(self, mock_broker):
        queue = Queue(mock_broker, archive=False, dlq_archive=False)
        info = QueueInfo.from_queue(queue)

        assert info.name == "test_queue"
        assert info.archive is None
        assert info.dlq is None

    def test_from_queue_with_custom_archive_options(self, mock_broker):
        custom_opts: ArchiveOptions = {"ttl": timedelta(days=7), "limit": 100}
        queue = Queue(mock_broker, archive=custom_opts, dlq_archive=False)
        info = QueueInfo.from_queue(queue)

        assert info.name == "test_queue"
        assert info.archive is not None
        assert info.archive.ttl == 7 * 24 * 60 * 60  # 7 days in seconds
        assert info.archive.limit == 100
        assert info.dlq is None


class TestCreateRouter:
    """Tests for create_router function using TestClient (sync)."""

    class TestListQueue:
        @staticmethod
        def _create_app(router):
            """Helper to create a FastAPI app with the router mounted."""
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            return app

        @classmethod
        def _get_response(cls, router) -> list[dict]:
            app = cls._create_app(router)
            with TestClient(app) as client:
                response = client.get("/")
                assert response.status_code == 200
                return response.json()

        def test_no_queues(self):
            """Test that calling list_queues with no queues returns empty list."""
            router = create_router()
            assert self._get_response(router) == []

        def test_single_queue(self, mock_broker_with_dlq):
            """Test that a single queue is correctly returned."""
            queue = Queue(mock_broker_with_dlq, archive=True, dlq_archive=True)
            router = create_router(queue)
            data = self._get_response(router)

            assert len(data) == 1
            assert data[0]["name"] == "test_queue"
            assert data[0]["archive"] is not None
            assert data[0]["dlq"] is not None
            assert data[0]["dlq"]["name"] == "test_queue_dlq"

        def test_mutliple_queues(self):
            """Test that multiple queues are correctly returned."""
            queues = [
                Queue(
                    AsyncMock(
                        queue_name=f"test_queue_{idx}",
                        dlq=AsyncMock(queue_name=f"test_queue_{idx}_dlq"),
                    ),
                )
                for idx in range(2)
            ]

            router = create_router(*queues)
            data = self._get_response(router)
            assert [queue["name"] for queue in data] == [
                queue.broker.queue_name for queue in queues
            ]

        def test_queues_with_mixed_configurations(self):
            """Test queues with different archive/DLQ configurations."""
            # Create one broker with DLQ and archive
            mock_broker_with_all = AsyncMock(spec=Broker)
            mock_broker_with_all.queue_name = "queue_with_all"
            dlq_mock = AsyncMock(spec=Broker)
            dlq_mock.queue_name = "queue_with_all_dlq"
            mock_broker_with_all.dlq = dlq_mock

            # Create one broker without DLQ and archive
            mock_broker_minimal = AsyncMock(spec=Broker)
            mock_broker_minimal.queue_name = "queue_minimal"
            mock_broker_minimal.dlq = None

            queue_with_all = Queue(mock_broker_with_all, archive=True, dlq_archive=True)
            queue_minimal = Queue(mock_broker_minimal, archive=False, dlq_archive=False)

            router = create_router(queue_with_all, queue_minimal)
            data = self._get_response(router)

            assert data == [
                {
                    "name": "queue_with_all",
                    "archive": {
                        "ttl": DEFAULT_ARCHIVE_OPTIONS["ttl"].total_seconds(),
                        "limit": DEFAULT_ARCHIVE_OPTIONS["limit"],
                    },
                    "dlq": {
                        "name": "queue_with_all_dlq",
                        "archive": {
                            "ttl": DEFAULT_ARCHIVE_OPTIONS["ttl"].total_seconds(),
                            "limit": DEFAULT_ARCHIVE_OPTIONS["limit"],
                        },
                    },
                },
                {"name": "queue_minimal", "archive": None, "dlq": None},
            ]

        def test_queue_info_reflects_custom_archive_options(self):
            """Test that custom archive options are reflected in the response."""
            mock_broker = AsyncMock(spec=Broker)
            mock_broker.queue_name = "queue_custom"
            mock_broker.dlq = None

            custom_opts: ArchiveOptions = {"ttl": timedelta(days=7), "limit": 100}
            queue = Queue(mock_broker, archive=custom_opts, dlq_archive=False)

            router = create_router(queue)
            data = self._get_response(router)

            assert data == [
                {
                    "name": "queue_custom",
                    "archive": {"ttl": timedelta(days=7).total_seconds(), "limit": 100},
                    "dlq": None,
                }
            ]

    class TestListQueueItems:
        """Tests for the /{queue_name}/queue endpoint using real broker."""

        @staticmethod
        def _create_app(router):
            """Helper to create a FastAPI app with the router mounted."""
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            return app

        @pytest_asyncio.fixture
        async def client(self, broker: Broker):
            queue = Queue(broker)
            router = create_router(queue)
            app = self._create_app(router)

            transport = httpx2.ASGITransport(app=app)
            async with httpx2.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                yield client

        def test_returns_404_for_nonexistent_queue(self):
            """Test that requesting items from a non-existent queue returns 404."""
            router = create_router()
            app = self._create_app(router)

            with TestClient(app) as client:
                response = client.get("/nonexistent_queue/queue")
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()

        @pytest.mark.asyncio
        async def test_returns_paginated_items(
            self, client: httpx2.AsyncClient, broker: Broker
        ):
            """Test that items are returned with correct pagination."""
            payloads = [{"key": f"val-{idx}"} for idx in range(3)]

            for payload in payloads:
                await broker.enqueue(payload)

            response = await client.get("/test_queue/queue")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == len(payloads)
            assert data["page"] == 1
            assert data["page_size"] == 100
            assert data["total"] == len(payloads)

        @pytest.mark.asyncio
        async def test_pagination_with_page_and_page_size(
            self, client: httpx2.AsyncClient, broker
        ):
            """Test pagination with custom page and page_size parameters."""
            payloads = [{"key": f"value{idx}"} for idx in range(3)]
            for payload in payloads:
                await broker.enqueue(payload)

            response = await client.get("/test_queue/queue?page=1&page_size=2")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2
            assert data["page"] == 1
            assert data["page_size"] == 2

        @pytest.mark.asyncio
        async def test_item_structure(self, client: httpx2.AsyncClient, broker: Broker):
            """Test that items have the correct structure with id and payload."""
            payloads = [
                {"key": "value1"},
                {"key": "value2"},
                {"key": "value3"},
            ]

            ids = [await broker.enqueue(payload) for payload in payloads]

            response = await client.get("/test_queue/queue")
            assert response.status_code == 200
            data = response.json()
            assert data == {
                "items": [
                    {"id": id, "payload": payload} for id, payload in zip(ids, payloads)
                ],
                "page": 1,
                "page_size": 100,
                "total": 3,
            }
