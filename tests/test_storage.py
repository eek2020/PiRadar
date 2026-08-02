from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from piradar.storage import CredentialsStore, EnrichmentCache


class StorageTests(unittest.TestCase):
    def test_enrichment_cache_persists_and_expires(self) -> None:
        now = [1000.0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cache.sqlite3"
            cache = EnrichmentCache(path, clock=lambda: now[0])
            cache.set("flight_details", "2026-08-02:ABC123", {"route": {"origin": "LHR"}}, 60)

            reopened = EnrichmentCache(path, clock=lambda: now[0])
            self.assertEqual(reopened.get("flight_details", "2026-08-02:ABC123")["route"]["origin"], "LHR")
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

            now[0] = 1060.0
            self.assertIsNone(reopened.get("flight_details", "2026-08-02:ABC123"))

    def test_credentials_are_owner_only_and_summaries_hide_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credentials.json"
            store = CredentialsStore(path)
            summary = store.replace("amadeus", {"client_id": "identifier", "client_secret": "top-secret-value"})

            self.assertTrue(summary["amadeus"]["configured"])
            self.assertNotIn("top-secret-value", json.dumps(summary))
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(CredentialsStore(path).credentials("amadeus")["client_id"], "identifier")

            cleared = store.replace("amadeus", {"client_id": "", "client_secret": ""})
            self.assertFalse(cleared["amadeus"]["configured"])

    def test_partial_multi_field_credentials_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CredentialsStore(Path(directory) / "credentials.json")
            with self.assertRaisesRegex(ValueError, "all credential fields"):
                store.replace("amadeus", {"client_id": "identifier", "client_secret": ""})


if __name__ == "__main__":
    unittest.main()
