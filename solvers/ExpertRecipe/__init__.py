from .. import Solver
from ...simulator import Craft, Manager

durReq = 1  # 留一个作业耐久
cpReq = 12  # 留一个作业cp
SpecialStatus = {"高品质", "结实", "高效", "长持续"}

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

def is_process_finished(craft: Craft.Craft) -> bool:
    """
    判断作业部分是否差一次制作完成
    :param craft:生产数据
    """
    return (craft.recipe.max_difficulty - craft.current_progress) / craft.craft_data.base_process <= 2

def progess_skill(craft: Craft.Craft, skill: str) -> str:
    """
    对于作业类技能先模拟是否会搓爆，是的话打一个确认
    :param craft: 生产数据
    :param skill: 技能名
    :return: 决定使用的技能
    """
    temp = craft.clone().use_skill(skill) # 创建数据副本并且使用技能
    if temp.is_finished(): # 判断是否满作业
        return "最终确认"
    else:
        return skill

def Get_Quality_AllowSkills(craft: Craft.Craft, craft_history: list = []) -> set:
    """
    当前可进行的加工技能
    :param craft: 生产配方
    :param craft_history: 历史路线
    :return: 可用技能
    """
    remainCp = craft.current_cp - cpReq # 可用cp
    available_actions = set()
    forbidden_actions = set()
    if craft.status.name == "高品质":
        available_actions.add("集中加工")
        available_actions.add("秘诀")
        forbidden_actions = forbidden_actions.union({"加工", "中级加工", "上级加工"})
    elif '观察' in craft.effects and craft.status.name not in SpecialStatus: return {'注视加工'} # 观察-注释加工
    if (craft.recipe.max_quality - craft.current_quality) <= craft.get_skill_quality("比尔格的祝福"): return {"比尔格的祝福"} # 第一种提前收尾
    if remainCp < 0: return available_actions # 无CP
    available_actions = available_actions.union({"加工", "俭约加工", "坯料加工"}) # 初始化
    inner_quiet = 0 if "内静" not in craft.effects else craft.effects["内静"].param
    manipulation = 0
    if "掌握" in craft.effects:
        manipulation = craft.effects["掌握"].param
        if craft.effects["掌握"].param < 3 and inner_quiet < 2: forbidden_actions.add("加工")
    if "俭约" in craft.effects:
        available_actions.add("坯料加工")
        forbidden_actions.add("俭约加工")
    else:
        available_actions.add("俭约加工")
        forbidden_actions.add("坯料加工")
    # 耐久相关
    now_dur = craft.current_durability + 5 * manipulation - durReq # 可用耐久
    if '改革' not in craft.effects and '阔步' not in craft.effects and '加工' not in craft.effects and '中级加工' not in craft.effects:
        # if remainCp >= 250 and craft.current_durability <= craft.recipe.max_durability - 30: available_actions.add('精修')
        if inner_quiet < 8 and remainCp >= 230:
            # if (craft.recipe.max_durability == 70 and craft.recipe.max_durability - craft.current_durability >= 50) or craft.recipe.max_durability == 35: # 兼容35/40dur配方
                if '掌握' not in craft.effects: available_actions.add("掌握")
                available_actions.add('精修')
    # if craft.current_durability <= 15 and craft.current_cp >= 170: available_actions.add("精修")
    if craft_history.count("工匠的神技"): forbidden_actions.add("俭约加工")
    if now_dur <= 30 + craft.get_skill_durability("加工"): forbidden_actions.add("加工")
    if now_dur <= 10 + craft.get_skill_durability("俭约加工"): forbidden_actions.add("俭约加工")
    if now_dur <= 10 + craft.get_skill_durability("加工"): forbidden_actions = forbidden_actions.union({"加工", "集中加工", "观察"})
    if craft.current_durability <= (5 * int(bool(manipulation)) + 5 + craft.get_skill_durability("坯料加工")): forbidden_actions.add("坯料加工")
    if now_dur <= 10: forbidden_actions = forbidden_actions.union({"工匠的神技", "阔步", "改革"})
    # buff相关
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
            if remainCp < 56 + craft.get_skill_cost("工匠的神技"): forbidden_actions.add("工匠的神技") # [改革-X-工匠的神技-阔步-比尔格]**CP不足
            if remainCp < 56 + craft.get_skill_cost("俭约加工"): # [改革-X-俭约加工-阔步-比尔格]**CP不足
                forbidden_actions.add("俭约加工")
                forbidden_actions.add("观察")
        if craft.effects["改革"].param < 3:
            if remainCp < 74 + craft.get_skill_cost("工匠的神技"): forbidden_actions.add("工匠的神技") # [改革-X-X-工匠的神技-阔步-改革-比尔格]**CP不足
            if remainCp < 74 + craft.get_skill_cost("俭约加工"): # [改革-X-X-俭约加工-?-阔步-改革-比尔格]**CP不足
                forbidden_actions.add("俭约加工")
                forbidden_actions.add("观察")
        if craft.effects["改革"].param // 2 and inner_quiet >= 8: available_actions.add("观察")
    else:
        available_actions.add("改革")
        if inner_quiet >= 2: forbidden_actions = forbidden_actions.union({"加工", "中级加工", "上级加工", "工匠的神技", "俭约加工", "坯料加工", "比尔格的祝福"})
    #CP相关
    if remainCp < 81: # [-俭约加工-阔步-比尔格]**CP不足
        forbidden_actions.add("俭约加工") 
        forbidden_actions.add("观察") 
    if remainCp < 42 + craft.get_skill_cost("阔步") and "改革" not in craft.effects:#[阔步-改革-比尔格]**CP不够
        forbidden_actions.add("阔步")
    if remainCp < 56 + craft.get_skill_cost("改革") and "阔步" not in craft.effects:#[阔步-改革-比尔格]**CP不够
        forbidden_actions.add("改革")
    if remainCp < 24 + craft.get_skill_cost("阔步"): # [-阔步-比尔格]**CP不足
        forbidden_actions.add("工匠的神技")
        forbidden_actions.add("阔步")
    if remainCp < 24 + craft.get_skill_cost("改革"): forbidden_actions.add("改革") # [-改革-比尔格]**CP不足
    result_actions = set()
    for action in available_actions:
        if action not in forbidden_actions and craft.get_skill_availability(action): result_actions.add(action)
    return result_actions

def Generate_Quality_Routes(craft: Craft.Craft) -> tuple[Craft.Craft, list]:
    """
    根据品质计算结果
    :param craft: 生产配方
    :return: tuple[Craft.Craft, list]: 最终预估结果, 目标路线图
    """
    queue = [(craft, [])] # 待办事项
    top_route = (craft, []) # 目前最佳项 第一个坑是数据，第二个是技能历史
    while queue:
        t_craft, t_history = queue.pop(0) # 获取一个待办事项
        for action in Get_Quality_AllowSkills(t_craft, t_history):
            tt_craft = t_craft.clone()
            tt_craft.use_skill(action)
            tt_craft.status = Manager.mStatus.DEFAULT_STATUS() # 重设球色
            new_data = (tt_craft, t_history + [action]) # 模拟使用技能然后组成一个新的事项
            if tt_craft.current_durability < durReq or tt_craft.current_cp < cpReq: continue # 不满足收尾条件
            if top_route[0].current_quality < tt_craft.current_quality: top_route = new_data # 得到当前路径品质最高的解
            elif top_route[0].current_quality == tt_craft.current_quality:
                if top_route[0].craft_round > tt_craft.craft_round: top_route = new_data # 如果品质相同比较轮次
                elif top_route[0].craft_round == tt_craft.craft_round and top_route[0].current_cp <= tt_craft.current_cp: top_route = new_data # 如果轮次相同保留高CP
            if action == "比尔格的祝福": continue # 比尔格收尾了
            if tt_craft.current_quality == craft.recipe.max_quality: continue #品质满了
            queue.insert(0, new_data) # 将未进行完的事项从重新添加到队列
    return top_route[0], top_route[1]

class Stage1:

    def is_finished(self, craft: Craft.Craft, prev_skill: str = None) -> bool:
        """
        接口，用于判断本stage是否负责完成
        :param craft: 生产数据
        :param prev_skill: 上一个使用的技能名字
        :return: bool
        """
        return is_process_finished(craft)

    def deal(self, craft: Craft.Craft, prev_skill: str = None) -> str:
        process_finish = is_process_finished(craft)
        inner_quiet = 0 if "内静" not in craft.effects else craft.effects["内静"].param
        if craft.status == "长持续":# 紫球处理
            if not process_finish and "崇敬" not in craft.effects: return "崇敬"
            if craft.current_cp > 400:
                if "俭约" not in craft.effects: return "俭约"
                if "掌握" not in craft.effects: return "掌握"
        elif craft.status == "高品质":# 红球处理
            if craft.current_durability > 10:
                if inner_quiet < 4 or "改革" in craft.effects: return "集中加工"
                elif ("崇敬" in craft.effects or is_process_finished(craft.clone().use_skill("集中制作"))) and craft.current_durability > 10: return progess_skill(craft, "集中制作") # 可以通过集中制作进入加工阶段
            return "秘诀"
        elif craft.status == "高效": # 绿球处理
            if craft.current_cp >= 400:
                if "掌握" not in craft.effects: return "掌握"
                empty_dur = craft.recipe.max_durability - craft.current_durability # 消耗了多少耐久（用于判断精修一类）
                if empty_dur >= 30: return "精修"

        if craft.current_durability <= craft.get_skill_durability("制作"): return "精修" # 耐久不足以使用下一个作业技能就打精修
        
        if craft.status == "安定": # 黄球处理
            if "崇敬" in craft.effects and not process_finish: return progess_skill(craft, "高速制作")
            elif inner_quiet < 4: return "仓促"
            return progess_skill(craft, "高速制作")
        if not process_finish:
            if craft.status == "大进展" or "崇敬" in craft.effects:
                process_list = {"制作", "高速制作"}
                process_list.add("俭约制作") if "俭约" not in craft.effects else process_list.add("模范制作")
                for s in process_list:
                    if is_process_finished(craft.clone().use_skill(s)): return progess_skill(craft, s)
                return progess_skill(craft, "高速制作")
        if inner_quiet < 4:
            return "仓促" if "俭约" in craft.effects else "俭约加工"
        else: return "崇敬"

class Stage2:

    def __init__(self) -> None:
        self.queue = []
        self.prev_skill = None
        try:
            from FFxivPythonTrigger import plugins
            for equip_id in {10337, 10338, 10339, 10340, 10341, 10342, 10343, 10344}: # 判断专家水晶
                for i in plugins.XivMemory.inventory.get_item_in_containers_by_key(equip_id, "equipment"):
                    if i: self.blueprint = sum(i.count for i in plugins.XivMemory.inventory.get_item_in_containers_by_key(28724, "backpack")) # 获取背包图纸数量
        except:
            self.blueprint = 0
        self.blueprint_used = 0 # 目前使用过的图纸数量

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
            if ans: self.queue = ans
        return not bool(self.queue)

    def deal(self, craft: Craft.Craft, prev_skill: str = None) -> str:
        """
        接口，返回生产技能
        :param craft: 生产数据
        :param prev_skill: 上一个使用的技能名字
        :return: 生产技能
        """
        self.prev_skill = self.queue.pop(0)
        if prev_skill == "设计变动": self.blueprint_used += 1
        if self.prev_skill == "比尔格的祝福": # 判断是否需要使用图纸
            if craft.status != "高品质" and self.blueprint - self.blueprint_used and self.blueprint_used < 3 and craft.get_skill_quality("比尔格的祝福") + craft.current_quality < craft.recipe.recipe_row["RequiredQuality"] and craft.get_skill_quality("比尔格的祝福") * 1.5 + craft.current_quality >= craft.recipe.recipe_row["RequiredQuality"]: # 存在可用图纸且未达到最低品质线
                return "设计变动"
        return self.prev_skill

class Stage3:
    
    def __init__(self):
        self.queue = []
        self.prev_skill = None

    def is_finished(self, craft: Craft.Craft, prev_skill: str = None) ->bool:
        """
        接口，用于判断本stage是否负责完成
        :param craft: 生产数据
        :param prev_skill: 上一个使用的技能名字
        :return: bool
        """
        remaining_prog = (craft.recipe.max_difficulty - craft.current_progress) / craft.craft_data.base_process
        if craft.status.name in {"高品质", "最高品质"}:#特殊收尾
            if remaining_prog <= 1 and craft.current_quality < craft.recipe.recipe_row["RequiredQuality"] and craft.current_cp < 32: self.queue.append("秘诀")
            elif remaining_prog > 1 and craft.current_cp >= 18: self.queue.append("集中制作")
        if not bool(self.queue) or craft.status.name in SpecialStatus or prev_skill != self.prev_skill:
            if remaining_prog <= 1 and craft.current_cp >= 32 and craft.current_quality < craft.recipe.recipe_row["RequiredQuality"]: self.queue.append("精密制作")
            elif remaining_prog <= 1.2: self.queue.append("制作")
            elif remaining_prog <= 1.8: self.queue.append("模范制作")
            else: self.queue.extend(["观察", "注视制作"])
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
    
class ExpertRecipe(Solver):

    @staticmethod
    def suitable(craft):
        return craft.recipe.status_flag != 0b1111

    def __init__(self, craft, logger):
        super().__init__(craft, logger)
        self.stage = 0
        self.choose_stages = [Stage1, Stage2, Stage3]
        self.process_stages = [s() for s in self.choose_stages]

    def process(self, craft, used_skill = None) -> str:
        """
        接口，返回生产技能
        :param craft: 生产数据
        :param used_skill: 上一个使用的技能名字
        :return: 推荐技能名称
        """
        if self.stage < 0: return ""
        if craft.craft_round == 1: return "闲静"
        while self.process_stages[self.stage].is_finished(craft, used_skill):
            self.stage += 1
            if self.stage >= len(self.process_stages):
                self.stage = -1
                return ""
        ans = self.process_stages[self.stage].deal(craft, used_skill)
        return ans