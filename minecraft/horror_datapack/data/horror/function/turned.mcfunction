# ===== Игрок обернулся =====
scoreboard players set @s hr_state 1
scoreboard players set #freeze hr 0
execute as @e[type=minecraft:vindicator,tag=hr_golda] run data merge entity @s {Silent:0b,CustomNameVisible:1b}
execute as @e[type=minecraft:vindicator,tag=hr_golda] at @s run tp @s ~ ~ ~ facing entity @a[tag=hr_in,limit=1]
effect clear @s minecraft:blindness
effect give @s minecraft:darkness infinite 0 true
playsound minecraft:entity.vindicator.celebrate hostile @s ~ ~ ~ 2 0.5
playsound minecraft:entity.warden.roar hostile @s ~ ~ ~ 1 1.5
title @s times 0 30 10
title @s title {"text":"ГОЛДА!!","color":"dark_red","bold":true}
title @s subtitle {"text":"БЕГИ ВНИЗ","color":"red"}
tellraw @s [{"text":"<","color":"white"},{"text":"Поборник","color":"dark_red"},{"text":"> "},{"text":"ГОЛДА!!","color":"red","bold":true}]
