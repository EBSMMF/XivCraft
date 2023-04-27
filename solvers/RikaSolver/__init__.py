from .. import Solver
from ...simulator import Craft, Manager

default_process_round = 8

durReq = 1  # 留一个作业耐久
cpReq = 12  # 留一个作业cp
SpecialStatus = {"高品质", "最高品质"} 

def get_retention(craft: Craft.Craft):
    """
    生成保留数据
    :param craft: 生产配方
    """
    global cpReq
    remaining_prog = (craft.recipe.max_difficulty - craft.clone().current_progress) / craft.craft_data.base_process
    if remaining_prog >= 1.8: cpReq = 12
    elif remaining_prog >= 1.2: cpReq = 7
    else: cpReq = 0

def Get_Process_AllowSkills(craft: Craft.Craft, craft_history: list = []) -> set:
    """
    得到当前可使用的作业技能
    :param craft: 生产配方
    :param craft_history: 预计技能列表
    :return: 可用作业技能
    """
    available_actions = {"模范制作", "俭约制作", "制作", "精密制作"}
    forbidden_actions = set()
    if craft.craft_round == 4:
        available_actions.add("长期俭约")
        available_actions.add("俭约")
    if "俭约" in craft.effects or "坚信" in craft.effects:
        available_actions.add("坯料制作")
        forbidden_actions.add("俭约制作")
    if "坚信" in craft.effects:
        forbidden_actions = forbidden_actions.union({"制作", "模范制作", "俭约制作", "精密制作"})
    if craft_history.count("制作"): # 根据效率进行排序
        forbidden_actions = forbidden_actions.union({"坯料制作", "模范制作", "俭约制作"})
    if craft_history.count("模范制作"):
        forbidden_actions.add("坯料制作")
    if craft_history.count("模范制作") == 2:
        forbidden_actions.add("俭约制作")
    if craft_history.count("俭约制作"):
        forbidden_actions.add("坯料制作")
    if craft_history.count("俭约制作") == 2:
        forbidden_actions.add("模范制作")
    if craft_history.count("模范制作") == craft_history.count("俭约制作") == 1:
        if craft_history[-1] == "模范制作":
            forbidden_actions.add("俭约制作")
        if craft_history[-1] == "俭约制作":
            forbidden_actions.add("模范制作")
            forbidden_actions.add("制作") # 暂时保留, 可能存在过度剪枝的情况
    if craft_history.count("精密制作"):
        forbidden_actions = forbidden_actions.union({"坯料制作", "模范制作", "制作", "俭约制作"})
    if craft.status.name in SpecialStatus or "专心致志" in craft.effects: # 考虑一下高品质情况
        if craft.get_skill_durability("集中制作") + craft.current_progress < craft.recipe.max_difficulty:
            available_actions.add("集中制作")
            forbidden_actions.add("坯料制作")
        else:
            global default_process_round
            available_actions.add("秘诀")
            available_actions.add("集中加工")
            default_process_round += 1
    result_actions = set()
    for action in available_actions:
        if action not in forbidden_actions and craft.get_skill_availability(action): result_actions.add(action)
    return result_actions

def Get_Quality_AllowSkills(craft: Craft.Craft, craft_history: list = []) -> set:
    """
    得到当前可进行的加工技能
    :param craft: 生产配方
    :param craft_history: 预计技能列表
    :return: 可用加工技能
    """
    remainCp = craft.current_cp - cpReq # 可用cp
    available_actions = set()
    forbidden_actions = set()
    if craft.status.name in SpecialStatus:
        available_actions.add("集中加工")
        available_actions.add("秘诀")
        forbidden_actions = forbidden_actions.union({"加工", "中级加工", "上级加工"})
    elif '观察' in craft.effects and craft.status.name not in SpecialStatus: return {'注视加工'} # 观察-注释加工
    if (craft.recipe.max_quality - craft.current_quality) <= craft.get_skill_quality("比尔格的祝福"): return {"比尔格的祝福"} # 第一种提前收尾
    if remainCp < 0: return available_actions # 无CP
    available_actions = available_actions.union({"加工", "俭约加工", "坯料加工"}) # 初始化
    inner_quiet = 0 if "内静" not in craft.effects else craft.effects["内静"].param
    manipulation = 0
    # buff相关
    if "掌握" in craft.effects:
        manipulation = craft.effects["掌握"].param
        if craft.effects["掌握"].param < 3 and inner_quiet < 2: forbidden_actions.add("加工")
    if "俭约" in craft.effects:
        available_actions.add("坯料加工")
        forbidden_actions.add("俭约加工")
    else:
        available_actions.add("俭约加工")
        forbidden_actions.add("坯料加工")
    if "加工" in craft.effects:
        available_actions.add("中级加工")
        forbidden_actions = forbidden_actions.union({"加工", "俭约加工", "坯料加工", "改革"})
    if "中级加工" in craft.effects:
        available_actions.add("上级加工")
        forbidden_actions = forbidden_actions.union({"加工", "俭约加工", "坯料加工", "改革"})
    if inner_quiet >= 10:
        available_actions.add("工匠的神技")
        available_actions.add("阔步")
    if "阔步" in craft.effects:
        forbidden_actions.add("工匠的神技")
        forbidden_actions.add("阔步")
        if "改革" in craft.effects: available_actions.add("比尔格的祝福")
        if craft.effects["阔步"].param == 1: forbidden_actions.add("改革") # [阔步-X-X-改革]**格式禁用
    if "改革" in craft.effects:
        if craft.effects["改革"].param % 3: forbidden_actions.add("加工") # [改革-加工-*-加工-加工]**禁用格式
        if craft.effects["改革"].param % 3 == 1: forbidden_actions.add("阔步") # [改革-阔步-X-X-阔步]**禁用格式 # 暂时保留, 可能存在过度剪枝的情况
        if craft.effects["改革"].param >= 3:
            if remainCp < 88: forbidden_actions.add("工匠的神技") # [改革-X-工匠的神技-阔步-比尔格]**CP不足
            if remainCp < 81: # [改革-X-俭约加工-阔步-比尔格]**CP不足
                forbidden_actions.add("俭约加工")
                forbidden_actions.add("观察")
        if craft.effects["改革"].param < 3:
            if remainCp < 106: forbidden_actions.add("工匠的神技") # [改革-X-X-工匠的神技-阔步-改革-比尔格]**CP不足
            if remainCp < 99: # [改革-X-X-俭约加工-?-阔步-改革-比尔格]**CP不足
                forbidden_actions.add("俭约加工")
                forbidden_actions.add("观察")
        if craft.effects["改革"].param // 2 and inner_quiet >= 8: available_actions.add("观察")
    else:
        available_actions.add("改革")
        if inner_quiet >= 2: forbidden_actions = forbidden_actions.union({"加工", "中级加工", "上级加工", "工匠的神技", "俭约加工", "坯料加工", "比尔格的祝福"})
    # 耐久相关
    now_dur = craft.current_durability + 5 * manipulation - durReq # 可用耐久
    if '掌握' not in craft.effects and '改革' not in craft.effects and '阔步' not in craft.effects and '加工' not in craft.effects and '中级加工' not in craft.effects:
        # if remainCp >= 250 and craft.current_durability <= craft.recipe.max_durability - 30: available_actions.add('精修')
        if inner_quiet < 8 and remainCp >= 280:
            if (craft.recipe.max_durability == 70 and craft.recipe.max_durability - craft.current_durability >= 50) or craft.recipe.max_durability == 35: # 兼容35/40dur配方
                available_actions.add("掌握")
    if craft_history.count("工匠的神技"): forbidden_actions.add("俭约加工")
    if now_dur <= 40: forbidden_actions.add("加工")
    if now_dur <= 15: forbidden_actions.add("俭约加工")
    if now_dur <= 20: forbidden_actions = forbidden_actions.union({"加工", "集中加工", "观察"})
    if craft.current_durability <= (5 * int(bool(manipulation)) + 25): forbidden_actions.add("坯料加工")
    if now_dur <= 10: forbidden_actions = forbidden_actions.union({"工匠的神技", "阔步", "改革"})
    #CP相关
    if remainCp < 81: # [-俭约加工-阔步-比尔格]**CP不足
        forbidden_actions.add("俭约加工") 
        forbidden_actions.add("观察") 
    if remainCp < 74 and "改革" not in craft.effects and "阔步" not in craft.effects:#[阔步-改革-比尔格]**CP不够
        forbidden_actions.add("阔步")
        forbidden_actions.add("改革")
    if remainCp < 56: # [-阔步-比尔格]**CP不足
        forbidden_actions.add("工匠的神技")
        forbidden_actions.add("阔步")
    if remainCp < 42: forbidden_actions.add("改革") # [-改革-比尔格]**CP不足
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

def Generate_Process_Routes(craft: Craft.Craft) -> tuple[Craft.Craft, list]:
    """
    根据进度计算结果
    :param craft: 生产配方
    :return: 预计结果, 预计技能列表
    """
    queue = [(craft, [])]
    routes = (craft, [])
    max_difficulty = craft.recipe.max_difficulty
    base_base_process = craft.craft_data.base_process
    while queue: 
        t_craft, t_history = queue.pop(0) # 获取一个待办事项
        for action in Get_Process_AllowSkills(t_craft, t_history):
            tt_craft = t_craft.clone()
            tt_craft.use_skill(action)
            tt_craft.status = Manager.mStatus.DEFAULT_STATUS() # 重设球色
            new_data = (tt_craft, t_history + [action]) # 模拟使用技能然后组成一个新的事项
            if (max_difficulty - tt_craft.current_progress) / base_base_process <= 2: # 可以进行加工品质了
                get_retention(tt_craft)
                ttt_craft, ttt_history = Generate_Quality_Routes(tt_craft) # 将当前路径进行品质计算
                new_data = (ttt_craft, t_history + [action] + ttt_history) # 模拟使用技能然后组成一个新的事项
                if routes[0].current_quality < ttt_craft.current_quality: routes = new_data # 得到总路径品质最高的解
                elif routes[0].current_quality == ttt_craft.current_quality:
                    if process_usedtime(routes[1]) > process_usedtime(new_data[1]): routes = new_data # 如果品质相同比较轮次
                    elif routes[0].craft_round == ttt_craft.craft_round and routes[0].current_cp < ttt_craft.current_cp: routes = new_data # 如果轮次相同保留高CP
                continue
            if t_craft.craft_round < default_process_round: queue.insert(0, new_data) # 制作轮次大于默认制作轮次
    return routes[0], routes[1]

def Generate_Quality_Routes(craft: Craft.Craft) -> tuple[Craft.Craft, list]:
    """
    根据品质计算结果
    :param craft: 生产配方
    :return: 预计结果, 预计技能列表
    """
    queue = [(craft, [])] # 待办事项
    top_route = (craft, []) # 目前最佳项 第一个坑是数据，第二个是技能历史
    while queue:
        t_craft, t_history = queue.pop(0) # 获取一个待办事项
        for action in Get_Quality_AllowSkills(t_craft, t_history):
            tt_craft = t_craft.clone()
            tt_craft.use_skill(action)
            tt_craft.status = Manager.mStatus.DEFAULT_STATUS() # 重设球色
            if tt_craft.current_durability < durReq or tt_craft.current_cp < cpReq: continue # 不满足收尾条件
            new_data = (tt_craft, t_history + [action]) # 模拟使用技能然后组成一个新的事项
            if action == "比尔格的祝福" and tt_craft.current_quality < top_route[0].current_quality: continue # Low Quality
            if tt_craft.current_quality > top_route[0].current_quality: top_route = new_data # 得到当前路径品质最高的解
            elif top_route[0].current_quality == tt_craft.current_quality:
                if process_usedtime(new_data[1]) < process_usedtime(top_route[1]): top_route = new_data # 比较用时
                elif process_usedtime(new_data[1]) == process_usedtime(top_route[1]) and tt_craft.current_cp > top_route[0].current_cp: top_route = new_data # 如果工序用时保留高CP
            if action == "比尔格的祝福": continue # 比尔格收尾了
            if tt_craft.current_quality == craft.recipe.max_quality: continue # 品质满了
            queue.insert(0, new_data) # 将未进行完的事项从重新添加到队列
    return top_route[0], top_route[1]

class Stage1:#作业阶段

    def __init__(self):
        self.queue = []
        self.prev_skill = None

    def is_finished(self, craft: Craft.Craft, prev_skill: str = None) -> bool:
        """
        接口，用于判断本stage是否负责完成
        :param craft: 生产数据
        :param prev_skill: 上一个使用的技能名字
        :return: bool
        """
        if (craft.recipe.max_difficulty - craft.current_progress) / craft.craft_data.base_process <= 2: return True
        elif not bool(self.queue) or craft.status.name in SpecialStatus or prev_skill != self.prev_skill:
            routes, ans = Generate_Process_Routes(craft)
            if ans:
                self.queue = ans
            return False

    def deal(self, craft: Craft.Craft, prev_skill: str = None) -> str:
        self.prev_skill = self.queue.pop(0)
        return self.prev_skill

class Stage2:#加工阶段

    def __init__(self):
        self.queue = []
        self.prev_skill = None
        self.is_first = True

    def is_finished(self, craft: Craft.Craft, prev_skill: str = None) -> bool:
        """
        接口，用于判断本stage是否负责完成
        :param craft: 生产数据
        :param prev_skill: 上一个使用的技能名字
        :return: bool
        """
        if craft.current_quality >= craft.recipe.max_quality or prev_skill == "比尔格的祝福": return True
        if not bool(self.queue) or craft.status.name in SpecialStatus or prev_skill != self.prev_skill:
            get_retention(craft)
            routes, ans = Generate_Quality_Routes(craft)
            if ans:
                self.queue = ans
        return not bool(self.queue)

    def deal(self, craft: Craft.Craft, prev_skill: str = None) -> str:
        """
        接口，返回生产技能
        :param craft: 生产数据
        :param prev_skill: 上一个使用的技能名字
        :return: 生产技能
        """
        self.prev_skill = self.queue.pop(0)
        return self.prev_skill

class Stage3:
        
    def __init__(self):
        self.queue = []
        self.is_first = True
        self.prev_skill = None

    def is_finished(self, craft: Craft.Craft, prev_skill: str = None) -> bool:
        """
        接口，用于判断本stage是否负责完成
        :param craft: 生产数据
        :param prev_skill: 上一个使用的技能名字
        :return: bool
        """
        if self.is_first:
            self.is_first = False
            if craft.status.name in SpecialStatus and craft.current_cp >= 18: self.queue.append("集中制作")
            else:
                remaining_prog = (craft.recipe.max_difficulty - craft.current_progress) / craft.craft_data.base_process
                if remaining_prog >= 1.8: self.queue.extend(["观察", "注视制作"])
                elif remaining_prog >= 1.2: self.queue.append("模范制作")
                else: self.queue.append("制作")
        return not bool(self.queue)

    def deal(self, craft: Craft.Craft, prev_skill: str = None) -> str:
        """
        接口，返回生产技能
        :param craft: 生产数据
        :param prev_skill: 上一个使用的技能名字
        :return: 生产技能
        """
        self.prev_skill = self.queue.pop(0)
        return self.prev_skill

class RikaSolver(Solver): # 本算法根据Rika算法魔改,pruning(V2) by zeroneko

    @staticmethod
    def suitable(craft):
        return craft.recipe.recipe_row["RecipeLevelTable"]["ClassJobLevel"] == 90 and bool(craft.recipe.recipe_row["RecipeLevelTable"]["Stars"]) and craft.recipe.status_flag == 0b1111

    def __init__(self, craft, logger):
        super().__init__(craft, logger)
        self.stage = 0
        self.choose_stages = [Stage1, Stage2, Stage3]
        self.process_stages = [s() for s in self.choose_stages]
        self.can_hq = craft.recipe.recipe_row["CanHq"]

    def process(self, craft, used_skill = None) -> str:
        """
        接口，返回生产技能
        :param craft: 生产数据
        :param used_skill: 上一个使用的技能名字
        :return: 推荐技能名称
        """
        if self.stage < 0: return ''
        if craft.craft_round == 1: return '坚信' # Rika算法给定起手
        if craft.craft_round == 2: return '掌握'
        if craft.craft_round == 3: return '崇敬'
        while self.process_stages[self.stage].is_finished(craft, used_skill):
            self.stage += 1
            if self.stage >= len(self.process_stages):
                self.stage = -1
                return ''
        ans = self.process_stages[self.stage].deal(craft, used_skill)
        return ans