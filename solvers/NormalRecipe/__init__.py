from .. import Solver
from ...simulator import Craft, Manager

def AllowSkills(craft: Craft.Craft, craft_history: list = []) -> set:
    """
    得到当前可使用的技能
    :param craft: 生产配方
    :param craft_history: 预计技能列表
    :return: 可用技能
    """
    available_actions = set()
    forbidden_actions = set()
    if craft.craft_round == 1: # 添加首次工序预备技能
        available_actions.add("坚信")
        available_actions.add("闲静")
        return available_actions
    inner_quiet = 0 if "内静" not in craft.effects else craft.effects["内静"].param
    for buff in {"掌握", "俭约", "崇敬"}: # 添加buff组
        if buff not in craft.effects and craft.current_cp >= craft.get_skill_cost(buff) + 24:
            if buff == "掌握" and inner_quiet > 4: continue
            if buff == "俭约" and craft.current_cp >= craft.get_skill_cost("长期俭约") + 24: available_actions.add("长期俭约")
            if buff == "崇敬" and craft.current_quality < craft.recipe.max_quality: continue
            available_actions.add(buff)
    if "俭约" in craft.effects:forbidden_actions = forbidden_actions.union({"俭约", "长期俭约", "俭约加工", "俭约制作", "掌握"}) # 俭约下禁用技能
    if craft.current_quality < craft.recipe.max_quality and "比尔格的祝福" not in craft_history: # 加工未完成
        for buff in {"阔步", "改革"}: # 添加内静的buff组
            if buff == "阔步" and (inner_quiet < 6 or craft.current_quality == craft.recipe.max_quality): continue
            if buff == "改革" and craft.current_quality == craft.recipe.max_quality: continue
            available_actions.add(buff)
        if not craft.clone().use_skill("精密制作").is_finished(): available_actions.add("精密制作") # 添加精密制作进工序
        if "坚信" in craft.effects:
            _temp_actions = "" # 当前可进行的最高作业条技能
            for skill in "制作", "模范制作", "坯料制作":
                if not craft.clone().use_skill(skill).is_finished(): _temp_actions = skill
            if _temp_actions == "模范制作" and "俭约" not in craft.effects: available_actions.add("俭约制作")
            if _temp_actions:
                available_actions.add(_temp_actions)
                return available_actions
        available_actions = available_actions.union({"加工", "俭约加工", "坯料加工"}) # 初始化加工
        if craft.status.name in {"高品质", "最高品质"}: # 处理集中加工
            available_actions = available_actions.union({"集中作业", "集中加工"})
            forbidden_actions = forbidden_actions.union({"加工", "中级加工", "上级加工"})
        if inner_quiet >= 6: available_actions.add("比尔格的祝福") # 4层才可以用比尔格的祝福
        if inner_quiet >= 10: available_actions.add("工匠的神技") # 10层才可以用工匠的神技
        if "改革" in craft.effects:
            forbidden_actions = forbidden_actions.union({"改革", "掌握", "俭约", "长期俭约"})
            if craft.effects["改革"].param % 3 == 1: forbidden_actions.add("阔步")
            if craft.effects["改革"].param < 3: forbidden_actions.add("加工") # [改革-*-加工-加工-*]**禁用格式
        else:
            available_actions.add("改革")
            if inner_quiet >= 2: forbidden_actions = forbidden_actions.union({"加工", "中级加工", "上级加工", "工匠的神技", "俭约加工", "坯料加工", "比尔格的祝福"})
        if "加工" in craft.effects:
            available_actions.add("中级加工")
            forbidden_actions = forbidden_actions.union({"加工", "俭约加工", "坯料加工"})
        if "中级加工" in craft.effects:
            available_actions.add("上级加工")
            forbidden_actions = forbidden_actions.union({"加工", "俭约加工", "坯料加工"})
        if craft_history.count("加工"): forbidden_actions = forbidden_actions.union({"掌握", "俭约", "长期俭约"})
        if craft_history.count("坯料加工"): forbidden_actions = forbidden_actions.union({"掌握", "俭约", "长期俭约", "俭约加工"})
        if craft_history.count("俭约加工"): forbidden_actions = forbidden_actions.union({"掌握", "俭约", "长期俭约"})
        if "阔步" in craft.effects:
            forbidden_actions.add("工匠的神技")
            forbidden_actions.add("阔步")
            if craft.effects["阔步"].param == 1: forbidden_actions.add("改革") # 防止无效buff
        manipulation = craft.effects["掌握"].param if "掌握" in craft.effects else 0
        now_dur = craft.current_durability + 5 * manipulation
        if now_dur <= 40: forbidden_actions.add("加工") # 耐久不足
        if now_dur <= 15: forbidden_actions.add("俭约加工") # 耐久不足
        if now_dur <= 20: forbidden_actions = forbidden_actions.union({"加工", "集中加工", "观察"})
        if craft.current_durability <= (5 * int(bool(manipulation)) + 10 + craft.get_skill_durability("坯料加工")): forbidden_actions.add("坯料加工")
        if now_dur <= 10: forbidden_actions = forbidden_actions.union({"工匠的神技", "阔步", "改革"}) # 耐久不足
    else: # craft.current_quality == craft.recipe.max_quality
        _temp_actions = "制作" # 当前可进行的最高作业条技能
        for skill in "制作", "模范制作", "坯料制作":
            _temp_actions = skill
            if craft.clone().use_skill(skill).is_finished():
                break
        if craft.status.name in {"高品质", "最高品质"}: _temp_actions = "集中制作"
        if _temp_actions == "模范制作" and "俭约" not in craft.effects: available_actions.add("俭约制作")
        available_actions.add(_temp_actions)
    result_actions = set() # 得到可用技能组
    for action in available_actions:
        if action not in forbidden_actions and craft.get_skill_availability(action): result_actions.add(action)
    return result_actions

def process_usedtime(process: list=[]) -> int:
    """
    计算制作实际工次时间
    :param process: 预计技能列表
    :return: 实际工次时间
    """
    used_time = 0
    for temp_skill in process: used_time += 2 if temp_skill in ["俭约", "长期俭约", "崇敬", "阔步", "改革", "最终确认", "掌握"] else 3
    return used_time

def Generate_Routes(craft: Craft.Craft) -> tuple[Craft.Craft, list]:
    """
    计算结果
    :param craft: 生产配方
    :return: 预计结果, 预计技能列表
    """
    queue = [(craft, [])] # 待办事项
    routes = (craft, []) # 目前最佳项 第一个坑是数据，第二个是技能历史
    max_usetime = 999
    while queue:
        t_craft, t_history = queue.pop(0) # 获取一个待办事项
        if process_usedtime(t_history) + 3 >= max_usetime: continue # Timeout
        for action in AllowSkills(t_craft, t_history):
            tt_craft = t_craft.clone()
            tt_craft.use_skill(action)
            tt_craft.status = Manager.mStatus.DEFAULT_STATUS() # 重设球色
            if action == "比尔格的祝福" and tt_craft.current_quality < routes[0].current_quality: continue # Low Quality
            new_data = (tt_craft, t_history + [action]) # 模拟使用技能然后组成一个新的事项
            if tt_craft.is_finished():
                if tt_craft.current_quality > routes[0].current_quality: routes = new_data # 新生成的品质更好
                else:
                    if not bool(process_usedtime(routes[1])): routes = new_data # 初始化一个routes
                    if process_usedtime(new_data[1]) < process_usedtime(routes[1]): # 比较用时
                        routes = new_data
                        if new_data[0].current_quality == craft.recipe.max_quality: max_usetime = process_usedtime(new_data[1]) # 重设最佳时间
                continue
            queue.insert(0, new_data) # 将未进行完的事项从重新添加到队列
    return routes[0], routes[1]

class NormalRecipe(Solver): # 这个手法成立的前提是你能搓出来100%HQ

    @staticmethod
    def suitable(craft: Craft.Craft):
        return 80 < craft.recipe.recipe_row["RecipeLevelTable"]["ClassJobLevel"] <= 90 and not bool(craft.recipe.recipe_row["RecipeLevelTable"]["Stars"]) and craft.recipe.status_flag == 0b1111

    def __init__(self, craft: Craft.Craft, logger):
        super().__init__(craft, logger)
        self.queue = []
        self.is_first = True
        self.prev_skill = None

    def process(self, craft: Craft.Craft, prev_skill: str = None) -> str: # 返回技能名称
        remaining_quality = craft.recipe.max_quality - craft.current_quality
        if remaining_quality and remaining_quality <= craft.get_skill_quality("比尔格的祝福"): return ("比尔格的祝福") # 收尾
        if not bool(self.queue) or craft.status.name in {"高品质", "最高品质"} or prev_skill != self.prev_skill:
            routes, ans = Generate_Routes(craft)
            if ans: self.queue = ans
        self.prev_skill = self.queue.pop(0)
        return self.prev_skill