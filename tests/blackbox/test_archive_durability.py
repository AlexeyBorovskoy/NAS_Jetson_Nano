"""A failed flush of the published HDD name must retain the SSD source."""
from blackbox import archive
from test_archive_safety import _Run, _Result, _case, _catalog


def test_published_directory_flush_failure_retains_source(tmp_path):
    cfg, source = _case(tmp_path)
    catalog = _catalog(tmp_path)

    class FailFinalSync(_Run):
        def __call__(self, argv, **kwargs):
            if 'sync' in argv and str(argv[-1]).endswith('.tar.xz'):
                return _Result(1)
            return super().__call__(argv, **kwargs)

    result = archive.archive_week(cfg, catalog, '2026-W40', FailFinalSync())
    assert result['status'] == 'failed'
    assert source.exists()
    assert catalog.archives() == []
    catalog.close()
