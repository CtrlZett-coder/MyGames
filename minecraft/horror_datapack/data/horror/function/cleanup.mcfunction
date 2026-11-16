kill @e[type=minecraft:vindicator,tag=hr_golda]
effect clear @s minecraft:blindness
effect clear @s minecraft:darkness
effect clear @s minecraft:mining_fatigue
tag @s remove hr_in
scoreboard players set @s hr_state 0
scoreboard players set @s hr_ticks 0
scoreboard players set @s hr_timer 0
scoreboard players set #busy hr 0
