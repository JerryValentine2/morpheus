"""Apollo HTTP transport for Morpheus. No direct Firestore/GCS access.

Exact document retrieval requires the Apollo backend's new /content route.
This transport does not authorize product activation or infer a product list.
"""
import json
import urllib.error
import urllib.parse
import urllib.request


class ApolloAPIError(RuntimeError):
    pass


class ApolloHTTPClient:
    def __init__(self, base_url: str, write_key: str, timeout: int = 15):
        if not base_url.startswith("https://") or not write_key:
            raise ApolloAPIError("INVALID_APOLLO_CONFIGURATION")
        self.base_url = base_url.rstrip("/")
        self.write_key = write_key
        self.timeout = timeout

    def read_document_content(self, product_id: str, document_id: str) -> dict:
        if not product_id or not document_id or any(
            "/" in value or value in (".", "..") for value in (product_id, document_id)
        ):
            raise ApolloAPIError("INVALID_DOCUMENT_IDENTITY")
        path = "/products/{}/documents/{}/content".format(
            urllib.parse.quote(product_id, safe=""),
            urllib.parse.quote(document_id, safe=""),
        )
        request = urllib.request.Request(
            self.base_url + path,
            headers={"X-API-Key": self.write_key, "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ApolloAPIError("APOLLO_READ_FAILED")
                payload = json.load(response)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            raise ApolloAPIError("APOLLO_READ_FAILED") from exc
        if not isinstance(payload, dict):
            raise ApolloAPIError("INVALID_APOLLO_RESPONSE")
        return payload
