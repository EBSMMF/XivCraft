from .Models import Effect

class Observe(Effect):
    id = -99
    use_rounds = False
    name = '观察'
    _special_factor = 1

class Veneration(Effect):
    id = 2226
    name = '崇敬'
    _progress_factor = 0.5

class Innovation(Effect):
    id = 2189
    name = '改革'
    _quality_factor = 0.5

class InnerQuiet(Effect):
    id = 251
    name = '内静'
    use_rounds = False

    def after_round(self, craft, used_skill):
        if used_skill.quality(craft):
            self.param = min(10, self.param + 1)

class WasteNot(Effect):
    id = 252
    name = "俭约"
    _durability_factor = -0.5

class WasteNotTwo(WasteNot):
    id = 257

class GreatStrides(Effect):
    id = 254
    name = '阔步'
    _quality_factor = 1

    def after_round(self, craft, used_skill):
        if used_skill.quality(craft):
            del craft.effects[self.name]

class CarefulObservation(Effect):
    id = 2190
    name = '最终确认'

    def after_round(self, craft, used_skill):
        if craft.current_progress >= craft.recipe.max_difficulty:
            craft.current_progress = craft.recipe.max_difficulty - 1
            del craft.effects[self.name]
        else:
            super(CarefulObservation, self).after_round(craft, used_skill)
            # self.param -= 1
            # if not self.param and self.name in craft.effects:
            #     del craft.effects[self.name]

class MuscleMemory(Effect):
    id = 2191
    name = '坚信'
    _progress_factor = 1

    def after_round(self, craft, used_skill):
        self.param -= 1
        if (used_skill.progress(craft) or not self.param) and self.name in craft.effects:
            del craft.effects[self.name]

class Manipulation(Effect):
    id = 1164
    name = '掌握'

    def after_round(self, craft, used_skill):
        self.param -= 1
        if not self.param and self.name in craft.effects:
            del craft.effects[self.name]
        if craft.current_durability:
            craft.current_durability = min(craft.current_durability + 5, craft.recipe.max_durability)

class BasicTouch(Effect):
    id = -100
    name = '加工'
    _special_factor = 1

class StandardTouch(Effect):
    id = -101
    name = '中级加工'
    _special_factor = 1

class StandardTouch(Effect):
    id = -101
    name = '中级加工'
    _special_factor = 1

class HeartAndSoul(Effect):
    id = 2665
    name = '专心致志'