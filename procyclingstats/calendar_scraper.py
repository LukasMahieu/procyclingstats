from typing import Any, Dict, List

from .scraper import Scraper
from .table_parser import TableParser
from .utils import parse_table_fields_args


class Calendar(Scraper):
    """
    Scraper for Calendar HTML page.
    """

    def calendar(self, *args: str) -> List[Dict[str, Any]]:
        """
        Parses calendar from HTML.
        """
        available_fields = (
            "date",
            "race_name",
            "race_url", 
            "stage_name",
            "stage_url",
            "rider_name",
            "rider_url",
        )

        fields = parse_table_fields_args(args, available_fields)
        calendar_html = self.html.css_first("table.basic")

        if calendar_html:
            calendar_parser = TableParser(calendar_html)
            calendar_parser.parse(fields)
            return calendar_parser.table
        return []
