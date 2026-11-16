# ===== Постройка белой лестницы (x≈10000, z≈10000, y 300 → 201) =====
# Сплошной белый массив
execute in minecraft:overworld run fill 9999 196 9994 10003 306 10050 minecraft:white_concrete
execute in minecraft:overworld run fill 9999 196 10051 10003 306 10107 minecraft:white_concrete
# Площадка наверху
execute in minecraft:overworld run fill 10000 301 9995 10002 304 9999 minecraft:air
execute in minecraft:overworld run setblock 10001 304 9997 minecraft:light[level=12]
# 100 ступеней вниз
scoreboard players set #step hr 100
execute in minecraft:overworld run summon minecraft:marker 10001 300 10000 {Tags:["hr_builder"]}
execute as @e[type=minecraft:marker,tag=hr_builder,limit=1] at @s run function horror:build/step
kill @e[type=minecraft:marker,tag=hr_builder]
# Площадка внизу (спасение)
execute in minecraft:overworld run fill 10000 202 10100 10002 205 10106 minecraft:air
execute in minecraft:overworld run setblock 10001 205 10103 minecraft:light[level=15]
scoreboard players set #built hr 1
scoreboard players set #40 hr 40
tellraw @a [{"text":"[Хоррор] ","color":"dark_red"},{"text":"Белая лестница построена.","color":"gray"}]
