"""Network layer for fetching and writing story data from the DeskFox API."""

from __future__ import annotations

import sys
import threading
from typing import Any, Dict, Optional, Tuple

import requests


class StoryManager:
    """Handles async HTTP fetches for fishing story results.

    Communicates with a remote Deno backend that stores story data in
    Deno KV. Network calls run on daemon threads to avoid blocking the
    main Pygame loop; results are delivered via a thread-safe queue.
    """

    REQUEST_TIMEOUT_S: int = 5
    NON_FOX_STORY_RANGE: Tuple[int, int] = (11, 20)

    def __init__(
        self, pet_context: Any, base_url: str, pathname: str
    ) -> None:
        """Initialize the story manager with the backend URL.

        Args:
            pet_context: The ``DesktopPet`` instance.
            base_url: Base URL of the Deno story server.
            pathname: API path (typically ``/stories``).
        """
        self.pet: Any = pet_context
        self.base_url: str = base_url
        self.pathname: str = pathname
        self.full_url: str = f"{self.base_url}{self.pathname}"
        self.last_read_index: int = 0

    def get_next_story_id(self) -> int:
        """Return the next story index to fetch from the API.

        Returns:
            ``last_read_index + 1`` based on the pet's current index.
        """
        self.last_read_index = self.pet.last_read_index
        return self.last_read_index + 1

    def fetch_story_sync(self, index: int) -> Optional[Dict[str, Any]]:
        """Synchronously fetch story data for a given index.

        Attempts standard JSON parsing first, then falls back to
        ``ast.literal_eval`` for Python-literal responses.

        Args:
            index: The story index to request.

        Returns:
            A dictionary with ``title``, ``author``, and ``content`` keys,
            or ``None`` if the request fails or the response is invalid.
        """
        try:
            params: Dict[str, int] = {"index": index}
            response = requests.get(
                self.full_url, params=params, timeout=self.REQUEST_TIMEOUT_S
            )

            if response.status_code == 200:
                raw_content: str = response.text
                try:
                    story_data: Dict[str, Any] = response.json()
                except ValueError:
                    import ast
                    try:
                        story_data = ast.literal_eval(raw_content)
                    except (ValueError, SyntaxError):
                        return None

                required_keys = ["title", "author", "content"]
                if isinstance(story_data, dict) and all(
                    key in story_data for key in required_keys
                ):
                    return story_data
                else:
                    return None
            else:
                return None

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network error during story fetch: {e}")
            return None

    def fetch_story_async(self, story_id: int) -> None:
        """Fetch story data on a background daemon thread.

        The result is pushed into the pet's ``_tk_queue`` for the main
        thread to pick up via its queue poller.

        Args:
            story_id: The story index to request from the API.
        """

        def target() -> None:
            story_data_or_error = self.fetch_story_sync(story_id)
            is_successful = isinstance(story_data_or_error, dict)
            payload = story_data_or_error
            queue_item: Tuple[str, bool, Any, int] = (
                "story_result", is_successful, payload, story_id,
            )

            try:
                self.pet._tk_queue.put(queue_item)
            except Exception as e:
                print(
                    f"ERROR: [Async Thread] Failed to push result to queue: {e}",
                    file=sys.stderr,
                    flush=True,
                )

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()

    def write_data_sync(
        self, index: str, data: Dict[str, Any]
    ) -> Optional[str]:
        """Synchronously POST data to the API for the given index.

        Args:
            index: The target story index (sent as a string).
            data: A dictionary to write.

        Returns:
            The API response text on success, or ``None`` on failure.
        """
        try:
            json_payload: Dict[str, Any] = {"index": str(index), "data": data}
            response = requests.post(
                self.full_url,
                json=json_payload,
                timeout=self.REQUEST_TIMEOUT_S,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                return response.text
            else:
                return None

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Network error during data write: {e}")
            return None
