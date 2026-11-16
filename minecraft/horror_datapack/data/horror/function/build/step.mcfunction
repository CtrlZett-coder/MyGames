fill ~-1 ~1 ~ ~1 ~4 ~ minecraft:air
fill ~-1 ~ ~ ~1 ~ ~ minecraft:quartz_stairs[facing=north]
setblock ~ ~4 ~ minecraft:light[level=10]
tp @s ~ ~-1 ~1
scoreboard players remove #step hr 1
execute if score #step hr matches 1.. at @s run function horror:build/step
