from __future__ import annotations

import io
import json
import unittest
from urllib.error import HTTPError

from piradar.location import PostcodeGeocoder


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class PostcodeGeocoderTests(unittest.TestCase):
    def test_resolves_and_normalizes_postcode(self) -> None:
        requested_urls: list[str] = []

        def opener(request: object, timeout: int) -> FakeResponse:
            requested_urls.append(request.full_url)  # type: ignore[attr-defined]
            self.assertEqual(timeout, 8)
            return FakeResponse(
                {
                    "result": {
                        "postcode": "OX1 1AA",
                        "latitude": 51.752,
                        "longitude": -1.2577,
                    }
                }
            )

        location = PostcodeGeocoder(opener=opener).lookup("ox1 1aa")
        self.assertEqual(location["postcode"], "OX1 1AA")
        self.assertEqual(requested_urls, ["https://api.postcodes.io/postcodes/OX11AA"])

    def test_rejects_incomplete_postcode_without_network_call(self) -> None:
        geocoder = PostcodeGeocoder(opener=lambda *_args, **_kwargs: self.fail("unexpected lookup"))
        with self.assertRaisesRegex(ValueError, "complete UK postcode"):
            geocoder.lookup("OX1")

    def test_reports_unknown_postcode(self) -> None:
        def opener(*_args: object, **_kwargs: object) -> FakeResponse:
            raise HTTPError("https://api.postcodes.io", 404, "Not Found", {}, io.BytesIO())

        with self.assertRaisesRegex(ValueError, "postcode not found"):
            PostcodeGeocoder(opener=opener).lookup("ZZ1 1ZZ")


if __name__ == "__main__":
    unittest.main()
