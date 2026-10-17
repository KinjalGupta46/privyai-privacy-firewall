"""
tests/test_security_utils.py

Phase 1 tests — security utility functions.
"""

from __future__ import annotations


def test_generate_request_id_is_string():
    from app.core.security import generate_request_id
    rid = generate_request_id()
    assert isinstance(rid, str)
    assert len(rid) == 36  # standard UUID4 length


def test_generate_request_id_is_unique():
    from app.core.security import generate_request_id
    ids = {generate_request_id() for _ in range(100)}
    assert len(ids) == 100, "Expected all 100 request IDs to be unique"


def test_sanitize_filename_safe():
    from app.core.security import sanitize_filename
    assert sanitize_filename("report_final.pdf") == "report_final.pdf"


def test_sanitize_filename_strips_path_traversal():
    from app.core.security import sanitize_filename
    result = sanitize_filename("../../etc/passwd")
    # Must not contain double-dots or slashes after sanitisation.
    assert ".." not in result, f"Double-dot still present: {result}"
    assert "/" not in result
    # Must still have some content (not empty).
    assert len(result) > 0


def test_sanitize_filename_strips_leading_dot():
    from app.core.security import sanitize_filename
    result = sanitize_filename(".hidden_file")
    assert not result.startswith(".")


def test_sanitize_filename_replaces_special_chars():
    from app.core.security import sanitize_filename
    result = sanitize_filename("file name (1).pdf")
    assert " " not in result
    assert "(" not in result
    assert ")" not in result


def test_sanitize_filename_empty_string():
    from app.core.security import sanitize_filename
    result = sanitize_filename("")
    assert result == "unnamed_file"
