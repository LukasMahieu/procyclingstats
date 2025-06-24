from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union
import re


from selectolax.parser import Node

from .errors import ExpectedParsingError, UnexpectedParsingError
from .utils import add_times, format_time


class TableParser:
    """
    Parser for HTML tables. Parsed content is stored in `self.table`, which is
    represented as list of dicts.

    :param html_table: HTML table to be parsed from.
    """

    table_row_dict: Dict[str, str] = {"tbody": "tr", "table": "tr", "ul": "li"}
    """Finds out what is the table row tag."""
    row_column_tag_dict: Dict[str, str] = {"tr": "td", "li": "div"}
    """Finds out what is the table row column tag."""

    def __init__(self, html_table: Node) -> None:
        self.table = []
        table_body = html_table.css_first("tbody")
        if table_body:
            self.html_table = table_body
            self.header = html_table.css_first("thead")
        else:
            self.html_table = html_table
            self.header = None

        self.table_row_tag = self.table_row_dict[self.html_table.tag]
        self.row_column_tag = self.row_column_tag_dict[self.table_row_tag]

        self.a_elements = self.html_table.css("a")
        self.table_length = len(self.html_table.css(self.table_row_tag))
        self.row_length = len(
            self.html_table.css(
                f"{self.table_row_tag}:first-child > {self.row_column_tag}"
            )
        )

    def parse(self, fields: Union[List[str], Tuple[str, ...]]) -> None:
        """
        Parses HTML table to `self.table` (list of dicts) by calling given
        table parsing methods. Every parsed table row is dictionary with
        `fields` keys.

        :param fields: Table parsing methods of this class.
        :raises UnexpectedParsingError: When parsed field values aren't the
        same size as table length.

        :regular fields options:
            - rider_url
            - rider_name
            - team_url
            - team_name
            - stage_url
            - stage_name
            - race_url
            - race_name
            - nation_url
            - nation_name
            - age
            - nationality
            - time
            - bonus
            - profile_icon
            - season
            - rider_number

        :fields options for tables with a header:
            - rank
            - status
            - prev_rank
            - pcs_points
            - uci_points
            - points
            - class
            - first_places
            - second_places
            - third_places
            - distance
            - date
        """
        raw_table = []
        for _ in range(self.table_length):
            raw_table.append({})

        for field in fields:
            if field != "class":
                parsed_field_list = getattr(self, field)()
            # special case when field is called class
            else:
                parsed_field_list = getattr(self, "class_")()
            # field wasn't found in every table row, so isn't matching table
            # rows correctly
            if len(parsed_field_list) != self.table_length:
                message = f"Field '{field}' wasn't parsed correctly"
                raise UnexpectedParsingError(message)

            for row, parsed_value in zip(raw_table, parsed_field_list):
                row[field] = parsed_value

        # remove unwanted rows
        for row in raw_table:
            self.table.append(row)

        if "time" in fields and self.table:
            self._make_times_absolute()

    def extend_table(self, field_name: str, values: List[Any]):
        """
        Add given values to table.

        :param field_name: Name for column that's being added.
        :param values: Values which are being added.
        :raises ValueError: When values to add aren't the same length as table.
        """
        if len(values) != len(self.table) and self.table:
            raise ValueError(
                "Given values has to be the same length as table rows count"
            )
        if self.table:
            for row, value in zip(self.table, values):
                row[field_name] = value
        else:
            for value in values:
                self.table.append({field_name: value})

    def parse_extra_column(
        self,
        index_or_header_value: Union[int, str],
        func: Callable = int,
        separator: str = "",
        get_href: bool = False,
    ) -> List[Any]:
        """
        Parses values from given column.

        :param index_or_header_value: Either index of column to parse (negative
        indexing works too) or column name from table header (table has to have
        a header in that case).
        :param func: Function to call on parsed text value, defaults to int.
        :param separator: Separator for text attributes given to `func`.
        :param get_href: Whether to get href of each element, instead of text.
            Defaults to False.
        :return: List with parsed values.
        """
        if isinstance(index_or_header_value, str):
            index = self._get_column_index_from_header(index_or_header_value)
        else:
            index = index_or_header_value
        if index < 0:
            index = self.row_length + index
        elements = self.html_table.css(
            f"{self.table_row_tag} > {self.row_column_tag}:nth-child({index + 1})"
        )

        values = []
        for element in elements:
            text = element.text(separator=separator)
            if get_href:
                a_element = element.css_first("a")
                if a_element:
                    text = a_element.attributes["href"]
                else:
                    text = ""
            values.append(func(text))
        return values

    def rider_url(self) -> List[str]:
        rider_urls = self._filter_a_elements("rider", True)
        # Handle mismatch between table rows and rider elements
        if len(rider_urls) != self.table_length:
            # Pad with empty strings if we have fewer rider URLs than table rows
            while len(rider_urls) < self.table_length:
                rider_urls.append("")
            # Truncate if we have more rider URLs than table rows
            rider_urls = rider_urls[:self.table_length]
        return rider_urls

    def rider_name(self) -> List[str]:
        rider_names = self._filter_a_elements("rider", False)
        # Handle mismatch between table rows and rider elements
        if len(rider_names) != self.table_length:
            # Pad with empty strings if we have fewer rider names than table rows
            while len(rider_names) < self.table_length:
                rider_names.append("")
            # Truncate if we have more rider names than table rows
            rider_names = rider_names[:self.table_length]
        return rider_names

    def team_url(self) -> List[str]:
        try:
            return self.parse_extra_column("Team", str, get_href=True)
        except Exception:
            team_urls = self._filter_a_elements(
                "team", True, lambda x: True if x.text() != "view" else False
            )
            # Handle mismatch between table rows and team elements
            if len(team_urls) != self.table_length:
                # Pad with empty strings if we have fewer team URLs than table rows
                while len(team_urls) < self.table_length:
                    team_urls.append("")
                # Truncate if we have more team URLs than table rows
                team_urls = team_urls[:self.table_length]
            return team_urls

    def team_name(self) -> List[str]:
        try:
            return self.parse_extra_column("Team", str, get_href=False)
        except Exception:
            team_names = self._filter_a_elements(
                "team", False, lambda x: True if x.text() != "view" else False
            )
            # Handle mismatch between table rows and team elements
            if len(team_names) != self.table_length:
                # Pad with empty strings if we have fewer team names than table rows
                while len(team_names) < self.table_length:
                    team_names.append("")
                # Truncate if we have more team names than table rows
                team_names = team_names[:self.table_length]
            return team_names

    def stage_url(self) -> List[Optional[str]]:
        """
        One URL per row from the Stage column (handles both <a href> and
        <span data-url>, with a row‐wide fallback).
        """
        urls: List[Optional[str]] = []
        for row in self.html_table.css(self.table_row_tag):
            href: Optional[str] = None

            # try to target the "Stage" cell by index if there's a header
            try:
                idx = self._get_column_index_from_header("Stage")
            except Exception:
                idx = None

            if idx is not None:
                # nth-child is 1‐based
                cell = row.css_first(f"{self.row_column_tag}:nth-child({idx + 1})")
                if cell:
                    a = cell.css_first("a")
                    if a and a.attrs.get("href"):
                        href = a.attrs["href"]
                    else:
                        span = cell.css_first("span[data-url]")
                        if span:
                            href = span.attrs["data-url"]

            # fallback: any link‐like element in this row whose URL has "/stage"
            if not href:
                for elt in row.css("a, span[data-url]"):
                    candidate = elt.attrs.get("href") or elt.attrs.get("data-url")
                    if candidate and "/stage" in candidate:
                        href = candidate
                        break

            urls.append(href)
        return urls

    def stage_name(self) -> List[Optional[str]]:
        """
        One visible name per row from the Stage column. Matches whatever
        element gave stage_url().
        """
        names: List[Optional[str]] = []
        # reuse your new stage_url output
        url_list = self.stage_url()

        for row, url in zip(self.html_table.css(self.table_row_tag), url_list):
            if not url:
                names.append(None)
                continue

            # find the same element we grabbed the URL from
            selector = f"a[href='{url}'], span[data-url='{url}']"
            elt = row.css_first(selector)
            names.append(elt.text().strip() if elt else None)

        return names

    # def stage_url(self) -> List[str]:
    #     return self._filter_a_elements("race", True)

    # def stage_name(self) -> List[str]:
    #     return self._filter_a_elements("race", False)

    def nation_url(self) -> List[str]:
        nations_urls = self._filter_a_elements("nation", True)
        # return only urls to nation overview, not `pcs-season-wins`
        return [url for url in nations_urls if "pcs" not in url]

    def nation_name(self) -> List[str]:
        nations_texts = self._filter_a_elements("nation", False)
        # return text only when is not numeric, so doesn't represent number of
        # wins of the nation
        return [text for text in nations_texts if not text.isnumeric() and text != "-"]

    def climb_url(self) -> List[str]:
        """
        Parses all location elements hrefs from HTML. NOT only climbs, but for
        ease of use method is called climb name.

        :return: List of all climb URLs from table.
        """
        return self._filter_a_elements("location", True)

    def climb_name(self) -> List[str]:
        """
        Parses all location elements text values from HTML. NOT only climbs,
        but for ease of use method is called climb name.

        :return: List of all climb names from table.
        """
        return self._filter_a_elements("location", False)

    def race_url(self) -> List[str]:
        """
        Parses all race elements hrefs from HTML.

        :return: List of all race URLs from table.
        """
        return self._filter_a_elements("race", True)

    def race_name(self) -> List[str]:
        """
        Parses all race elements text values from HTML.

        :return: List of all race names from table.
        """
        return self._filter_a_elements("race", False)

    def age(self) -> List[Optional[int]]:
        ages_elements = self.html_table.css(".age")
        return [int(age_e.text()) if age_e.text() else None for age_e in ages_elements]

    def nationality(self) -> List[str]:
        flags_elements = self.html_table.css(".flag")
        flags = []
        for flag_e in flags_elements:
            if flag_e.attributes["class"] and " " in flag_e.attributes["class"]:
                flags.append(flag_e.attributes["class"].split(" ")[1].upper())
        return flags

    def time(self) -> List[Optional[str]]:
        times_elements = self.html_table.css(".time")
        times = []
        for time_e in times_elements:
            time_e_text = time_e.text(separator="\n")
            rider_time = None
            for time_line in time_e_text.split("\n"):
                if ",," not in time_line and "″" not in time_line:
                    rider_time = time_line
                    break
            if rider_time == "-" or rider_time is None:
                rider_time = None
            else:
                rider_time = format_time(rider_time.replace(" ", ""))
            times.append(rider_time)
        return times

    def bonus(self) -> List[str]:
        """
        Parses all bonuses elements from the table. If there aren't any returns
        where every row has bonus 0. Bonus is in classical time format `H:MM:SS`,
        or `-H:MM:SS` if penalty.

        :return: List of bonuses.
        """
        bonuses_elements = self.html_table.css(".bonis")
        bonuses = []
        time_pattern = re.compile(r"(-?\d+)(?::(\d{2}))?″")

        for bonus_e in bonuses_elements:
            bonus_text = bonus_e.text().replace("″", "").replace(" ", "")
            if not bonus_text:
                bonus = "0:00:00"
            else:
                match = time_pattern.match(bonus_text)
                if match:
                    sign, minutes, seconds = match.groups()
                    if seconds is None:
                        # It's just seconds
                        seconds = int(sign)
                        sign = "" if seconds >= 0 else "-"
                        seconds = abs(seconds)
                        minutes = 0
                    else:
                        minutes = int(sign)
                        seconds = int(seconds)
                        sign = "" if minutes >= 0 else "-"

                    hours = 0  # We assume there are no hours as per the format
                    bonus = f"{sign}{hours}:{minutes:02}:{seconds:02}"
                else:
                    bonus = "0:00:00"
            bonuses.append(bonus)
        if not bonuses:
            bonuses = ["0:00:00" for _ in range(self.table_length)]
        return bonuses

    def profile_icon(self) -> List[Literal["p0", "p1", "p2", "p3", "p4", "p5"]]:
        icons_elements = self.html_table.css(".icon.profile")
        profiles = []
        for icon_e in icons_elements:
            classes = icon_e.attributes["class"]
            if classes and len(classes.split(" ")) >= 3:
                profiles.append(classes.split(" ")[-1])
        return profiles

    def season(self) -> List[Optional[int]]:
        """
        Parses all season elements text values from table. If value is not
        numeric sesaon is set to None.

        :return: List of seasons.
        """
        seasons_elements = self.html_table.css(".season")
        seasons = []
        for season_e in seasons_elements:
            season_e_text = season_e.text()
            if season_e_text.isnumeric():
                seasons.append(int(season_e_text))
            else:
                seasons.append(None)
        return seasons

    def rider_number(self) -> List[Optional[int]]:
        bibs_elements = self.html_table.css(".bibs")
        return [
            int(bib_e.text()) if bib_e.text().isnumeric() else None
            for bib_e in bibs_elements
        ]

    def rank(self) -> List[Optional[int]]:
        possible_columns = ["Rnk", "pos", "Result", "#"]
        for column_name in possible_columns:
            try:
                return self.parse_extra_column(
                    column_name, lambda x: int(x) if x.isnumeric() else None
                )
            except ValueError:
                pass
        raise ValueError("Rank column wasn't found.")

    def status(self) -> List[Literal["DF", "DNF", "DNS", "OTL", "DSQ"]]:
        return self.parse_extra_column("Rnk", lambda x: "DF" if x.isnumeric() else x)

    def prev_rank(self) -> List[Optional[int]]:
        try:
            return self.parse_extra_column("Prev", lambda x: int(x) if x else None)
        except ValueError:
            return [None for _ in range(self.table_length)]

    def uci_points(self) -> List[Optional[float]]:
        try:
            def safe_parse_uci(x):
                if not x or x.strip() == "-":
                    return 0
                try:
                    # Handle European decimal format (comma as decimal separator)
                    cleaned = x.strip().replace(",", ".")
                    return float(cleaned)
                except ValueError:
                    return 0
            return self.parse_extra_column("UCI", safe_parse_uci)
        except ValueError:
            return [0 for _ in range(self.table_length)]

    def pcs_points(self) -> List[Optional[int]]:
        try:
            return self.parse_extra_column("Pnt", lambda x: int(x) if x else 0)
        except ValueError:
            try:
                return self.parse_extra_column(
                    "PCS points", lambda x: int(x) if x and x.isdigit() else 0
                )
            except ValueError:
                return [0 for _ in range(self.table_length)]

    def points(self) -> List[int]:
        def safe_parse_points(x):
            if not x or x.strip() == "-":
                return 0
            try:
                # Handle European decimal format (comma as decimal separator)
                cleaned = x.strip().replace(",", ".")
                return float(cleaned)
            except ValueError:
                return 0
        return self.parse_extra_column("Points", safe_parse_points)

    def class_(self) -> List[str]:
        """
        Parses classes from table with a header. Method is called class_ so
        it won't be interchanged with class keyword. In parsed table underscore
        is removed.

        :return: List of classes.
        """
        return self.parse_extra_column("Class", str)

    def first_places(self) -> List[Optional[int]]:
        return self.parse_extra_column("Wins", lambda x: int(x) if x.isnumeric() else 0)

    def second_places(self) -> List[Optional[int]]:
        return self.parse_extra_column("2nd", lambda x: int(x) if x.isnumeric() else 0)

    def third_places(self) -> List[Optional[int]]:
        return self.parse_extra_column("3rd", lambda x: int(x) if x.isnumeric() else 0)

    def distance(self) -> List[float]:
        def safe_parse_distance(x):
            if not x or x.strip() == "-":
                return None
            try:
                # Handle European decimal format (comma as decimal separator)
                cleaned = x.strip().replace(",", ".")
                return float(cleaned)
            except ValueError:
                return None
        return self.parse_extra_column("KMs", safe_parse_distance)

    def date(self) -> List[str]:
        return self.parse_extra_column("Date", str)

    def rename_field(self, field_name: str, new_field_name: str) -> None:
        """
        Renames field from table.

        :param field_name: Original field name.
        :param new_field_name: New name of original field.
        """
        for row in self.table:
            value = row.pop(field_name)
            row[new_field_name] = value

    def _get_column_index_from_header(self, column_name: str) -> int:
        if self.header is None:
            raise ExpectedParsingError(
                f"Can not parse '{column_name}' column without table header"
            )
        for i, column_name_e in enumerate(self.header.css("th")):
            if column_name.lower() in column_name_e.text().lower():
                return i
        raise ValueError(f"'{column_name}' column isn't in table header")

    def _make_times_absolute(self, time_field: str = "time") -> None:
        """
        Sums all times from table with first time from table. Table has to have
        at least 2 rows.

        :param time_field: Field which represents wanted time, defaults to
        `time`.
        """
        first_time = self.table[0][time_field]
        for i, row in enumerate(self.table[1:]):
            if row[time_field]:
                try:
                    row[time_field] = add_times(first_time, row["time"])
                # if time is in invalid format
                except Exception:
                    if i == 0:
                        row[time_field] = "0:00:00"
                    # set the same time as previous rider
                    else:
                        row[time_field] = self.table[1:][i - 1]["time"]

    def _filter_a_elements(
        self, keyword: str, get_href: bool, validator: Callable = lambda x: True
    ) -> List[str]:
        """
        Filters from all a elements these which has at the beggining of their
        href given keyword and gets their href or text.

        :param keyword: Keyword that element's href should have.
        :param get_href: Whether to return the href of a element, when False
        text is returned.
        :param validator: Function to call on every a element. When returns
        True element is added to result list, otherwise not.
        :return: List of all a elements texts or hrefs with given keyword.
        """
        filtered_values = []
        for a_element in self.a_elements:
            href = a_element.attributes["href"]
            if href and href.split("/")[0] == keyword and validator(a_element):
                if get_href:
                    filtered_values.append(href)
                else:
                    filtered_values.append(a_element.text())
        return filtered_values
