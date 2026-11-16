scoreboard players add @s hr_timer 1
execute if score @s hr_timer >= #interval hr if score #busy hr matches 0 run function horror:start
# Если лестница занята другим игроком — подождать
execute if score @s hr_timer > #interval hr run scoreboard players operation @s hr_timer = #interval hr
