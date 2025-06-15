"""Tests for ImageProcessor protocol."""

from emojismith.domain.repositories.image_processor import ImageProcessor


def test_image_processor_protocol_defines_process_method() -> None:
    """Test that ImageProcessor protocol defines the required process method."""
    # This test ensures the protocol is defined correctly
    assert hasattr(ImageProcessor, "process")

    # Check that we can implement the protocol
    class TestProcessor(ImageProcessor):
        def process(self, image_data: bytes) -> bytes:
            return image_data

    processor = TestProcessor()
    result = processor.process(b"test data")
    assert result == b"test data"
