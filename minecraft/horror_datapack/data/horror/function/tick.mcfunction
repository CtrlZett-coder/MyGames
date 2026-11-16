# Выдать ID новым игрокам
execute as @a unless score @s hr_id matches 1.. run function horror:assign_id

# Смерть во время эвента
execute as @a[tag=hr_in,scores={hr_deaths=1..}] run function horror:died
scoreboard players reset @a hr_deaths

# Игрок вышел из игры во время эвента — освободить лестницу
execute if score #busy hr matches 1 unless entity @a[tag=hr_in] run function horror:abandon
# Игрок зашёл обратно, а эвент уже сброшен — вернуть домой
execute if score #busy hr matches 0 as @a[tag=hr_in] run function horror:escape

# Таймер (только когда лестница построена)
execute if score #built hr matches 1 as @a[tag=!hr_in,gamemode=!spectator] run function horror:timer

# Сам эвент
execute as @a[tag=hr_in] at @s run function horror:event_tick
