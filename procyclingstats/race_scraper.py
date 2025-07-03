from typing import Any, Dict, List

from .errors import ExpectedParsingError, UnexpectedParsingError
from .scraper import Scraper
from .table_parser import TableParser
from .utils import get_day_month, parse_select, parse_table_fields_args


class Race(Scraper):
    """
    Scraper for race overview HTML page.

    Usage:

    >>> from procyclingstats import Race
    >>> race = Race("race/tour-de-france/2022")
    >>> race.enddate()
    '2022-07-24'
    >>> race.parse()
    {
        'category': 'Men Elite',
        'edition': 109,
        'enddate': '2022-07-24',
        'is_one_day_race': False,
        ...
    }

    """

    def year(self) -> int:
        """
        Parse year when the race occured from HTML.

        :return: Year when the race occured.
        """
        year_element = self.html.css_first("span.hideIfMobile")
        if not year_element:
            raise ExpectedParsingError("Race year unavailable.")
        year_text = year_element.text().strip()
        # Extract just the year part (e.g., "2025" from "2025 \xa0 » \xa0 112th ")
        year_part = year_text.split()[0]
        return int(year_part)

    def name(self) -> str:
        """
        Parses display name from HTML.

        :return: Name of the race, e.g. ``Tour de France``.
        """
        # Try new structure first
        h1_element = self.html.css_first("h1")
        if h1_element:
            text = h1_element.text()
            if "»" in text:
                parts = text.split("»")
                if len(parts) > 1:
                    race_name = parts[1].strip()
                    # Remove edition number if present (e.g., "109th Tour de France" -> "Tour de France")
                    import re
                    race_name = re.sub(r'^\d+(?:st|nd|rd|th)\s+', '', race_name)
                    return race_name
        
        # Fallback to original selector
        display_name_html = self.html.css_first(".page-title > .main > h1")
        if not display_name_html:
            raise ExpectedParsingError("Race name unavailable.")
        return display_name_html.text()

    def is_one_day_race(self) -> bool:
        """
        Parses whether race is one day race from HTML.

        :return: Whether given race is one day race.
        """
        # Check for stage tables first
        stage_tables = self.html.css("table.basic")
        for table in stage_tables:
            table_text = table.text()
            if "Stage" in table_text and ("Date" in table_text or "Day" in table_text):
                return False
        
        # Fallback to original method
        titles = self.html.css("div > div > h3")
        titles = [] if not titles else titles
        for title_html in titles:
            if "Stages" in title_html.text():
                return False
        return True

    def nationality(self) -> str:
        """
        Parses race nationality from HTML.

        :return: 2 chars long country code in uppercase.
        """
        # Try new structure first - look for flag in page title area
        page_title = self.html.css_first(".page-title")
        if page_title:
            flag_elements = page_title.css("span[class*='flag']")
            for flag_elem in flag_elements:
                flag_class = flag_elem.attributes.get("class", "")
                # Look for flag classes like "flag fr w32" or "flag fr"
                parts = flag_class.split()
                if len(parts) >= 2 and parts[0] == "flag" and len(parts[1]) == 2:
                    return parts[1].upper()
        
        # Fallback to original method
        flag_elements = self.html.css("span[class*='flag']")
        for flag_elem in flag_elements:
            flag_class = flag_elem.attributes.get("class", "")
            # Look for flag classes like "flag fr" or "flag gb"
            parts = flag_class.split()
            if len(parts) >= 2 and parts[0] == "flag":
                return parts[1].upper()
        
        # Fallback to original selector
        nationality_html = self.html.css_first(".page-title > .main > span.flag")
        if not nationality_html:
            raise ExpectedParsingError("Race nationality unavailable.")
        flag_class = nationality_html.attributes["class"]
        return flag_class.split(" ")[1].upper()  # type: ignore

    def edition(self) -> int:
        """
        Parses race edition year from HTML.

        :return: Edition as int.
        """
        # Try new structure first - look for edition in H1
        h1_element = self.html.css_first("h1")
        if h1_element:
            text = h1_element.text()
            import re
            edition_match = re.search(r'(\d+)(?:st|nd|rd|th)', text)
            if edition_match:
                return int(edition_match.group(1))
        
        # Fallback to original selector
        edition_html = self.html.css_first(".page-title > .main > span + font")
        if edition_html is not None:
            return int(edition_html.text()[:-2])
        raise ExpectedParsingError("Race cancelled, edition unavailable.")

    def startdate(self) -> str:
        """
        Parses race startdate from HTML.

        :return: Startdate in ``YYYY-MM-DD`` format.
        """
        # Try new structure first - keyvalue list
        keyvalue_list = self.html.css_first('ul.list.keyvalueList')
        if keyvalue_list:
            for li in keyvalue_list.css('li'):
                title_elem = li.css_first('.title')
                value_elem = li.css_first('.value')
                if title_elem and value_elem:
                    title = title_elem.text().strip().rstrip(':')
                    if title == 'Startdate':
                        return value_elem.text().strip()
        
        # Fallback to original method
        startdate_html = self.html.css_first(".infolist > li > div:nth-child(2)")
        if not startdate_html:
            raise ExpectedParsingError("Race startdate unavailable (race may not have occurred yet).")
        return startdate_html.text()

    def enddate(self) -> str:
        """
        Parses race enddate from HTML.

        :return: Enddate in ``YYYY-MM-DD`` format.
        """
        # Try new structure first - keyvalue list
        keyvalue_list = self.html.css_first('ul.list.keyvalueList')
        if keyvalue_list:
            for li in keyvalue_list.css('li'):
                title_elem = li.css_first('.title')
                value_elem = li.css_first('.value')
                if title_elem and value_elem:
                    title = title_elem.text().strip().rstrip(':')
                    if title == 'Enddate':
                        return value_elem.text().strip()
        
        # Fallback to original method
        enddate_elements = self.html.css(".infolist > li > div:nth-child(2)")
        if len(enddate_elements) < 2:
            raise ExpectedParsingError("Race enddate unavailable (race may not have occurred yet).")
        enddate_html = enddate_elements[1]
        return enddate_html.text()

    def category(self) -> str:
        """
        Parses race category from HTML.

        :return: Race category e.g. ``Men Elite``.
        """
        # Try new structure first - keyvalue list
        keyvalue_list = self.html.css_first('ul.list.keyvalueList')
        if keyvalue_list:
            for li in keyvalue_list.css('li'):
                title_elem = li.css_first('.title')
                value_elem = li.css_first('.value')
                if title_elem and value_elem:
                    title = title_elem.text().strip().rstrip(':')
                    if title == 'Category':
                        return value_elem.text().strip()
        
        # Fallback to original method
        category_elements = self.html.css(".infolist > li > div:nth-child(2)")
        if len(category_elements) < 3:
            raise ExpectedParsingError("Race category unavailable (race may not have occurred yet).")
        category_html = category_elements[2]
        return category_html.text()

    def uci_tour(self) -> str:
        """
        Parses UCI Tour of the race from HTML.

        :return: UCI Tour of the race e.g. ``UCI Worldtour``.
        """
        # Try new structure first - keyvalue list
        keyvalue_list = self.html.css_first('ul.list.keyvalueList')
        if keyvalue_list:
            for li in keyvalue_list.css('li'):
                title_elem = li.css_first('.title')
                value_elem = li.css_first('.value')
                if title_elem and value_elem:
                    title = title_elem.text().strip().rstrip(':')
                    if title == 'UCI Tour':
                        return value_elem.text().strip()
        
        # Fallback to original method
        uci_tour_elements = self.html.css(".infolist > li > div:nth-child(2)")
        if len(uci_tour_elements) < 4:
            raise ExpectedParsingError("UCI Tour unavailable (race may not have occurred yet).")
        uci_tour_html = uci_tour_elements[3]
        return uci_tour_html.text()

    def prev_editions_select(self) -> List[Dict[str, str]]:
        """
        Parses previous race editions from HTML.

        :return: Parsed select menu represented as list of dicts with keys
            ``text`` and ``value``.
        """
        editions_select_html = self.html.css_first("form > select")
        return parse_select(editions_select_html)

    def stages(self, *args: str) -> List[Dict[str, Any]]:
        """
        Parses race stages from HTML (available only on stage races). When
        race is one day race, empty list is returned.

        :param args: Fields that should be contained in returned table. When
            no args are passed, all fields are parsed.

            - date: Date when the stage occured in ``MM-DD`` format.
            - profile_icon: Profile icon of the stage (p1, p2, ... p5).
            - stage_name: Name of the stage, e.g \
                ``Stage 2 | Roskilde - Nyborg``.
            - stage_url: URL of the stage, e.g. \
                ``race/tour-de-france/2022/stage-2``.

        :raises ValueError: When one of args is of invalid value.
        :return: Table with wanted fields.
        """
        available_fields = (
            "date",
            "profile_icon",
            "stage_name",
            "stage_url",
        )
        if self.is_one_day_race():
            return []

        fields = parse_table_fields_args(args, available_fields)
        
        # Find the stages table - look for table with Stage column
        stages_table_html = None
        for table in self.html.css("table.basic"):
            table_text = table.text()
            if "Stage" in table_text and ("Date" in table_text or "Day" in table_text):
                stages_table_html = table
                break
        
        if not stages_table_html:
            return []
        # remove rest day table rows
        for stage_e in stages_table_html.css("tbody > tr"):
            not_p_icon = not (
                stage_e.css_first(".icon.profile.p1")
                or stage_e.css_first(".icon.profile.p2")
                or stage_e.css_first(".icon.profile.p3")
                or stage_e.css_first(".icon.profile.p4")
                or stage_e.css_first(".icon.profile.p5")
            )
            if not_p_icon:
                stage_e.remove()

        # removes last row from stages table
        for row in stages_table_html.css("tr.sum"):
            row.remove()
        table_parser = TableParser(stages_table_html)
        casual_f_to_parse = [f for f in fields if f != "date"]
        table_parser.parse(casual_f_to_parse)

        # add stages dates to table if needed
        if "date" in fields:
            dates = table_parser.parse_extra_column(0, get_day_month)
            table_parser.extend_table("date", dates)
        return table_parser.table

    def stages_winners(self, *args) -> List[Dict[str, str]]:
        """
        Parses stages winners from HTML (available only on stage races). When
        race is one day race, empty list is returned.

        :param args: Fields that should be contained in returned table. When
            no args are passed, all fields are parsed.

            - stage_name: Stage name, e.g. ``Stage 2 (TTT)``.
            - rider_name: Winner's name.
            - rider_url: Wineer's URL.
            - nationality: Winner's nationality as 2 chars long country code.

        :raises ValueError: When one of args is of invalid value.
        :return: Table with wanted fields.
        """
        available_fields = (
            "stage_name",
            "rider_name",
            "rider_url",
            "nationality",
        )
        if self.is_one_day_race():
            return []

        fields = parse_table_fields_args(args, available_fields)
        orig_fields = fields
        
        # Find the winners table - look for table with Stage and Winner columns
        winners_html = None
        for table in self.html.css("table.basic"):
            table_text = table.text()
            if "Stage" in table_text and "Winner" in table_text:
                winners_html = table
                break
        
        if not winners_html:
            return []
        # remove rest day table rows
        for stage_e in winners_html.css("tbody > tr"):
            stage_name = stage_e.css_first("td").text()
            if not stage_name:
                stage_e.remove()
        table_parser = TableParser(winners_html)

        casual_f_to_parse = [f for f in fields if f != "stage_name"]
        try:
            table_parser.parse(casual_f_to_parse)
        # if nationalities don't fit stages winners
        except UnexpectedParsingError:
            casual_f_to_parse.remove("nationality")
            if "rider_url" not in args:
                casual_f_to_parse.append("rider_url")
            table_parser.parse(casual_f_to_parse)
            nats = table_parser.nationality()
            j = 0
            for i in range(len(table_parser.table)):
                if j < len(nats) and table_parser.table[i]["rider_url"].split("/")[1]:
                    table_parser.table[i]["nationality"] = nats[j]
                    j += 1
                else:
                    table_parser.table[i]["nationality"] = None

                if "rider_url" not in orig_fields:
                    table_parser.table[i].pop("rider_url")

        if "stage_name" in fields:
            stage_names = [
                val for val in table_parser.parse_extra_column(0, str) if val
            ]
            table_parser.extend_table("stage_name", stage_names)

        return table_parser.table

    def final_5k_stats(self, *args: str) -> List[Dict[str, Any]]:
        """
        Parses final 5k statistics from HTML (available only on stage races).
        When race is one day race, empty list is returned.

        :param args: Fields that should be contained in returned table. When
            no args are passed, all fields are parsed.

            - rank: Position in the ranking (1, 2, 3, ...).
            - profile_icon: Stage difficulty profile (p1, p2, p3, p4, p5).
            - stage_name: Stage name with destination.
            - stage_url: Relative URL to the stage.
            - vertical_meters: Vertical meters climbed in final 5k.
            - avg_gradient: Average gradient percentage in final 5k.

        :raises ValueError: When one of args is of invalid value.
        :return: Table with wanted fields.
        """
        available_fields = (
            "rank",
            "profile_icon", 
            "stage_name",
            "stage_url",
            "vertical_meters",
            "avg_gradient",
        )
        
        if self.is_one_day_race():
            return []

        fields = parse_table_fields_args(args, available_fields)
        
        # Create new scraper instance with final-5k URL
        from .scraper import Scraper
        final_5k_url = f"{self.relative_url()}/route/final-5k"
        final_5k_scraper = Scraper(final_5k_url)
        
        # Find the final 5k statistics table
        final_5k_table_html = None
        for table in final_5k_scraper.html.css("table.basic"):
            table_text = table.text()
            if "Vertical meters" in table_text and "Stage" in table_text:
                final_5k_table_html = table
                break
        
        if not final_5k_table_html:
            return []
        
        # Keep all rows including hidden ones (show more functionality)
        
        table_parser = TableParser(final_5k_table_html)
        
        # Parse the fields that don't need special handling
        casual_f_to_parse = [f for f in fields if f in ("stage_name", "stage_url")]
        table_parser.parse(casual_f_to_parse)
        
        # Add rank if needed
        if "rank" in fields:
            ranks = table_parser.parse_extra_column(0, str)
            table_parser.extend_table("rank", ranks)
        
        # Add profile icon if needed
        if "profile_icon" in fields:
            profile_icons = []
            for row in final_5k_table_html.css("tbody > tr"):
                icon_elem = row.css_first("span.icon.profile")
                if icon_elem:
                    icon_class = icon_elem.attributes.get("class")
                    if icon_class:
                        # Extract profile level (p1, p2, p3, p4, p5)
                        for part in icon_class.split():
                            if part.startswith("p") and part[1:].isdigit():
                                profile_icons.append(part)
                                break
                        else:
                            profile_icons.append(None)
                    else:
                        profile_icons.append(None)
                else:
                    profile_icons.append(None)
            table_parser.extend_table("profile_icon", profile_icons)
        
        # Add vertical meters if needed
        if "vertical_meters" in fields:
            vertical_meters = table_parser.parse_extra_column(3, str)
            table_parser.extend_table("vertical_meters", vertical_meters)
        
        # Add average gradient if needed
        if "avg_gradient" in fields:
            avg_gradient = table_parser.parse_extra_column(4, str)
            table_parser.extend_table("avg_gradient", avg_gradient)
        
        return table_parser.table
