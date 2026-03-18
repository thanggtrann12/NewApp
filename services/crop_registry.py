import json
from models.crop import Crop

class CropRegistry:
    def __init__(self, path="data/crops.json"):
        # Accept both UTF-8 and UTF-8 BOM encoded JSON files.
        with open(path, "r", encoding="utf-8-sig") as f:
            self._crops = {
                c["id"]: Crop(**c)
                for c in json.load(f)
            }

    def get(self, crop_id):
        return self._crops.get(crop_id)

    def all(self):
        return list(self._crops.values())
