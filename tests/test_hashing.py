from shared.hashing import normalize_for_hash, sha256_hex


def test_sha256_hex_is_deterministic():
    assert sha256_hex(b"hello") == sha256_hex(b"hello")
    assert sha256_hex(b"hello") != sha256_hex(b"world")


def test_normalize_for_hash_strips_volatile_timing_comment():
    # regression test for the real bug: this comment's value changes on every request,
    # which otherwise made an unchanged page hash differently on every crawl
    html_a = b"<p>content</p><!-- cached or not being index.aspx page --><!-- Elapsed time: 0.0156223 -->"
    html_b = b"<p>content</p><!-- cached or not being index.aspx page --><!-- Elapsed time: 9.9999999 -->"

    normalized_a = normalize_for_hash(html_a, "html")
    normalized_b = normalize_for_hash(html_b, "html")

    assert normalized_a == normalized_b
    assert sha256_hex(normalized_a) == sha256_hex(normalized_b)


def test_normalize_for_hash_leaves_non_html_untouched():
    pdf_bytes = b"%PDF-1.4 fake pdf content"
    assert normalize_for_hash(pdf_bytes, "pdf") == pdf_bytes


def test_normalize_for_hash_still_detects_real_content_changes():
    html = b"<p>real content</p><!-- cached or not being index.aspx page --><!-- Elapsed time: 0.01 -->"
    changed_html = b"<p>different content</p><!-- cached or not being index.aspx page --><!-- Elapsed time: 0.01 -->"
    assert normalize_for_hash(html, "html") != normalize_for_hash(changed_html, "html")
