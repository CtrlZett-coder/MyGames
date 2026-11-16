# ===== Игрок спасся — вернуть туда, где он стоял =====
tag @s add hr_me
execute as @e[type=minecraft:marker,tag=hr_ret] if score @s hr_id = @a[tag=hr_me,limit=1] hr_id run tag @s add hr_target
tp @s @e[type=minecraft:marker,tag=hr_target,limit=1]
execute as @e[type=minecraft:marker,tag=hr_target] at @s run forceload remove ~ ~
kill @e[type=minecraft:marker,tag=hr_target]
tag @s remove hr_me
function horror:cleanup
title @s times 5 30 20
title @s title {"text":""}
title @s subtitle {"text":"...ты сбежал. Пока что.","color":"gray","italic":true}
playsound minecraft:block.portal.travel master @s ~ ~ ~ 0.3 1.5
