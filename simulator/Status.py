from .Models import Status

from FFxivPythonTrigger import plugins

class White(Status):
    id = 1
    name = "通常"

class Red(Status):
    id = 2
    name = "高品质"
    _quality_factor = 0.5
    for equip_id in {38737, 38738, 38739, 38740, 38741, 38742, 38743, 38744}: # patch 6.35 Adaptive splendorous tool add 0.25 quality_factor
        for i in plugins.XivMemory.inventory.get_item_in_containers_by_key(equip_id, "equipment"):
            if i: _quality_factor += 0.25

class Rainbow(Status):
    id = 3
    name = "最高品质"
    _quality_factor = 3

class Black(Status):
    id = 4
    name = "低品质"
    _quality_factor = -0.5

class Yellow(Status):
    id = 5
    name = "安定"

class Blue(Status):
    id = 6
    name = "结实"
    _durability_factor = -0.5

class Green(Status):
    id = 7
    name = "高效"
    _cost_factor = -0.5

class DeepBlue(Status):
    id = 8
    name = "大进展"
    _progress_factor = 0.5

class Purple(Status):
    id = 9
    name = "长持续"

    def after_round(self, craft, used_skill):
        for e in craft.effect_to_add.values():
            if e.use_rounds:
                e.param += 2

DEFAULT_STATUS = White
