# Copyright 2015 Planet Labs, Inc.
# Copyright 2022 Planet Labs PBC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Manage data for requests and responses."""
import logging
import re
from typing import AsyncGenerator, Callable, List, Optional
from urllib.parse import urlparse

import httpx

from .exceptions import PagingError

LOGGER = logging.getLogger(__name__)


class Response:
    """Handles the Planet server's response to a HTTP request."""

    def __init__(self, http_response: httpx.Response):
        """Initialize object.

        Parameters:
            http_response: Response that was received from the server.
        """
        self._http_response = http_response

    def __repr__(self):
        return f'<models.Response [{self.status_code}]>'

    @property
    def status_code(self) -> int:
        """HTTP status code"""
        return self._http_response.status_code

    @property
    def filename(self) -> Optional[str]:
        """Name of the download file.

        The filename is None if the response does not represent a download.
        """
        filename = None

        if self.length is not None:  # is a download file
            filename = _get_filename_from_response(self._http_response)

        return filename

    @property
    def length(self) -> Optional[int]:
        """Length of the download file.

        The length is None if the response does not represent a download.
        """
        LOGGER.warning('here')
        try:
            length = int(self._http_response.headers["Content-Length"])
        except KeyError:
            length = None
        LOGGER.warning(length)
        return length

    def json(self) -> dict:
        """Response json"""
        return self._http_response.json()


def _get_filename_from_response(response) -> Optional[str]:
    """The name of the response resource.

        The default is to use the content-disposition header value from the
        response. If not found, falls back to resolving the name from the url
        or generating a random name with the type from the response.
        """
    name = (_get_filename_from_headers(response.headers)
            or _get_filename_from_url(str(response.url)))
    return name


def _get_filename_from_headers(headers: httpx.Headers) -> Optional[str]:
    """Get a filename from the Content-Disposition header, if available."""
    cd = headers.get('content-disposition', '')
    match = re.search('filename="?([^"]+)"?', cd)
    return match.group(1) if match else None


def _get_filename_from_url(url: str) -> Optional[str]:
    """Get a filename from the  url.

    Getting a name for Landsat imagery uses this function.
    """
    path = urlparse(url).path
    name = path[path.rfind('/') + 1:]
    return name or None


class Paged:
    """Asynchronous iterator over results in a paged resource.

    Each returned result is a JSON dict.
    """
    LINKS_KEY = '_links'
    NEXT_KEY = 'next'
    ITEMS_KEY = 'items'

    def __init__(self,
                 response: Response,
                 request_fcn: Callable,
                 limit: int = 0):
        """
        Parameters:
            request: Request to send to server for first page.
            request_fcn: Function for submitting a request and retrieving a
            result. Must take in url and method parameters.
            limit: Maximum number of results to return. When set to 0, no
                maximum is applied.
        """
        self._request_fcn = request_fcn

        self._pages = self._get_pages(response)

        self._items: List[dict] = []

        self.i = 0
        self.limit = limit

    def __aiter__(self):
        return self

    async def __anext__(self) -> dict:
        # This was implemented because traversing _get_pages()
        # in an async generator was resulting in retrieving all the
        # pages, when the goal is to stop retrieval when the limit
        # is reached
        if self.limit and self.i >= self.limit:
            raise StopAsyncIteration

        try:
            item = self._items.pop(0)
            self.i += 1
        except IndexError:
            page = await self._pages.__anext__()
            self._items = page[self.ITEMS_KEY]
            try:
                item = self._items.pop(0)
                self.i += 1
            except IndexError:
                raise StopAsyncIteration

        return item

    async def _get_pages(self, response) -> AsyncGenerator:
        page = response.json()
        yield page

        next_url = self._next_link(page)
        while (next_url):
            LOGGER.debug('getting next page')
            response = await self._request_fcn(url=next_url, method='GET')
            page = response.json()

            # If the next URL is the same as the previous URL we will
            # get the same response and be stuck in a page cycle. This
            # has happened in development and could happen in the case
            # of a bug in the production API.
            prev_url = next_url
            next_url = self._next_link(page)

            if next_url == prev_url:
                raise PagingError(
                    "Page cycle detected at {!r}".format(next_url))

            yield page

    def _next_link(self, page):
        try:
            next_link = page[self.LINKS_KEY][self.NEXT_KEY]
            LOGGER.debug(f'next: {next_link}')
        except KeyError:
            LOGGER.debug('end of the pages')
            next_link = False
        return next_link
