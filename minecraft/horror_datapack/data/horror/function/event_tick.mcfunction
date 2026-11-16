scoreboard players add @s hr_ticks 1

# --- Фаза 0: он идёт следом, пока игрок не обернётся ---
execute if score @s hr_state matches 0 if entity @s[x=9990,dx=20,y=0,dy=320,z=10003,dz=200] as @e[type=minecraft:vindicator,tag=hr_golda] at @a[tag=hr_in,limit=1] run tp @s ~ ~3 ~-3 facing entity @a[tag=hr_in,limit=1]
execute if score @s hr_state matches 0 if score @s hr_ticks matches 60.. run function horror:footsteps
# Обернулся? (смотрит не в сторону спуска). Первую секунду не проверяем
execute if score @s hr_state matches 0 if score @s hr_ticks matches 20.. unless entity @s[y_rotation=-100..100] run function horror:turned

# --- Фаза 1: замер перед броском ---
execute if score @s hr_state matches 1 run scoreboard players add #freeze hr 1
execute if score @s hr_state matches 1 if score #freeze hr matches 15.. run function horror:chase

# --- Фаза 2: погоня, оскорбления в чат ---
execute if score @s hr_state matches 2 run scoreboard players add #taunt hr 1
execute if score @s hr_state matches 2 if score #taunt hr matches 50.. run function horror:taunt


# --- Добежал до низа — спасён ---
execute if entity @s[x=9998,y=190,z=10100,dx=6,dy=25,dz=10] run function horror:escape
