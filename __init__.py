from ctypes import *
from typing import TYPE_CHECKING
import re

from FFxivPythonTrigger import *
from FFxivPythonTrigger.decorator import event, re_event
from FFxivPythonTrigger.hook import PluginHook
from FFxivPythonTrigger.saint_coinach import realm
from FFxivPythonTrigger.memory import read_int, read_memory
from FFxivPythonTrigger.memory.struct_factory import OffsetStruct, PointerStruct
from .simulator import Models, Manager, Craft
from .solvers import RikaSolver, JustDoIt, MacroCraft2, ExpertRecipe, NormalRecipe

registered_solvers = [
    JustDoIt.JustDoIt,
    MacroCraft2.MacroCraft,
    NormalRecipe.NormalRecipe,
    RikaSolver.RikaSolver,
    ExpertRecipe.ExpertRecipe,
]

recipe_sheet = realm.game_data.get_sheet('Recipe')
action_sheet = realm.game_data.get_sheet('Action')
craft_action_sheet = realm.game_data.get_sheet('CraftAction')

craft_start_sig = "40 53 48 83 EC ? 48 8B D9 C6 81 ? ? ? ? ? E8 ? ? ? ? 48 8D 4B ?"
craft_status_sig = "8B 05 * * * * BE ? ? ? ? 89 44 24 ?"
base_quality_ptr_sig = "48 8B 05 * * * * 33 C9 84 D2 48 89 5C 24"

CraftStatus_Offset = 0x18 #patch6.28cn
CraftStatus = OffsetStruct({
    'round': (c_uint, 0x0 + CraftStatus_Offset),
    'current_progress': (c_uint, 0x4 + CraftStatus_Offset),
    'current_quality': (c_uint, 0xC + CraftStatus_Offset),
    'current_durability': (c_uint, 0x18 + CraftStatus_Offset),
    'status_id': (c_ushort, 0x20 + CraftStatus_Offset)
})
BaseQualityPtr = PointerStruct(c_uint, 0x450)

def get_action_name_by_id(action_id):
    if action_id >= 100000:
        return craft_action_sheet[action_id]['Name']
    else:
        return action_sheet[action_id]['Name']

callback = lambda ans: plugins.XivMemory.calls.do_text_command(f'/ac {ans}')

class CraftStart(EventBase):
    id = "craft_start"

    def __init__(self, recipe: Models.Recipe, player: Models.Player, base_quality: int):
        self.recipe = recipe
        self.player = player
        self.base_quality = base_quality

    def text(self):
        return f"CraftStart;{self.recipe};{self.player};{self.base_quality}"

class CraftEnd(EventBase):
    id = "craft_end"

    def text(self):
        return "CraftEnd"

class CraftAction(EventBase):
    id = "craft_action"

    def __init__(self, craft: Craft.Craft, skill: Models.Skill):
        self.craft = craft
        self.skill = skill

    def text(self):
        return f"CraftAction;{self.skill.name}"

class XivCraft(PluginBase):
    name = "XivCraft"

    def __init__(self):
        super().__init__()
        class ChatLogRegexProcessor(object):
            def __init__(_self):
                _self.data = dict()

            def register(_self, channel_id, regex, callback):
                if channel_id not in _self.data:
                    _self.data[channel_id] = set()
                _self.data[channel_id].add((re.compile(regex), callback))

        am = AddressManager(self.name, self.logger)
        self.craft_starthook = self.craft_start_hook(self, am.scan_address("craft_start", craft_start_sig))
        self.craft_status = read_memory(CraftStatus, am.scan_point('craft_status', craft_status_sig))
        self.base_quality = read_memory(BaseQualityPtr, am.scan_point('base_quality_ptr', base_quality_ptr_sig))
        self.base_quality = 0 if self.base_quality.value is None else self.base_quality.value

        self.channel_id = dict()
        self._recipe = None
        self.solver = None
        self.base_data = None

    @PluginHook.decorator(c_int64, [c_int64], True)
    def craft_start_hook(self, hook, a1):
        try:
            recipe_id = read_int(a1+0x3a4)
            self._recipe = recipe_sheet[recipe_id] if recipe_id else None
        except Exception as e:
            self.logger.error("error in craft start hook:\n" + format_exc())
        return hook.original(a1)

    def get_base_data(self):
        recipe = Models.Recipe(self._recipe)
        me = plugins.XivMemory.actor_table.me
        me_info = plugins.XivMemory.player_info.attr
        player = Models.Player(me.level, me_info.craft, me_info.control, me.max_cp)
        return recipe, player

    def get_current_craft(self, current_round = None, current_progress = None, current_quality = None, current_durability = None):
        me = plugins.XivMemory.actor_table.me
        recipe, player = self.base_data
        effects = dict()
        for eid, effect in me.effects.get_items():
            if eid in Manager.effects_id:
                new_effect = Manager.effects_id[eid](effect.param)
                effects[new_effect.name] = new_effect
        return Craft.Craft(
            recipe=recipe,
            player=player,
            craft_round=current_round or self.craft_status.round,
            current_progress=current_progress or self.craft_status.current_progress,
            current_quality=current_quality or self.craft_status.current_quality,
            current_durability=current_durability or self.craft_status.current_durability,
            current_cp=me.current_cp,
            status=Manager.status_id[self.craft_status.status_id or 1](),
            effects=effects,
        )

    def _craft_next(self, craft: Craft.Craft, skill: Models.Skill):
        if skill == "观察": craft.add_effect("观察", 1)
        if skill == "加工": craft.add_effect("加工", 1)
        if skill == "中级加工": craft.add_effect("中级加工", 1)
        if craft.effect_to_add != dict(): craft.merge_effects()
        # self.logger.debug(f"use skill:{skill.name}")
        # self.logger.debug(craft)
        process_event(CraftAction(craft, skill))
        if self.solver is not None and not craft.is_finished():
            ans = self.solver.process(craft, skill)
            self.logger.debug("suggested skill '%s'" % ans)
            if ans and callback is not None:
                self.create_mission(callback, ans, limit_sec=0)

    @event("network/zone/server/event_play", limit_sec = 0)
    def craft_next_network(self, evt: 'ServerEventPlay'):
        if evt.struct_message.event_id == 1 and evt.struct_message.category == 10:
            if evt.args[0] == 2: # 开始制作
                recipe, player = self.base_data = self.get_base_data()
                self.logger.info("start recipe:" + recipe.detail_str)
                craft = Craft.Craft(recipe=recipe, player=player, current_quality=self.base_quality)
                process_event(CraftStart(recipe, player, self.base_quality))
                for solver in registered_solvers:
                    if solver.suitable(craft):
                        self.solver = solver(craft=craft, logger=self.logger)
                        break
                sleep(0.7)
                if self.solver is not None:
                    self.logger.info("solver found, starting to solve...")
                    ans = self.solver.process(craft, None)
                    self.logger.debug("suggested skill '%s'" % ans)
                    if ans is not None and callback is not None:
                        self.create_mission(callback, ans, limit_sec=100000)
            if evt.args[0] == 4: # 结束制作
                process_event(CraftEnd())
                self.solver = None
                self.logger.info("end craft")
            if evt.args[0] in {9, 10}: # 制作动作结束
                event_message = {
                    "prev_action_id": evt.args[4],
                    "round": evt.args[6],
                    "current_progress": evt.args[7],
                    "add_progress": evt.args[8],
                    "current_quality": evt.args[9],
                    "add_quality": evt.args[10],
                    "current_durability": evt.args[12],
                    "add_durability": (evt.args[13] - (1 << 32)) if evt.args[13] else 0, # 0x100000000
                    "status_id": evt.args[14],
                    "prev_action_flag": evt.args[17] if evt.args[17] <= 32 else (evt.args[17] % (1 << 16)),
                }
                try:
                    skill = Manager.skills[get_action_name_by_id(event_message["prev_action_id"]) + ('' if event_message["prev_action_flag"] in {18,19} else ':fail')]()
                except KeyError:
                    return
                sleep(0.1)
                self._craft_next(self.get_current_craft(
                    current_round = event_message["round"],
                    current_progress = event_message["current_progress"],
                    current_quality = event_message["current_quality"],
                    current_durability = event_message["current_durability"],
                ), skill)
    # # layout control
