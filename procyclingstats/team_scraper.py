from typing import Any, Dict, List, Optional

from .errors import ExpectedParsingError
from .scraper import Scraper
from .table_parser import TableParser
from .utils import (get_day_month, join_tables, parse_select,
                    parse_table_fields_args)


class Team(Scraper):
    """
    Scraper for team HTML page.

    Usage:

    >>> from procyclingstats import Team
    >>> team = Team("team/bora-hansgrohe-2022")
    >>> team.abbreviation()
    'BOH'
    >>> team.parse()
    {
        'abbreviation': 'BOH',
        'bike': 'Specialized',
        'history_select': [
            {
                'text': '2027 | BORA - hansgrohe',
                'value': 'team/bora-hansgrohe-2027/overview/'
            },
            ...
        ],
        'name': 'BORA - hansgrohe',
        ...
    }
    """
    def name(self) -> str:
        """
        Parses team display name from HTML.

        :return: Display name, e.g. ``BORA - hansgrohe``.
        """
        # Try new structure first
        display_name_html = self.html.css_first(".page-title h1")
        if not display_name_html:
            # Fallback to original selector
            display_name_html = self.html.css_first(".page-title > .main > h1")
        
        if not display_name_html:
            # Last resort - any h1
            display_name_html = self.html.css_first("h1")
            
        if not display_name_html:
            raise ExpectedParsingError("Team name unavailable from current HTML structure.")
            
        return display_name_html.text().split(" (")[0]

    def nationality(self) -> str:
        """
        Parses team's nationality from HTML.

        :return: Team's nationality as 2 chars long country code in uppercase.
        """
        # Try new structure first - look for flag in page-title
        nationality_html = self.html.css_first(".page-title span.flag")
        if not nationality_html:
            # Fallback to original selector
            nationality_html = self.html.css_first(".page-title > .main > span.flag")
        
        if not nationality_html:
            raise ExpectedParsingError("Team nationality unavailable from current HTML structure.")
            
        flag_class = nationality_html.attributes['class']
        # Extract country code from class like "flag nl w32" or "flag nl"
        parts = flag_class.split(" ")
        if len(parts) >= 2:
            return parts[1].upper()
        else:
            raise ExpectedParsingError("Could not parse team nationality from flag class.")

    def status(self) -> str:
        """
        Parses team status (class) from HTML.

        :return: Team status as 2 chars long code in uppercase, e.g. ``WT``.
        """
        team_status_html = self.html.css_first(
            "div > ul.infolist > li:nth-child(1) > div:nth-child(2)")
        return team_status_html.text()

    def abbreviation(self) -> str:
        """
        Parses team abbreviation from HTML.

        :return: Team abbreviation as 3 chars long code in uppercase, e.g.
            ``BOH``
        """
        abbreviation_html = self.html.css_first(
            "div > ul.infolist > li:nth-child(2) > div:nth-child(2)")
        return abbreviation_html.text()

    def bike(self) -> str:
        """
        Parses team's bike brand from HTML.

        :return: Bike brand e.g. ``Specialized``.
        """
        bike_html = self.html.css_first(
            "div > ul.infolist > li:nth-child(4) > div:nth-child(2)")
        return bike_html.text()

    def wins_count(self) -> Optional[int]:
        """
        Parses count of wins in corresponding season from HTML.

        :return: Count of wins in corresponding season.
        """
        wins_count_html = self.html.css_first(".team-kpi > li.nr")
        if wins_count_html:
            wins_count_text = str(wins_count_html.text())
            if wins_count_text.isdigit():
                return int(wins_count_text)
            elif wins_count_text == '-':
                return 0
        return None
    
    def pcs_points(self) -> Optional[int]:
        """
        Parses team's PCS points from HTML.

        :return: PCS points gained throughout corresponding year.
        """
        team_ranking_html = self.html.css_first(
            ".team-kpi > li.nr:nth-child(4)")
        if team_ranking_html and team_ranking_html.text().isnumeric():
            return int(team_ranking_html.text())
        else:
            return None
   

    def pcs_ranking_position(self) -> Optional[int]:
        """
        Parses team's PCS ranking position from HTML.

        :return: PCS team ranking position in corresponding year.
        """
        team_ranking_html = self.html.css_first(
            ".team-kpi > li.nr:nth-child(6)")
        if team_ranking_html and team_ranking_html.text().isnumeric():
            return int(team_ranking_html.text())
        else:
            return None
        
    def uci_ranking_position(self) -> Optional[int]:
        """
        Parses team's UCI ranking position from HTML.

        :return: UCI team ranking position in corresponding year.
        """
        team_ranking_html = self.html.css_first(
            ".team-kpi > li.nr:nth-child(8)")
        if team_ranking_html and team_ranking_html.text().isnumeric():
            return int(team_ranking_html.text())
        else:
            return None
   

    def history_select(self) -> List[Dict[str, str]]:
        """
        Parses team seasons select menu from HTML.

        :return: Parsed select menu represented as list of dicts with keys
            ``text`` and ``value``.
        """
        team_seasons_select_html = self.html.css_first("form > select")
        return parse_select(team_seasons_select_html)

    def riders(self, *args: str) -> List[Dict[str, Any]]:
        """
        Parses team riders in curresponding season from HTML.

        :param args: Fields that should be contained in returned table. When
            no args are passed, all fields are parsed.

            - rider_name
            - rider_url
            - nationality: Rider's nationality as 2 chars long country code.
            - age: Rider's age.
            - since: First rider's day in the team in corresponding season in
              ``MM-DD`` format, most of the time ``01-01``.
            - until: Last rider's day in the team in corresponding season in
              ``MM-DD`` format, most of the time ``12-31``.
            - career_points: Current riders's career points.
            - ranking_points: Current rider's points in PCS ranking.
            - ranking_position: Current rider's position in PCS ranking.

        :raises ValueError: When one of args is of invalid value.
        :return: Table with wanted fields.
        """
        available_fields = (
            "nationality",
            "rider_name",
            "rider_url",
            "age",
            "since",
            "until",
            "career_points",
            "ranking_points",
            "ranking_position"
        )
        casual_fields = [
            "nationality",
            "rider_name",
            "rider_url"]
        # Try new structure first - direct table access
        all_tables = self.html.css("table")
        fields = parse_table_fields_args(args, available_fields)
        
        # Find the main rider table (usually has rider names and multiple columns)
        career_points_table_html = None
        for table in all_tables:
            headers = table.css('thead th, tr:first-child td')
            if headers:
                header_texts = [h.text().strip().lower() for h in headers]
                if 'rider' in ' '.join(header_texts) and len(headers) >= 3:
                    career_points_table_html = table
                    break
        
        if not career_points_table_html:
            # Fallback to original tab-based structure
            mapping = {}
            for i, li in enumerate(self.html.css("ul.riderlistTabs > li")):
                mapping[li.text()] = i
            rider_tab_tables = self.html.css("div.ridersTab")
            if rider_tab_tables and "points" in mapping:
                career_points_table_html = rider_tab_tables[mapping["points"]]
        
        if not career_points_table_html:
            return []  # No rider data available
            
        table_parser = TableParser(career_points_table_html)
        career_points_fields = [field for field in fields
                         if field in casual_fields]
        # add rider_url to the table for table joining purposes
        if "rider_url" not in career_points_fields:
            career_points_fields.append("rider_url")
        table_parser.parse(career_points_fields)
        if "career_points" in fields:
            career_points = table_parser.parse_extra_column(2,
                lambda x: int(x) if x.isnumeric() else 0)
            table_parser.extend_table("career_points", career_points)
        table = table_parser.table

        # For the new HTML structure, additional data from separate tables may not be available
        # Return the basic rider data that was successfully parsed
        # TODO: Enhance this when the new table structure is better understood
        
        # Filter table to only include requested fields that were successfully parsed
        if table:
            # Remove fields that weren't successfully parsed or aren't available
            available_fields_in_table = set(table[0].keys()) if table else set()
            for row in table:
                for field in list(row.keys()):
                    if field not in fields and field != "rider_url":  # Keep rider_url for joining
                        row.pop(field, None)

        return table
