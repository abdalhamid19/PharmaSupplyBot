"""Exception classes for Tawreed order processing."""


class _SkipItem(Exception):
    """Signal that one item should be skipped without failing the whole order run."""

    pass


class _NoResultsItem(_SkipItem):
    """Signal that one item had no Tawreed results and should be skipped quickly."""

    pass
