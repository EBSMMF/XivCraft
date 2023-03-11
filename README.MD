# XivCraft

本插件基于FPT2中XivCraft进行重建
使用本插件默认您为满级角色

## JsutDoit 
适用于普通配方


## CutsceneSkipper

动画城跳动画

@cutscene

## PosLocker

位置锁定（防击退）

@posL

## SkillAniUnlocker

解除动画锁（十插）

@sALock

## Slider

滑步

@slide

## SpeedHack

加速

@speedH [get/set] [args]

## SuperJump

超级跳

@sjump [function] [args]

function

```
    [get]:      get current jump value
    [set]:      set current jump value
                format: /e @sjump set [value(float) / "default"]
```

## Teleporter

瞬移

@tp [function] [args]

function

```
    [get]:          get current coordinates
  
    [set]:          set current coordinates
                    format: /e @tp set [x:float] [y:float] [z:float]
  
    [list]:         list saved coordinates in current zone
  
    [save]:         save coordinates with a name
  
                    format: /e @tp save [name:str]
    [drop]:         drop a saved coordinates
  
                    format: /e @tp drop [name:str]
  
    [goto]:         goto a saved coordinates with 15 meters limit
                    format: /e @tp goto [name:str]
  
    [force-goto]:   goto a saved coordinates with no distance limit
                    format: /e @tp force-goto [name:str]

    relative coordinates teleport:
        format: /e @tp [direction] [distance:float]
        direction:  u/up,
                    d/down,
                    f/front,
                    l/left,
                    r/right,
                    b/back,
                    n/north,
                    e/east,
                    w/west,
                    s/south
```
