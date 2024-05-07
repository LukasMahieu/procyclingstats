import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import requests
from selectolax.parser import HTMLParser

from .errors import ExpectedParsingError


class Scraper:
    """Base class for all scraping classes."""

    BASE_URL: str = "https://www.procyclingstats.com/"

    _public_nonparsing_methods = ("update_html", "parse", "relative_url")
    """Public methods that aren't called by `parse` method."""

    def __init__(self, url: str, **params) -> None:
        """
        Initializes a scraper object with an endpoint and parameters to dynamically build the URL.

        :param url: (Relative) URL or endpoint on the base site to be accessed.
        :param params: Keyword arguments representing query parameters to construct the URL dynamically.
        """
        url = self._make_url_absolute(url)
        if params:
            url = f"{url}.php"
            url = self._make_url_with_params(url, **params)
        self.__init_with_url(url)

    def __init_with_url(
        self, url: str, html: Optional[str] = None, update_html: bool = True
    ) -> None:
        """
        Creates scraper object that is by default ready for HTML parsing. Call
        parsing methods to parse data from HTML.

        :param url: URL of procyclingstats page to parse. Either absolute or
            relative.
        :param html: HTML to be parsed from, defaults to None. When passing the
            parameter, set `update_html` to False to prevent overriding or
            making useless request.
        :param update_html: Whether to make request to given URL and update
            `self.html`. When False `self.update_html` method has to be called
            manually to make object ready for parsing. Defaults to True.

        :raises ValueError: When given HTML or HTML from given URL is invalid,
            e.g. 'Page not found' is contained in the HTML.
        """
        # validate given URL
        self._url = url
        self._html = None
        if html:
            self._html = HTMLParser(html)
            if not self._html_valid():
                raise ValueError("Given HTML is invalid.")
            self._set_up_html()
        if update_html:
            self.update_html()
            if not self._html_valid():
                raise ValueError(f"HTML from given URL is invalid: '{self.url}'")
            self._set_up_html()

    def _make_url_with_params(self, endpoint: str, **params) -> str:
        """
        Constructs a complete URL from the endpoint and provided parameters.

        :param endpoint: Endpoint of the website to attach to the base URL.
        :param params: Dictionary of query parameters.
        :return: Fully constructed URL.
        """
        query = "&".join(
            f"{key}={value}" for key, value in params.items() if value is not None
        )
        url = f"{endpoint.strip('/')}"
        return f"{url}?{query}" if query else url

    def __repr__(self) -> str:
        return f"{type(self).__name__}(url='{self.url}')"

    @property
    def url(self) -> str:
        """Absolute URL from URL that was passed when constructing."""
        return self._url

    @property
    def html(self) -> HTMLParser:
        """
        HTML that is used for parsing.

        :raises AttributeError: when HTML is None
        """
        if self._html is None:
            raise AttributeError(
                "In order to access HTML, update it using "
                + "`self.update_html` method."
            )
        return self._html

    def relative_url(self) -> str:
        """
        Makes relative URL from absolute url (cuts `self.BASE_URL` from URL).

        :return: Relative URL.
        """
        return "/".join(self._url.split("/")[3:])

    def update_html(self) -> None:
        """
        Calls request to `self.url` and updates `self.html` to HTMLParser
        object created from returned HTML.
        """
        html_str = requests.get(self._url).text
        # pylint: disable=missing-timeout
        self._html = HTMLParser(html_str)

    def parse(
        self,
        exceptions_to_ignore: Tuple[Type[Exception], ...] = (ExpectedParsingError,),
        none_when_unavailable: bool = True,
    ) -> Dict[str, Any]:
        """
        Creates JSON like dict with parsed data by calling all parsing methods.
        Keys in dict are methods names and values parsed data

        :param exceptions_to_ignore: Tuple of exceptions that should be
            ignored when raised by parsing methods. Defaults to
            ``(ExpectedParsingError,)``
        :param none_when_unavailable: Whether to set dict value to None when
            method raises ignored exception. When False the key value pair is
            skipped. Defaults to True.
        :return: Dict with parsing methods mapping to parsed data.
        """
        parsing_methods = self._parsing_methods()
        parsed_data = {}
        for method_name, method in parsing_methods:
            try:
                parsed_data[method_name] = method()
            except exceptions_to_ignore:
                if none_when_unavailable:
                    parsed_data[method_name] = None
        return parsed_data

    def _decompose_url(self) -> List[str]:
        """
        Splits relative URL to list of strings.

        :return: Splitted relative URL without empty strings.
        """
        splitted_url = self.relative_url().split("/")
        return [part for part in splitted_url if part]

    def _parsing_methods(self) -> List[Tuple[str, Callable]]:
        """
        Gets all parsing methods from a class. That are all public methods
        except of methods listed in `_public_nonparsing_methods`.

        :return: List of tuples parsing methods names and parsing methods.
        """
        methods = inspect.getmembers(self, predicate=inspect.ismethod)
        parsing_methods = []
        for method_name, method in methods:
            if (
                method_name[0] != "_"
                and method_name not in self._public_nonparsing_methods
            ):
                parsing_methods.append((method_name, method))
        return parsing_methods

    def _make_url_absolute(self, url: str) -> str:
        """
        Makes absolute URL from given url (adds `self.base_url` to URL if
        needed).

        :param url: URL to format.
        :return: Absolute URL.
        """
        if "https" not in url:
            if url[0] == "/":
                url = self.BASE_URL + url[1:]
            else:
                url = self.BASE_URL + url
        return url

    def _set_up_html(self):
        """
        Empty method that should be overridden by subclasses if it's needed to
        modify HTML before parsing.
        """

    def _html_valid(self) -> bool:
        """
        Checks whether given HTML is valid based on some known invalid formats
        of invalid HTMLs.

        :return: True if given HTML is valid, otherwise False.
        """
        try:
            page_title = self.html.css_first(".page-title > .main > h1").text()
            assert page_title != "Page not found"

            page_title2 = self.html.css_first("div.page-content > div").text()
            assert page_title2 != (
                "Due to technical difficulties this page "
                + "is temporarily unavailable."
            )

            page_title3 = self.html.css_first(".page-title > .main > h1").text()
            assert page_title3 != "Start"
            return True
        except AssertionError:
            return False
