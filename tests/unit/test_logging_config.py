"""Tests for ToolUniverse logging configuration."""

import logging

import pytest

from tooluniverse.logging_config import ToolUniverseFormatter, _stream_supports_unicode


class EncodingCheckingStream:
    """Minimal stream that raises if written text cannot be encoded."""

    def __init__(self, encoding):
        self.encoding = encoding
        self.values = []

    def write(self, value):
        value.encode(self.encoding)
        self.values.append(value)

    def flush(self):
        pass

    def getvalue(self):
        return "".join(self.values)


@pytest.mark.unit
def test_stream_supports_unicode_detects_cp1252_limitations():
    """Non-UTF Windows streams should not receive emoji log prefixes."""

    stream = EncodingCheckingStream("cp1252")

    assert _stream_supports_unicode(stream) is False


@pytest.mark.unit
def test_stream_supports_unicode_accepts_utf8_streams():
    """UTF-8 streams should keep the existing emoji log prefixes."""

    stream = EncodingCheckingStream("utf-8")

    assert _stream_supports_unicode(stream) is True


@pytest.mark.unit
def test_formatter_does_not_emit_emoji_for_cp1252_stream():
    """Formatter output should be encodable by non-UTF Windows consoles."""

    stream = EncodingCheckingStream("cp1252")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        ToolUniverseFormatter(
            fmt="%(message)s",
            use_emoji=_stream_supports_unicode(stream),
        )
    )

    record = logging.LogRecord(
        name="tooluniverse.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Loaded 1 tool",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    assert stream.getvalue() == "Loaded 1 tool\n"


@pytest.mark.unit
def test_formatter_keeps_prefixes_for_utf8_stream():
    """Formatter should preserve prefixed output when the stream supports it."""

    stream = EncodingCheckingStream("utf-8")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        ToolUniverseFormatter(
            fmt="%(message)s",
            use_emoji=_stream_supports_unicode(stream),
        )
    )

    record = logging.LogRecord(
        name="tooluniverse.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Loaded 1 tool",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    assert "Loaded 1 tool" in stream.getvalue()
    assert stream.getvalue() != "Loaded 1 tool\n"
