import calendar
from typing import Any, Dict, List, Optional
import re
from procyclingstats.errors import UnexpectedParsingError, ExpectedParsingError

from .scraper import Scraper
from .table_parser import TableParser
from .utils import get_day_month, parse_table_fields_args


class Rider(Scraper):
    """
    Scraper for rider HTML page.

    To parse results from specific season, pass URL with the season, e.g.
    ``rider/tadej-pogacar/2021``, and use the ``Rider.results`` method. But it
    might be easier to just use the ``RiderResults`` scraping class for that
    purpose.

    Usage:

    >>> from procyclingstats import Rider
    >>> rider = Rider("rider/tadej-pogacar")
    >>> rider.birthdate()
    '1998-9-21'
    >>> rider.parse()
    {
        'birthdate': '1998-9-21',
        'height': 1.76,
        'name': 'Tadej  Pogačar',
        'nationality': 'SI',
        ...
    }
    """

    def birthdate(self) -> str:
        """
        Parses rider's birthdate from HTML.

        :return: birthday of the rider in ``YYYY-MM-DD`` format.
        """
        # Try new structure first
        info_box = self.html.css_first(".borderbox.left.w65")
        if info_box:
            text = info_box.text()
            import re
            birth_match = re.search(r'Date of birth:(\d{1,2})(?:st|nd|rd|th)([A-Za-z]+)(\d{4})', text)
            if birth_match:
                day, str_month, year = birth_match.groups()
                month = list(calendar.month_name).index(str_month)
                return f"{year}-{month}-{day}"
        
        # Fallback to original structure
        general_info_html = self.html.css_first(".rdr-info-cont")
        if not general_info_html:
            raise ExpectedParsingError("Rider birthdate unavailable.")
        bd_string = general_info_html.text(separator=" ", deep=False)
        bd_list = [item for item in bd_string.split(" ") if item][:3]
        [day, str_month, year] = bd_list
        month = list(calendar.month_name).index(str_month)
        return f"{year}-{month}-{day}"

    def place_of_birth(self) -> str:
        """
        Parses rider's place of birth from HTML

        :return: rider's place of birth (town only).
        """
        # Try new structure first
        info_box = self.html.css_first(".borderbox.left.w65")
        if info_box:
            text = info_box.text()
            import re
            place_match = re.search(r'Place of birth:\s*([\w\s,]+)', text)
            if place_match:
                full_match = place_match.group(1)
                # Get just the first part before newlines or other content
                place_parts = full_match.split('\n')[0].strip()
                return place_parts
        
        # Fallback to original structure
        # normal layout
        try:
            place_of_birth_html = self.html.css_first(
                ".rdr-info-cont > span > span > a"
            )
            return place_of_birth_html.text()
        # special layout
        except AttributeError:
            try:
                place_of_birth_html = self.html.css_first(
                    ".rdr-info-cont > span > span > span > a"
                )
                return place_of_birth_html.text()
            except AttributeError:
                return ""

    def name(self) -> str:
        """
        Parses rider's name from HTML.

        :return: Rider's name.
        """
        # Try new structure first
        h1_element = self.html.css_first("h1")
        if h1_element:
            return h1_element.text()
        
        # Fallback to original selector
        name_element = self.html.css_first(".page-title > .main > h1")
        if not name_element:
            raise ExpectedParsingError("Rider name unavailable.")
        return name_element.text()

    def weight(self) -> float:
        """
        Parses rider's current weight from HTML.

        :return: Rider's weigth in kilograms.
        """
        # Try new structure first
        info_box = self.html.css_first(".borderbox.left.w65")
        if info_box:
            text = info_box.text()
            import re
            weight_match = re.search(r'Weight:(\d+)kg', text)
            if weight_match:
                return float(weight_match.group(1))
        
        # Fallback to original structure
        # normal layout
        try:
            weight_html = self.html.css(".rdr-info-cont > span")[1]
            return float(weight_html.text().split(" ")[1])
        # special layout
        except (AttributeError, IndexError):
            try:
                weight_html = self.html.css(".rdr-info-cont > span > span")[1]
                return float(weight_html.text().split(" ")[1])
            except (AttributeError, IndexError):
                return 0.0

    def height(self) -> float:
        """
        Parses rider's height from HTML.

        :return: Rider's height in meters.
        """
        # Try new structure first
        info_box = self.html.css_first(".borderbox.left.w65")
        if info_box:
            text = info_box.text()
            import re
            height_match = re.search(r'Height:(\d+\.\d+)m', text)
            if height_match:
                return float(height_match.group(1))
        
        # Fallback to original structure
        # normal layout
        try:
            height_html = self.html.css_first(".rdr-info-cont > span > span")
            return float(height_html.text().split(" ")[1])
        # special layout
        except (AttributeError, IndexError):
            try:
                height_html = self.html.css_first(".rdr-info-cont > span > span > span")
                return float(height_html.text().split(" ")[1])
            except (AttributeError, IndexError):
                return 0.0

    def nationality(self) -> str:
        """
        Parses rider's nationality from HTML.

        :return: Rider's current nationality as 2 chars long country code in
            uppercase.
        """
        # Try new structure first - look for flag elements in rider info
        info_box = self.html.css_first(".borderbox.left.w65")
        if info_box:
            flag_elements = info_box.css("span[class*='flag']")
            for flag_elem in flag_elements:
                flag_class = flag_elem.attributes.get("class", "")
                # Look for flag classes like "flag si" or "flag gb"
                parts = flag_class.split()
                if len(parts) >= 2 and parts[0] == "flag":
                    return parts[1].upper()
        
        # Fallback to original structure
        # normal layout
        nationality_html = self.html.css_first(".rdr-info-cont > .flag")
        if nationality_html is None:
            # special layout
            nationality_html = self.html.css_first(".rdr-info-cont > span > span")
        if not nationality_html:
            raise ExpectedParsingError("Rider nationality unavailable.")
        flag_class = nationality_html.attributes["class"]
        return flag_class.split(" ")[-1].upper()  # type:ignore

    def image_url(self) -> Optional[str]:
        """
        Parses URL of rider's PCS image.

        :return: Relative URL of rider's image. None if image is not available.
        """
        # Try new structure first - look for rider images
        imgs = self.html.css("img")
        for img in imgs:
            src = img.attributes.get("src", "")
            if src and "riders/" in src:
                return src
        
        # Fallback to original selector
        image_html = self.html.css_first("div.rdr-img-cont > a > img")
        if not image_html:
            return None
        return image_html.attributes["src"]

    # def teams_history(self, *args: str) -> List[Dict[str, Any]]:
    #     """
    #     Parses rider's team history throughout career.

    #     :param args: Fields that should be contained in returned table. When
    #         no args are passed, all fields are parsed.

    #         - team_name:
    #         - team_url:
    #         - season:
    #         - class: Team's class, e.g. ``WT``.
    #         - since: First day for rider in current season in the team in
    #           ``MM-DD`` format, most of the time ``01-01``.
    #         - until: Last day for rider in current season in the team in
    #           ``MM-DD`` format, most of the time ``12-31``.

    #     :raises ValueError: When one of args is of invalid value.
    #     :return: Table with wanted fields.
    #     """
    #     available_fields = (
    #         "season",
    #         "since",
    #         "until",
    #         "team_name",
    #         "team_url",
    #         "class",
    #     )
    #     fields = parse_table_fields_args(args, available_fields)
    #     seasons_html_table = self.html.css_first("ul.list.rdr-teams")
    #     table_parser = TableParser(seasons_html_table)
    #     casual_fields = [f for f in fields if f in ("season", "team_name", "team_url")]
    #     if casual_fields:
    #         table_parser.parse(casual_fields)
    #     # add classes for row validity checking
    #     classes = table_parser.parse_extra_column(
    #         2,
    #         lambda x: x.replace("(", "").replace(")", "").replace(" ", "")
    #         if x and "retired" not in x.lower()
    #         else None,
    #     )
    #     table_parser.extend_table("class", classes)
    #     if "since" in fields:
    #         until_dates = table_parser.parse_extra_column(
    #             -2, lambda x: get_day_month(x) if "as from" in x else "01-01"
    #         )
    #         table_parser.extend_table("since", until_dates)
    #     if "until" in fields:
    #         until_dates = table_parser.parse_extra_column(
    #             -2, lambda x: get_day_month(x) if "until" in x else "12-31"
    #         )
    #         table_parser.extend_table("until", until_dates)

    #     table = [row for row in table_parser.table if row["class"]]
    #     # remove class field if isn't needed
    #     if "class" not in fields:
    #         for row in table:
    #             row.pop("class")
    #     return table

    def teams_history(self, *args: str) -> List[Dict[str, Any]]:
        """
        Parses rider's team history. Manually extracts season, team_name,
        team_url, then reuses TableParser for class/since/until.
        """
        available_fields = (
            "season",
            "since",
            "until",
            "team_name",
            "team_url",
            "class",
        )
        fields = parse_table_fields_args(args, available_fields)

        # 1) find the UL list (old selector + fallback)
        seasons_html_list = self.html.css_first("ul.list.rdr-teams")
        if seasons_html_list is None:
            for ul in self.html.css("ul"):
                first_li = ul.css_first("li")
                if first_li and re.match(r"^\s*\d{4}\s*$", first_li.text()):
                    seasons_html_list = ul
                    break
        if seasons_html_list is None:
            raise UnexpectedParsingError(
                "Could not find the Teams history list on this page."
            )

        # 2) set up parser on that <ul>
        parser = TableParser(seasons_html_list)

        # 3) MANUAL pull of season / team_name / team_url
        seasons = parser.parse_extra_column(0, lambda x: x.strip())
        team_names = parser.parse_extra_column(1, lambda x: x.strip())
        team_urls = parser.parse_extra_column(1, lambda x: x.strip(), get_href=True)

        # 4) build the initial table
        parser.table = [
            {"season": s, "team_name": tn, "team_url": tu}
            for s, tn, tu in zip(seasons, team_names, team_urls)
        ]

        # 5) now apply your old “extra” logic:
        #    class
        classes = parser.parse_extra_column(
            2,
            lambda x: x.replace("(", "").replace(")", "").replace(" ", "")
            if x and "retired" not in x.lower()
            else None,
        )
        parser.extend_table("class", classes)

        #    since
        if "since" in fields:
            since_dates = parser.parse_extra_column(
                -2, lambda x: get_day_month(x) if "as from" in x else "01-01"
            )
            parser.extend_table("since", since_dates)

        #    until
        if "until" in fields:
            until_dates = parser.parse_extra_column(
                -2, lambda x: get_day_month(x) if "until" in x else "12-31"
            )
            parser.extend_table("until", until_dates)

        # 6) filter out retired rows and drop “class” if not requested
        table = [row for row in parser.table if row.get("class")]
        if "class" not in fields:
            for row in table:
                row.pop("class", None)

        return table

    def points_per_season_history(self, *args: str) -> List[Dict[str, Any]]:
        """
        Parses rider's points per season history.

        :param args: Fields that should be contained in returned table. When
            no args are passed, all fields are parsed.

            - season:
            - points: PCS points gained throughout the season.
            - rank: PCS ranking position after the season.

        :raises ValueError: When one of args is of invalid value.
        :return: Table with wanted fields.
        """
        available_fields = ("season", "points", "rank")
        fields = parse_table_fields_args(args, available_fields)
        points_table_html = self.html.css_first("table.rdr-season-stats")
        if not points_table_html:
            return []
        table_parser = TableParser(points_table_html)
        table_parser.parse(fields)
        return table_parser.table

    def points_per_speciality(self) -> Dict[str, int]:
        """
        Parses rider's points per specialty from HTML.

        :return: Dict mapping rider's specialties and points gained.
            Dict keys: one_day_races, gc, time_trial, sprint, climber, hills
        """
        specialty_html = self.html.css(".pps > ul > li > .pnt")
        pnts = [int(e.text()) for e in specialty_html]
        keys = ["one_day_races", "gc", "time_trial", "sprint", "climber", "hills"]
        return dict(zip(keys, pnts))

    def season_results(self, *args: str) -> List[Dict[str, Any]]:
        """
        Parses rider's results from season specified in URL. If no URL is
        specified, results from current season are parsed.

        :param args: Fields that should be contained in returned table. When
            no args are passed, all fields are parsed.

            - result: Rider's result. None if not rated.
            - gc_position: GC position after the stage. None if the race is
                one day race, after last stage, or if stage is points
                classification etc...
            - stage_url:
            - stage_name:
            - distance: Distance of the stage, if is given. Otherwise None.
            - date: Date of the stage in YYYY-MM-DD format. None if the stage
                is GC, points classification etc...
            - pcs_points:
            - uci_points:

        :raises ValueError: When one of args is of invalid value.
        :return: Table with wanted fields.
        """
        available_fields = (
            "result",
            "gc_position",
            "stage_url",
            "stage_name",
            "distance",
            "date",
            "pcs_points",
            "uci_points",
        )
        fields = parse_table_fields_args(args, available_fields)
        casual_fields = ["stage_url", "stage_name"]
        for field in list(casual_fields):
            if field not in fields:
                casual_fields.remove(field)

        results_html = self.html.css_first("#resultsCont > table.rdrResults")
        if not results_html:
            return []
        for tr in results_html.css("tbody > tr"):
            if not tr.css("td")[1].text():
                tr.remove()

        table_parser = TableParser(results_html)
        if casual_fields:
            table_parser.parse(casual_fields)
        if "date" in fields:
            try:
                year = self.html.css_first(".rdrSeasonNav > li.cur > a").text()
                dates = table_parser.parse_extra_column("Date", str)
                for i, date in enumerate(dates):
                    if date:
                        splitted_date = date.split(".")
                        dates[i] = f"{year}-{splitted_date[1]}-{splitted_date[0]}"
                    else:
                        dates[i] = None
                table_parser.extend_table("date", dates)
            except AttributeError:
                pass
        if "result" in fields:
            results = table_parser.parse_extra_column(
                "Result", lambda x: int(x) if x.isnumeric() else None
            )
            table_parser.extend_table("result", results)
        if "gc_position" in fields:
            gc_positions = table_parser.parse_extra_column(
                2, lambda x: int(x) if x.isnumeric() else None
            )
            table_parser.extend_table("gc_position", gc_positions)
        if "distance" in fields:

            def _parse_distance(text: str) -> Optional[float]:
                tokens = text.strip().split()
                if not tokens:
                    return None
                # take the last token (actual distance, or the only one if no shortening)
                val = tokens[-1]
                try:
                    return float(val)
                except ValueError:
                    return None

            distances = table_parser.parse_extra_column("Distance", _parse_distance)
            table_parser.extend_table("distance", distances)
        if "pcs_points" in fields:
            pcs_points = table_parser.parse_extra_column(
                "PCS", lambda x: float(x) if x.isnumeric() else 0
            )
            table_parser.extend_table("pcs_points", pcs_points)
        if "uci_points" in fields:
            uci_points = table_parser.parse_extra_column(
                "UCI", lambda x: float(x) if x.isnumeric() else 0
            )
            table_parser.extend_table("uci_points", uci_points)

        return table_parser.table
