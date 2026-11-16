# Погиб на лестнице — убрать маркер, игрок возродится как обычно
tag @s add hr_me
execute as @e[type=minecraft:marker,tag=hr_ret] if score @s hr_id = @a[tag=hr_me,limit=1] hr_id run tag @s add hr_target
execute as @e[type=minecraft:marker,tag=hr_target] at @s run forceload remove ~ ~
kill @e[type=minecraft:marker,tag=hr_target]
tag @s remove hr_me
function horror:cleanup
tellraw @s [{"text":"<","color":"white"},{"text":"Поборник","color":"dark_red"},{"text":"> "},{"text":"Я же говорил, что найду.","color":"red"}]
