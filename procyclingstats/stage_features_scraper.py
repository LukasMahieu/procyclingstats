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
        list_items = self.html.css("ul.infolist > li")

        for item in list_items:
            key = item.css_first("div").text().strip().strip(":")
            value_div = item.css("div")[1]
            
            # Special handling for Parcours type - extract icon class
            if key == "Parcours type":
                icon = value_div.css_first("span.icon.profile")
                if icon:
                    # Extract the profile class (e.g., "p4" from "icon profile p4")
                    class_attr = icon.attributes.get("class", "")
                    if class_attr:
                        classes = class_attr.split()
                        profile_classes = [c for c in classes if c.startswith("p") and c != "profile"]
                        value = profile_classes[0] if profile_classes else ""
                    else:
                        value = ""
                else:
                    value = ""
            else:
                value = value_div.text().strip()
            
            features[key] = value

        return features

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
