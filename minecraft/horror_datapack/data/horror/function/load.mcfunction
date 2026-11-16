# ===== Хоррор: Белая лестница — загрузка =====
scoreboard objectives add hr_timer dummy
scoreboard objectives add hr_id dummy
scoreboard objectives add hr_state dummy
scoreboard objectives add hr_ticks dummy
scoreboard objectives add hr_deaths deathCount
scoreboard objectives add hr dummy

# Интервал между эвентами в тиках (600 = 30 секунд)
execute unless score #interval hr matches 1.. run scoreboard players set #interval hr 600
execute unless score #next_id hr matches 1.. run scoreboard players set #next_id hr 1
execute unless score #busy hr matches 0.. run scoreboard players set #busy hr 0
scoreboard players set #40 hr 40

# Лестница строится один раз (через 2 сек, чтобы чанки успели загрузиться)
execute in minecraft:overworld run forceload add 9984 9984 10015 10111
execute unless score #built hr matches 1 run schedule function horror:build/start 40t

tellraw @a [{"text":"[Хоррор] ","color":"dark_red"},{"text":"Белая лестница загружена. Беги...","color":"gray"}]
