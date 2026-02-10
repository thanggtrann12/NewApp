class Crop:
    def __init__(self, id, name, image, water):
        self.id = id
        self.name = name
        self.image = image
        self.water = water

    @property
    def suggest_text(self):
        return (
            f"{self.water['min_minutes']}–"
            f"{self.water['max_minutes']} min / day"
        )
