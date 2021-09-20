import ActionDecision
class plant_decision(ActionDecision.action_decision):
    def __init__(self, crop_types: list, coords: list) -> None:
        self.crop_types = crop_types
        self.coords = coords
        assert(len(crop_types) == len(coords))

    def __str__(self) -> str:
        res = f"plant "
        for i in range(len(self.crop_types)):
            res += self.crop_types[i]
            res += " "
            res += str(self.coords[i])
            res += " "
        res = res[:-1]
        return res