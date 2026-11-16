# ===== Начало эвента =====
scoreboard players set #busy hr 1
scoreboard players set @s hr_timer 0
scoreboard players set @s hr_state 0
scoreboard players set @s hr_ticks 0
scoreboard players set #taunt hr 0

# Запомнить, где стоял игрок (маркер + forceload, чтобы он не выгрузился)
summon minecraft:marker ~ ~ ~ {Tags:["hr_ret","hr_new"]}
tp @e[type=minecraft:marker,tag=hr_new,limit=1] @s
scoreboard players operation @e[type=minecraft:marker,tag=hr_new] hr_id = @s hr_id
execute as @e[type=minecraft:marker,tag=hr_new] at @s run forceload add ~ ~
tag @e[type=minecraft:marker,tag=hr_new] remove hr_new

tag @s add hr_in

# Телепорт на вершину белой лестницы, лицом вниз по ступеням
execute in minecraft:overworld run tp @s 10001.5 301 9999.5 0 10
effect give @s minecraft:blindness infinite 0 true
effect give @s minecraft:mining_fatigue infinite 4 true
effect give @s minecraft:resistance 2 4 true
playsound minecraft:ambient.cave master @s ~ ~ ~ 1 0.5
title @s times 5 40 10
title @s title {"text":"...","color":"white"}
title @s subtitle {"text":"Не оборачивайся.","color":"gray","italic":true}

# Он уже стоит за спиной
kill @e[type=minecraft:vindicator,tag=hr_golda]
execute in minecraft:overworld run summon minecraft:vindicator 10001.5 301 9996.5 {Tags:["hr_golda"],NoAI:1b,Silent:1b,Invulnerable:1b,PersistenceRequired:1b,CanPickUpLoot:0b,Rotation:[0f,0f],CustomName:{text:"Поборник",color:"dark_red"},CustomNameVisible:0b,equipment:{mainhand:{id:"minecraft:iron_axe",count:1}},drop_chances:{mainhand:0f},attributes:[{id:"minecraft:movement_speed",base:0.33d},{id:"minecraft:attack_damage",base:6d},{id:"minecraft:follow_range",base:64d}]}
