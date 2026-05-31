from postgres_task_queue.pgmq.metadata import Header, MessageStatus


class TestHeaderEnum:
    """Tests for Header enum."""

    def test_full_names(self):
        assert Header.STATUS.full_name() == "x-pgtq-status"
        assert Header.DLQ.full_name() == "x-pgtq-dlq"
        assert Header.ERRORS.full_name() == "x-pgtq-errors"


class TestMessageStatusEnum:
    """Tests for MessageStatus enum."""

    def test_status_values(self):
        assert MessageStatus.QUEUED == "queued"
        assert MessageStatus.PROCESSING == "processing"
        assert MessageStatus.FAILED == "failed"
        assert MessageStatus.COMPLETED == "completed"
