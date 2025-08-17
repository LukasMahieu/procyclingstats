import requests
from typing import Any, Dict, List

from .errors import ExpectedParsingError
from .scraper import Scraper
from .table_parser import TableParser
from .utils import parse_table_fields_args


class StageFeatures(Scraper):
    """
    Scraper for stage features HTML page.
    If one_day_race, replace 'stage-{stage_number}' with 'result' in the URL.

    Usage:

    >>> from procyclingstats import StageFeatures
    >>> stage_features = StageFeatures("race/tour-de-france/2022/stage-1")
    >>> stage_features.features()
    {
        'Date': '19 May 2024',
        'Start time': '10:40',
        'Avg. speed winner': '-',
        'Race category': 'ME - Men Elite',
        'Distance': '222 km',
        'Points scale': 'GT.B.Stage',
        'UCI scale': 'UCI.WR.GT.B.Stage',
        'Parcours type': 'p4',
        '...'
    }
    >>> stage_features.parse()
    {
        'features': {
            'Date': '19 May 2024',
            'Start time': '10:40',
            'Avg. speed winner': '-',
            'Race category': 'ME - Men Elite',
            'Distance': '222 km',
            'Points scale': 'GT.B.Stage',
            'UCI scale': 'UCI.WR.GT.B.Stage',
            'Parcours type': 'p4',
            '...'
        }
    }
    """

    def features(self) -> Dict[str, Any]:
        """
        Parses stage's features from an unordered list in the HTML.
        """
        features = {}
        # Try new structure first
        list_items = self.html.css("ul.list.keyvalueList > li")
        
        # Fallback to old structure if new one not found
        if not list_items:
            list_items = self.html.css("ul.infolist > li")

        for item in list_items:
            # New structure: <div class="title"> and <div class="value">
            title_div = item.css_first("div.title")
            value_div = item.css_first("div.value")
            
            if title_div and value_div:
                key = title_div.text().strip().strip(":")
            else:
                # Fallback to old structure: first and second div
                divs = item.css("div")
                if len(divs) < 2:
                    continue
                key = divs[0].text().strip().strip(":")
                value_div = divs[1]
            
            # Special handling for Parcours type - extract icon class
            if key == "Parcours type":
                icon = value_div.css_first("span.icon.profile")
                if icon:
                    # Extract the profile class (e.g., "p4" from "icon profile p4")
                    class_attr = icon.attributes.get("class", "")
                    if class_attr:
                        classes = class_attr.split()
                        # Look for profile class (p1, p2, p3, p4, p5)
                        profile_classes = []
                        for cls in classes:
                            if cls.startswith("p") and len(cls) == 2 and cls[1].isdigit():
                                profile_classes.append(cls)
                        value = profile_classes[0] if profile_classes else ""
                    else:
                        value = ""
                else:
                    value = ""
                
                # Fallback: if no profile found, try to get it from the Race page
                if not value:
                    value = self._get_profile_from_race_page()
            else:
                value = value_div.text().strip()
            
            features[key] = value

        return features

    def _get_profile_from_race_page(self) -> str:
        """
        Fallback method to get profile icon from the main race page.
        Extracts race URL and stage number from current URL to fetch from Race scraper.
        """
        try:
            from .race_scraper import Race
            
            # Parse the current URL to extract race info
            # Expected format: race/tour-de-france/2025/stage-1
            url_parts = self.relative_url().split('/')
            if len(url_parts) >= 4 and url_parts[3].startswith('stage-'):
                # Extract stage number from "stage-1", "stage-2", etc.
                stage_part = url_parts[3]
                stage_number = int(stage_part.split('-')[1])
                
                # Build race URL: race/tour-de-france/2025
                race_url = '/'.join(url_parts[:3])
                
                # Get stages from Race page
                race = Race(race_url)
                stages = race.stages('profile_icon', 'stage_name')
                
                # Find the matching stage (stage numbers are 1-indexed)
                if 1 <= stage_number <= len(stages):
                    return stages[stage_number - 1].get('profile_icon', '')
            
            return ""
        except Exception:
            # If anything goes wrong, return empty string
            return ""

    def parse(self) -> Dict[str, Any]:
        """
        Parse all available data from HTML.

        :return: Parsed data.
        """
        return {"features": self.features()}

    def download_profile_image(self, output_path: str) -> bool:
        """
        Downloads the stage profile image.

        :param output_path: The path where the image will be saved.
        :return: True if the download is successful, False otherwise.
        """
        profile_img_html = self.html.css_first(
            "div.mt10 > span.table-cont > ul.list > li > div > a > img"
        )
        if not profile_img_html:
            return False

        img_url = profile_img_html.attributes["src"]
        full_img_url = f"{self.BASE_URL}{img_url}"  # Adjust base URL if needed

        response = requests.get(full_img_url)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
        return False
