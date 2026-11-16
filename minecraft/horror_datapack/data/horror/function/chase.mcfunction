# ===== Бросается в погоню =====
scoreboard players set @s hr_state 2
scoreboard players set #taunt hr 40
execute as @e[type=minecraft:vindicator,tag=hr_golda] run data merge entity @s {NoAI:0b}
playsound minecraft:entity.vindicator.angry hostile @s ~ ~ ~ 2 0.7
