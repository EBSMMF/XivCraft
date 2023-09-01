from FFxivPythonTrigger.logger import Logger
from ..simulator import Models, Craft

def usedtime(self, process: list=[]) -> float:
    """
    计算制作实际工次时间
    :param process: 预计技能列表
    :return: 实际工次时间
    """
    used_time = 0
    for temp_skill in process: used_time += 1.5 if temp_skill in ["俭约", "长期俭约", "崇敬", "阔步", "改革", "最终确认", "掌握"] else 2.5
    return used_time

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
