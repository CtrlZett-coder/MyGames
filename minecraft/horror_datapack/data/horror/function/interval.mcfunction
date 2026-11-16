# Поменять интервал: /scoreboard players set #interval hr <тики>  (20 тиков = 1 сек)
tellraw @s [{"text":"Интервал сейчас (тики): ","color":"gray"},{"score":{"name":"#interval","objective":"hr"},"color":"white"}]
