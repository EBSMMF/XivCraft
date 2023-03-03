import math
from typing import Union

from . import Manager, Models

class CheckUnpass(Exception):
    pass

class CraftData(object):
    def __init__(self, recipe: Models.Recipe, player: Models.Player):
        rlv_data = recipe.recipe_row["RecipeLevelTable"]
        ProgressDivider = rlv_data["ProgressDivider"]   # 作业难度系数
        QualityDivider = rlv_data["QualityDivider"]     # 品质难度系数
        ProgressModifier = rlv_data["ProgressModifier"] / 100 # 作业压制系数
        QualityModifier = rlv_data["QualityModifier"] / 100   # 品质压制系数
        self.base_process = math.floor(ProgressModifier * (10 * player.craftmanship / ProgressDivider  + 2))
        self.base_quality = math.floor(QualityModifier * (10 * player.control/ QualityDivider + 35))

class Craft(object):
    def __init__(self,
                 recipe: Models.Recipe,
                 player: Models.Player,
                 craft_round: int = 1,
                 current_progress: int = 0,
                 current_quality: int = 0,
                 current_durability: int = None,
                 current_cp: int = None,
                 status: Models.Status = None,
                 effects: dict[str, Models.Effect] = None,
                 craft_data: CraftData = None,
                 ):
        self.recipe = recipe
        self.player = player
        self.craft_round = craft_round
        self.current_progress = current_progress
        self.current_quality = current_quality
        self.current_durability = current_durability if current_durability is not None else recipe.max_durability
        self.current_cp = current_cp if current_cp is not None else player.max_cp
        self.status = status if status is not None else Manager.mStatus.DEFAULT_STATUS()
        self.effects = effects if effects is not None else dict()
        self.craft_data = craft_data if craft_data is not None else CraftData(recipe, player)
        self.effect_to_add: dict[str, Models.Effect] = dict()
        
    def is_finished(self):
        return self.current_progress >= self.recipe.max_difficulty

    def clone(self) -> 'Craft':
        new_effects=dict()
        for e in self.effects.values():
            new_effects[e.name]=e.__class__(e.param)
        return Craft(
            recipe=self.recipe,
            player=self.player,
            craft_round=self.craft_round,
            current_progress=self.current_progress,
            current_quality=self.current_quality,
            current_durability=self.current_durability,
            current_cp=self.current_cp,
            status=self.status,
            effects=new_effects,
            craft_data=self.craft_data,
        )

    def add_effect(self, effect_name: str, param: int):
        new_effect = Manager.effects[effect_name](param)
        if new_effect.name in self.effects:
            del self.effects[new_effect.name]
        self.effect_to_add[new_effect.name] = new_effect
 
    def merge_effects(self):
        self.effects |= self.effect_to_add
        self.effect_to_add.clear()

    def get_skill_progress(self, skill: Union[Models.Skill, str]) -> int:
        if type(skill) == str:
            skill = Manager.skills[skill]()
        effect_progress = 0
        for e in self.effects.values():
            effect_progress += e.progress_factor(self, skill)
        base_progress = self.craft_data.base_process # 基准进展
        skill_progress = skill.progress(self) * (1 + effect_progress) / 100 # 效率系数=技能效率*(1+加成系数)/100
        status_progress = 1 + self.status.progress_factor(self, skill) #进展状态系数
        return math.floor(base_progress * skill_progress * status_progress)  #作业进展=基准进展*效率系数*进展状态系数


    def get_skill_quality(self, skill: Union[Models.Skill, str]) -> int:
        if type(skill) == str:
            skill = Manager.skills[skill]()
        innerquiet_quality = 0 if "内静" not in self.effects else self.effects["内静"].param
        effect_quality = 0
        for e in self.effects.values():
            effect_quality += e.quality_factor(self, skill)
        base_quality = self.craft_data.base_quality # 基准品质
        skill_quality = skill.quality(self) * (1 + effect_quality) / 100 # 效率系数=技能效率*(1+加成系数)/100
        status_progress = 1 + self.status.quality_factor(self, skill) #进展状态系数
        innerquiet_quality = 1 + 0.1 * innerquiet_quality #内静系数
        return math.floor(base_quality * skill_quality * status_progress * innerquiet_quality) #加工品质=基准品质*效率系数*品质状态系数
        
    def get_skill_durability(self, skill: Union[Models.Skill, str]) -> int:
        if type(skill) == str:
            skill = Manager.skills[skill]()
        effect_durability = 1
        for e in self.effects.values():
            effect_durability *= 1 + e.durability_factor(self, skill)
        return math.ceil(skill.durability(self) * effect_durability * (1 + self.status.durability_factor(self, skill)))

    def get_skill_cost(self, skill: Union[Models.Skill, str]) -> int:
        if type(skill) == str:
            skill = Manager.skills[skill]()
        effect_cost = 1
        for e in self.effects.values():
            effect_cost *= 1 + e.cost_factor(self, skill)
        return math.ceil(skill.cost(self) * effect_cost * (1 + self.status.cost_factor(self, skill)))
    
    def get_skill_availability(self, skill: Union[Models.Skill, str]) -> bool:
        if type(skill) == str:
            skill = Manager.skills[skill]()
        return self.get_skill_cost(skill) <= self.current_cp and self.get_skill_durability(skill) <= self.current_durability

    def use_skill(self, skill: Union[Models.Skill, str], check_mode=False) -> 'Craft':
        if type(skill) == str:
            skill = Manager.skills[skill]()
        self.effect_to_add.clear()

        added_progress = self.get_skill_progress(skill)
        added_quality = self.get_skill_quality(skill)
        used_durability = self.get_skill_durability(skill)
        used_cp = self.get_skill_cost(skill)

        if check_mode:
            if self.current_progress + added_progress < self.recipe.max_difficulty and self.current_durability <= used_durability: raise CheckUnpass(skill.name)
            if self.current_cp < used_cp: raise CheckUnpass(skill.name)

        self.current_progress = min(self.current_progress + added_progress, self.recipe.max_difficulty)
        self.current_quality = min(self.current_quality + added_quality, self.recipe.max_quality)
        self.current_durability = self.current_durability - used_durability
        self.current_cp = self.current_cp - used_cp

        skill.after_use(self)

        if skill.pass_rounds:
            self.craft_round += 1
            for e in list(self.effects.values()):
                e.after_round(self, skill)
            self.status.after_round(self, skill)

        self.merge_effects()

        if added_quality and "内静" not in self.effects and skill.name != "比尔格的祝福":
            self.add_effect('内静', 1)
            self.merge_effects()
            
        return self
        
    def simple_str(self):
        return f"{self.recipe}{self.player}:{self.current_progress}/{self.current_quality}/{self.current_durability}/{self.current_cp}"

    def __str__(self):
        return """********** round {round} **********
player:\t{player}
recipe:\t{recipe}
progress:\t{current_progress}/{max_difficulty}
quality:\t{current_quality}/{max_quality}
durability:\t{current_durability}/{max_durability}
CP:\t{current_cp}/{max_cp}
effects:\t{effects}
status:\t{status}
******************************""".format(
            round=self.craft_round,
            recipe=self.recipe,
            player=self.player,
            current_progress=self.current_progress,
            max_difficulty=self.recipe.max_difficulty,
            current_quality=self.current_quality,
            max_quality=self.recipe.max_quality,
            current_durability=self.current_durability,
            max_durability=self.recipe.max_durability,
            current_cp=self.current_cp,
            max_cp=self.player.max_cp,
            effects=" ".join(map(str, self.effects.values())),
            status=self.status,
        )