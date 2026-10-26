from datetime import date

import pytest

import extrate


def test_clickstream_url():
    assert extrate.clickstream_url("2026-01") == (
        "https://dumps.wikimedia.org/other/clickstream/2026-01/clickstream-frwiki-2026-01.tsv.gz")


def test_previous_months_crosses_year():
    assert list(extrate.previous_months(date(2026, 2, 15), 3)) == ["2026-01", "2025-12", "2025-11"]


def test_months_between():
    assert extrate.months_between("2025-11", "2026-02") == ["2025-11", "2025-12", "2026-01", "2026-02"]
    assert extrate.months_between("2026-03", "2026-03") == ["2026-03"]
    assert extrate.months_between("2026-04", "2026-03") == []


def test_latest_available_month(monkeypatch):
    available = {"2025-12"}
    monkeypatch.setattr(extrate, "month_is_available", lambda m, wiki="frwiki": m in available)
    monkeypatch.setattr(extrate, "date", type("D", (), {"today": staticmethod(lambda: date(2026, 2, 3))}))
    assert extrate.latest_available_month() == "2025-12"


def _fake_urlopen(code, seen):
    def urlopen(req, timeout=None):
        seen.append(req)
        raise extrate.urllib.error.HTTPError(req.full_url, code, "x", {}, None)
    return urlopen


def test_month_is_available_sends_user_agent_and_404_is_false(monkeypatch):
    seen = []
    monkeypatch.setattr(extrate.urllib.request, "urlopen", _fake_urlopen(404, seen))
    assert extrate.month_is_available("2026-10") is False
    assert seen[0].get_header("User-agent") == extrate.USER_AGENT
    assert seen[0].get_method() == "HEAD"


def test_month_is_available_does_not_hide_403(monkeypatch):
    monkeypatch.setattr(extrate.urllib.request, "urlopen", _fake_urlopen(403, []))
    with pytest.raises(extrate.urllib.error.HTTPError):
        extrate.month_is_available("2026-09")


def test_read_data_without_filter(clickstream_file):
    df = extrate.read_data(clickstream_file)
    assert list(df.columns) == extrate.COLUMNS
    assert len(df) == 11
    assert df["n"].dtype == "int64"


def test_read_data_with_filter_by_chunks(clickstream_file):
    df = extrate.read_data(clickstream_file, filter_fn=lambda c: c["n"] >= 300, chunksize=3)
    assert sorted(df["n"]) == [300, 300, 400, 500, 1000]


def test_read_data_keeps_null_like_titles(tmp_path):
    path = tmp_path / "cs.tsv"
    path.write_text("other-search\tNA\texternal\t5\nNULL\tnan\tlink\t2\n", encoding="utf-8")
    df = extrate.read_data(str(path))
    assert list(df["curr"]) == ["NA", "nan"]
