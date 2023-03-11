from .. import Solver
from ...simulator import Craft, Manager

def AllowSkills(craft: Craft.Craft, craft_history: list = []) -> set:
    """
    得到当前可使用的作业技能
    :param craft: 生产配方
    :param craft_history: 历史路线
    :return: 可用技能
    """
    available_actions = set()
    forbidden_actions = set()
    if craft.current_cp <= 7: available_actions.add("制作")
    else: available_actions.add("模范制作")
    if craft.status.name in {"高品质", "最高品质"}:
        available_actions.add("集中制作")
        forbidden_actions.add("坯料制作")
    available_actions.add("坯料制作")
    if "俭约" in craft.effects:
        forbidden_actions = forbidden_actions.union({"俭约", "长期俭约", "俭约制作"})
        available_actions.add("模范制作")
    else: available_actions = available_actions.union({"俭约", "长期俭约", "俭约制作"})
    if "掌握" in craft.effects: forbidden_actions.add("掌握")
    else: available_actions.add("掌握")
    if "崇敬" in craft.effects: forbidden_actions.add("崇敬")
    else: available_actions.add("崇敬")
    if craft_history.count("坯料制作"): forbidden_actions.add("崇敬")
    if craft_history.count("模范制作") or craft_history.count("俭约制作"): forbidden_actions = forbidden_actions.union({"崇敬", "坯料制作"})
    if craft_history.count("制作"): forbidden_actions = forbidden_actions.union({"坯料制作", "模范制作", "俭约制作", "崇敬"})
    result_actions = set()
    for action in available_actions:
        if action not in forbidden_actions and craft.get_skill_availability(action): result_actions.add(action)
    return result_actions

def process_usedtime(process: list) -> int:
    """
    计算制作实际工次时间
    :param process: 预计技能列表
    :return: 实际工次时间
    """
    used_time = 0
    for temp_skill in process:
        if temp_skill in ["俭约", "长期俭约", "崇敬", "阔步", "改革", "最终确认", "掌握"]: used_time += 2
        else: used_time += 3
    return used_time

def Generate_Routes(craft: Craft.Craft) -> tuple[Craft.Craft, list]:
    """
    根据当前生产配方计算路径
    :param craft: 生产配方
    :return: 预计结果, 预计技能列表
    """    
    queue = [(craft, [])]
    routes = (craft, [])
    max_usetime = 999
    while queue: 
        t_craft, t_history = queue.pop(0)
        if process_usedtime(t_history) > max_usetime - 3: continue # Timeout
        for action in AllowSkills(t_craft, t_history):
            tt_craft = t_craft.clone()
            tt_craft.use_skill(action)
            tt_craft.status = Manager.mStatus.DEFAULT_STATUS() # 重设球色
            new_data = (tt_craft, t_history + [action]) # 模拟使用技能然后组成一个新的事项
            if process_usedtime(new_data[1]) > max_usetime: continue # Timeout
            if tt_craft.is_finished():
                if not bool(process_usedtime(routes[1])): routes = new_data # 初始化一个routes
                if process_usedtime(new_data[1]) < process_usedtime(routes[1]):
                    routes = new_data
                    max_usetime = process_usedtime(new_data[1]) # 重设最佳时间
                continue
            queue.insert(0, new_data) # 将未进行完的事项从重新添加到队列
    return routes[0], routes[1]

class JustDoIt(Solver):
    
    @staticmethod
    def suitable(craft):
        return craft.player.level >= 80 and craft.recipe.recipe_row["RecipeLevelTable"]["ClassJobLevel"]  <= craft.player.level - 10 and craft.recipe.status_flag == 0b1111

    def __init__(self, craft, logger):
        super().__init__(craft, logger)
        self.queue = []
        self.prev_skill = None

    def process(self, craft, prev_skill = None) -> str:
        if prev_skill is None and craft.recipe.recipe_row["CanHq"]:
            return '工匠的神速技巧'
        else:
            if not bool(self.queue) or craft.status.name in {"高品质", "最高品质"} or prev_skill != self.prev_skill:
                routes, ans = Generate_Routes(craft)
                if ans: self.queue = ans
            self.prev_skill = self.queue.pop(0)
            return self.prev_skill
