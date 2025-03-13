class FortniteCosmetic:
    def __init__(self):
        self.cosmetic_id = ""
        self.name = ""
        self.backend_value = "AthenaCharacter"
        self.rarity_value = "common"
        self.small_icon = ""
        self.is_banner = False
        self.unlocked_styles = {}
        self.is_exclusive = False
        self.is_popular = False

    def to_dict(self):
        return {
            "cosmetic_id": self.cosmetic_id,
            "name": self.name,
            "backend_value": self.backend_value,
            "rarity_value": self.rarity_value,
            "small_icon": self.small_icon,
            "is_banner": self.is_banner,
            "unlocked_styles": self.unlocked_styles,
            "is_exclusive": self.is_exclusive,
            "is_popular": self.is_popular,
        }