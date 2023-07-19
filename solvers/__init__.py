from FFxivPythonTrigger.logger import Logger
from ..simulator import Models, Craft

class Solver(object):
    recipe: Models.Recipe
    player: Models.Player
    logger: Logger

    def __init__(self, craft:Craft.Craft, logger: Logger):
        self.recipe = craft.recipe
        self.player = craft.player
        self.logger = logger

    @staticmethod
    def suitable(craft) -> bool:
        return False

    def process(self, craft: Craft.Craft, used_skill: Models.Skill = "") -> str:
        return "观察"
