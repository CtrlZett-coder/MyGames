# Каждые ~2 секунды — шаги и дыхание за спиной
scoreboard players operation #m hr = @s hr_ticks
scoreboard players operation #m hr %= #40 hr
execute if score #m hr matches 0 run playsound minecraft:block.stone.step hostile @s ^ ^ ^-2 1 0.8
execute if score #m hr matches 20 run playsound minecraft:entity.vindicator.ambient hostile @s ^ ^ ^-3 0.4 0.6
