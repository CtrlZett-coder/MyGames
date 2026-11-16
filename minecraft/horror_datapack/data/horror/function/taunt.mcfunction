scoreboard players set #taunt hr 0
execute store result score #r hr run random value 1..3
execute if score #r hr matches 1 run tellraw @s [{"text":"<","color":"white"},{"text":"Поборник","color":"dark_red"},{"text":"> "},{"text":"Кабилджон, я тебя найду!","color":"red"}]
execute if score #r hr matches 2 run tellraw @s [{"text":"<","color":"white"},{"text":"Поборник","color":"dark_red"},{"text":"> "},{"text":"Капзда тебе!","color":"red"}]
execute if score #r hr matches 3 run tellraw @s [{"text":"<","color":"white"},{"text":"Поборник","color":"dark_red"},{"text":"> "},{"text":"Ты с*ка х*есос бл*ть!","color":"red"}]
playsound minecraft:entity.vindicator.ambient hostile @s ~ ~ ~ 1.5 0.6
