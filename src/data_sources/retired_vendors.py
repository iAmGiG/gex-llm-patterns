"""Placeholder clients for vendors whose access has ended (issue #272).

gex-database-infrastructure retired its Alpha Vantage and Polygon.io clients. Code paths that only
fetched from those vendors now get a RetiredVendorClient, which raises a RuntimeError naming the
vendor on first use instead of making any network call.
"""

ALPHA_VANTAGE_RETIRED = "Alpha Vantage (retired 2026-10-10; the premium key must not be used)"
POLYGON_RETIRED = "Polygon.io (access ended 2026-11-01)"


class RetiredVendorClient:
    """Stand-in for a retired vendor client: any attribute access raises RuntimeError."""

    def __init__(self, vendor: str = ALPHA_VANTAGE_RETIRED):
        self._vendor = vendor

    def __getattr__(self, name):
        raise RuntimeError(f"{self._vendor} client is unavailable: {name}() would need the retired vendor.")
