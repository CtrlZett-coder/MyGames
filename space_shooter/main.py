import pygame
import random
import sys
import math

# ─── Constants ────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 900
SCREEN_HEIGHT = 600
FPS = 60

# ─── Colours ──────────────────────────────────────────────────────────────────
BLACK     = (0,   0,   0)
WHITE     = (255, 255, 255)
RED       = (220, 50,  50)
DARK_RED  = (140, 0,   0)
YELLOW    = (255, 220, 0)
CYAN      = (0,   200, 255)
ORANGE    = (255, 140, 0)
GREEN     = (50,  200, 50)
GRAY      = (150, 150, 150)
DARK_GRAY = (40,  40,  40)
BLUE      = (50,  100, 255)
PURPLE    = (160, 30,  220)


# ─── Star (parallax background) ───────────────────────────────────────────────
class Star:
    def __init__(self):
        self._reset(spawn_anywhere=True)

    def _reset(self, spawn_anywhere=False):
        self.x = random.randint(0, SCREEN_WIDTH) if spawn_anywhere else SCREEN_WIDTH + 4
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.speed = random.uniform(0.8, 4.0)
        self.radius = 1 if self.speed < 2 else (2 if self.speed < 3.2 else 3)
        self.bright = random.randint(120, 255)

    def update(self):
        self.x -= self.speed
        if self.x < 0:
            self._reset()

    def draw(self, surf):
        c = (self.bright,) * 3
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.radius)


# ─── Bullet (player) ──────────────────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.speed = 14
        self.active = True
        self.W, self.H = 18, 5

    def update(self):
        self.x += self.speed
        if self.x > SCREEN_WIDTH + 20:
            self.active = False

    def draw(self, surf):
        ix, iy = int(self.x), int(self.y)
        pygame.draw.rect(surf, YELLOW, (ix, iy - 2, self.W, self.H))
        pygame.draw.rect(surf, WHITE,  (ix + 4, iy - 1, self.W - 8, 3))

    def get_rect(self):
        return pygame.Rect(self.x, self.y - 2, self.W, self.H)


# ─── Enemy bullet ─────────────────────────────────────────────────────────────
class EnemyBullet:
    def __init__(self, x, y, angle_deg=180):
        self.x = float(x)
        self.y = float(y)
        rad = math.radians(angle_deg)
        speed = 6
        self.vx = math.cos(rad) * speed
        self.vy = math.sin(rad) * speed
        self.active = True
        self.R = 5

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x < -20 or self.y < -20 or self.y > SCREEN_HEIGHT + 20:
            self.active = False

    def draw(self, surf):
        pygame.draw.circle(surf, RED,    (int(self.x), int(self.y)), self.R)
        pygame.draw.circle(surf, ORANGE, (int(self.x), int(self.y)), self.R - 2)

    def get_rect(self):
        return pygame.Rect(self.x - self.R, self.y - self.R, self.R*2, self.R*2)


# ─── Player ship ──────────────────────────────────────────────────────────────
class Player:
    def __init__(self):
        self.x = 120.0
        self.y = float(SCREEN_HEIGHT // 2)
        self.speed = 5
        self.max_health = 3
        self.health = self.max_health
        self.shoot_cooldown = 0
        self.shoot_delay   = 14          # frames between shots
        self.inv_frames    = 0           # invincibility after hit
        self.bullets: list[Bullet] = []

    def update(self, keys):
        if keys[pygame.K_UP]    or keys[pygame.K_w]: self.y -= self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self.y += self.speed
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.x += self.speed

        self.x = max(30, min(SCREEN_WIDTH // 2, self.x))
        self.y = max(30, min(SCREEN_HEIGHT - 30, self.y))

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if keys[pygame.K_SPACE] and self.shoot_cooldown == 0:
            self._shoot()

        if self.inv_frames > 0:
            self.inv_frames -= 1

        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.active]

    def _shoot(self):
        self.bullets.append(Bullet(self.x + 32, self.y))
        self.shoot_cooldown = self.shoot_delay

    def take_damage(self) -> bool:
        if self.inv_frames == 0:
            self.health -= 1
            self.inv_frames = 90
            return True
        return False

    def draw(self, surf):
        if self.inv_frames > 0 and (self.inv_frames // 5) % 2 == 0:
            return
        x, y = int(self.x), int(self.y)

        # --- wings ---
        wing_top = [(x-22,y-10), (x-5,y-26), (x+12,y-6)]
        wing_bot = [(x-22,y+10), (x-5,y+26), (x+12,y+6)]
        pygame.draw.polygon(surf, BLUE,        wing_top)
        pygame.draw.polygon(surf, BLUE,        wing_bot)
        pygame.draw.polygon(surf, (0,60,180),  wing_top, 1)
        pygame.draw.polygon(surf, (0,60,180),  wing_bot, 1)

        # --- main body ---
        body = [(x-28,y+12), (x+32,y), (x-28,y-12)]
        pygame.draw.polygon(surf, CYAN, body)
        pygame.draw.polygon(surf, (0,160,210), body, 1)

        # --- engine exhaust (animated) ---
        flame_len = random.randint(12, 22)
        flame_pts = [(x-28,y-5), (x-28-flame_len, y), (x-28,y+5)]
        pygame.draw.polygon(surf, ORANGE, flame_pts)
        pygame.draw.polygon(surf, YELLOW, [(x-28,y-2),(x-28-flame_len//2,y),(x-28,y+2)])

        # --- cockpit ---
        pygame.draw.circle(surf, WHITE, (x+12, y), 6)
        pygame.draw.circle(surf, CYAN,  (x+12, y), 4)

        # --- bullets ---
        for b in self.bullets:
            b.draw(surf)

    def get_rect(self):
        return pygame.Rect(self.x - 26, self.y - 13, 52, 26)


# ─── Enemy ────────────────────────────────────────────────────────────────────
class Enemy:
    TYPES = {
        'fighter': dict(speed=(3.0, 5.5), hp=1, w=42, h=26, score=100,
                        shoot_cd=(70, 140),  color=RED,    size='small'),
        'scout':   dict(speed=(5.5, 8.5), hp=1, w=30, h=20, score=150,
                        shoot_cd=(90, 180),  color=PURPLE, size='small'),
        'heavy':   dict(speed=(1.5, 2.8), hp=3, w=56, h=38, score=300,
                        shoot_cd=(50, 100),  color=ORANGE, size='large'),
    }

    def __init__(self, kind: str):
        cfg = self.TYPES[kind]
        self.kind   = kind
        self.hp     = cfg['hp']
        self.max_hp = cfg['hp']
        self.W, self.H = cfg['w'], cfg['h']
        self.score_val  = cfg['score']
        self.color  = cfg['color']

        self.x = float(SCREEN_WIDTH + self.W)
        self.y = float(random.randint(50, SCREEN_HEIGHT - 50))
        self.speed = random.uniform(*cfg['speed'])
        self.vy    = random.uniform(-1.2, 1.2)

        lo, hi = cfg['shoot_cd']
        self.shoot_timer = random.randint(lo, hi)
        self.shoot_delay_range = (lo, hi)
        self.bullets: list[EnemyBullet] = []
        self.active = True

    def update(self):
        self.x -= self.speed
        self.y += self.vy
        if self.y < 40 or self.y > SCREEN_HEIGHT - 40:
            self.vy *= -1
        if self.x < -self.W - 20:
            self.active = False

        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            lo, hi = self.shoot_delay_range
            self.shoot_timer = random.randint(lo, hi)
            # Heavy shoots 3 spread bullets
            if self.kind == 'heavy':
                for ang in [175, 180, 185]:
                    self.bullets.append(EnemyBullet(self.x - self.W//2, self.y, ang))
            else:
                self.bullets.append(EnemyBullet(self.x - self.W//2, self.y))

        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.active]

    def take_hit(self) -> bool:
        self.hp -= 1
        return self.hp <= 0

    def draw(self, surf):
        x, y = int(self.x), int(self.y)

        if self.kind == 'fighter':
            body = [(x+20,y), (x-20,y-13), (x-20,y+13)]
            pygame.draw.polygon(surf, RED,      body)
            wt = [(x-10,y-13),(x+2,y-26),(x+12,y-5)]
            wb = [(x-10,y+13),(x+2,y+26),(x+12,y+5)]
            pygame.draw.polygon(surf, DARK_RED, wt)
            pygame.draw.polygon(surf, DARK_RED, wb)
            pygame.draw.circle(surf, ORANGE, (x+18, y), 4)
            pygame.draw.circle(surf, YELLOW, (x+18, y), 2)

        elif self.kind == 'scout':
            body = [(x+14,y),(x-14,y-10),(x-14,y+10)]
            pygame.draw.polygon(surf, PURPLE, body)
            pygame.draw.circle(surf, WHITE, (x+4, y), 4)
            pygame.draw.circle(surf, PURPLE,(x+4, y), 2)

        else:  # heavy
            pygame.draw.ellipse(surf, ORANGE, (x-27, y-18, 56, 38))
            pygame.draw.ellipse(surf, (200,90,0),(x-13,y-10,28,22))
            # Gun barrels
            pygame.draw.rect(surf, GRAY, (x+15, y-22, 18, 6))
            pygame.draw.rect(surf, GRAY, (x+15, y+16,  18, 6))
            # Engine
            pygame.draw.circle(surf, YELLOW, (x+26, y), 7)
            pygame.draw.circle(surf, ORANGE, (x+26, y), 4)
            # HP bar
            bar_w = 44
            filled = max(0, int(bar_w * self.hp / self.max_hp))
            pygame.draw.rect(surf, DARK_GRAY, (x-22, y-30, bar_w, 6))
            pygame.draw.rect(surf, GREEN,     (x-22, y-30, filled, 6))

        for b in self.bullets:
            b.draw(surf)

    def get_rect(self):
        return pygame.Rect(self.x - self.W//2, self.y - self.H//2, self.W, self.H)


# ─── Explosion ────────────────────────────────────────────────────────────────
class Explosion:
    def __init__(self, x, y, big=False):
        self.x, self.y = x, y
        self.max_r  = 45 if big else 25
        self.frame  = 0
        self.total  = 22
        self.active = True
        # random sparks
        self.sparks = [(random.uniform(0, math.tau),
                        random.uniform(1.5, 4.5)) for _ in range(12 if big else 6)]

    def update(self):
        self.frame += 1
        if self.frame >= self.total:
            self.active = False

    def draw(self, surf):
        t = self.frame / self.total
        r = int(self.max_r * math.sin(t * math.pi))
        if r <= 0:
            return
        alpha = int(255 * (1 - t))
        col_out = (255, int(180*(1-t)), 0)
        col_in  = (255, 255, int(200*(1-t)))
        pygame.draw.circle(surf, col_out, (int(self.x), int(self.y)), r)
        if r > 5:
            pygame.draw.circle(surf, col_in, (int(self.x), int(self.y)), r//2)
        # sparks
        for ang, speed in self.sparks:
            sx = self.x + math.cos(ang) * speed * self.frame
            sy = self.y + math.sin(ang) * speed * self.frame
            pygame.draw.circle(surf, YELLOW, (int(sx), int(sy)), 2)


# ─── Main Game class ──────────────────────────────────────────────────────────
class Game:
    ENEMY_WEIGHTS = {
        1: {'fighter':8, 'scout':2, 'heavy':0},
        2: {'fighter':6, 'scout':3, 'heavy':1},
        3: {'fighter':5, 'scout':3, 'heavy':2},
    }

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("🚀 Space Shooter")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock  = pygame.time.Clock()
        self.font   = pygame.font.Font(None, 36)
        self.font_b = pygame.font.Font(None, 74)
        self.font_s = pygame.font.Font(None, 26)
        self._reset()

    def _reset(self):
        self.player     = Player()
        self.enemies:    list[Enemy]     = []
        self.explosions: list[Explosion] = []
        self.stars = [Star() for _ in range(180)]
        self.score       = 0
        self.level       = 1
        self.kills       = 0
        self.kills_level = 10
        self.spawn_timer = 0
        self.spawn_delay = 90
        self.state       = 'playing'   # 'playing' | 'game_over'

    # ── Enemy spawning ───────────────────────────────────────────────────────
    def _spawn_enemy(self):
        lv = min(self.level, 3)
        w  = self.ENEMY_WEIGHTS[lv]
        kinds  = list(w.keys())
        weights= list(w.values())
        kind = random.choices(kinds, weights=weights)[0]
        self.enemies.append(Enemy(kind))

    # ── Collision detection ──────────────────────────────────────────────────
    def _collisions(self):
        p_rect = self.player.get_rect()

        # Player bullets vs enemies
        for bullet in self.player.bullets:
            if not bullet.active:
                continue
            br = bullet.get_rect()
            for enemy in self.enemies:
                if enemy.active and br.colliderect(enemy.get_rect()):
                    bullet.active = False
                    if enemy.take_hit():
                        self.score += enemy.score_val
                        self.kills += 1
                        self.explosions.append(Explosion(enemy.x, enemy.y, big=True))
                        enemy.active = False
                    else:
                        self.explosions.append(Explosion(enemy.x, enemy.y, big=False))
                    break

        # Enemy bullets vs player
        for enemy in self.enemies:
            for eb in enemy.bullets:
                if eb.active and eb.get_rect().colliderect(p_rect):
                    eb.active = False
                    if self.player.take_damage():
                        self.explosions.append(Explosion(self.player.x, self.player.y))

        # Enemy ram vs player
        for enemy in self.enemies:
            if enemy.active and enemy.get_rect().colliderect(p_rect):
                enemy.active = False
                self.explosions.append(Explosion(enemy.x, enemy.y, big=True))
                if self.player.take_damage():
                    self.explosions.append(Explosion(self.player.x, self.player.y))

        if self.player.health <= 0:
            self.state = 'game_over'

    # ── Level progression ────────────────────────────────────────────────────
    def _check_level(self):
        threshold = self.kills_level * self.level
        if self.kills >= threshold:
            self.level += 1
            self.spawn_delay = max(28, 90 - self.level * 10)

    # ── HUD ──────────────────────────────────────────────────────────────────
    def _draw_hud(self):
        # Score
        s = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(s, (10, 10))

        # Level
        l = self.font.render(f"Level: {self.level}", True, YELLOW)
        self.screen.blit(l, (10, 44))

        # Lives (ship icons)
        lbl = self.font_s.render("Lives:", True, WHITE)
        self.screen.blit(lbl, (SCREEN_WIDTH - 195, 12))
        for i in range(self.player.max_health):
            col = CYAN if i < self.player.health else DARK_GRAY
            cx = SCREEN_WIDTH - 130 + i * 38
            cy = 22
            pts = [(cx-14,cy+7),(cx+16,cy),(cx-14,cy-7)]
            pygame.draw.polygon(self.screen, col, pts)

        # Kill-progress bar (centre-top)
        bx = SCREEN_WIDTH//2 - 80
        by = 8
        bw = 160
        bh = 14
        threshold = self.kills_level * self.level
        filled = min(bw, int(bw * self.kills / threshold)) if threshold else bw
        pygame.draw.rect(self.screen, DARK_GRAY, (bx, by, bw, bh))
        pygame.draw.rect(self.screen, GREEN,     (bx, by, filled, bh))
        pygame.draw.rect(self.screen, GRAY,      (bx, by, bw, bh), 1)
        pt = self.font_s.render(f"{self.kills}/{threshold}", True, WHITE)
        self.screen.blit(pt, pt.get_rect(center=(SCREEN_WIDTH//2, by + bh + 10)))

        # Controls hint (first 4 s)
        hint = self.font_s.render("WASD / Arrows — move    SPACE — shoot", True, GRAY)
        self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, SCREEN_HEIGHT - 28))

    # ── Game-over overlay ────────────────────────────────────────────────────
    def _draw_game_over(self):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))

        def centre(surf, y):
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, y)))

        centre(self.font_b.render("GAME  OVER", True, RED),               SCREEN_HEIGHT//2 - 80)
        centre(self.font.render(f"Score: {self.score}", True, WHITE),      SCREEN_HEIGHT//2 - 10)
        centre(self.font.render(f"Level reached: {self.level}", True, YELLOW), SCREEN_HEIGHT//2 + 35)
        centre(self.font.render("R — restart     Q — quit", True, CYAN),   SCREEN_HEIGHT//2 + 100)

    # ── Main loop ────────────────────────────────────────────────────────────
    def run(self):
        while True:
            # --- Events ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        pygame.quit(); sys.exit()
                    if event.key == pygame.K_r and self.state == 'game_over':
                        self._reset()

            # --- Update ---
            if self.state == 'playing':
                keys = pygame.key.get_pressed()
                self.player.update(keys)

                self.spawn_timer += 1
                if self.spawn_timer >= self.spawn_delay:
                    self._spawn_enemy()
                    self.spawn_timer = 0

                for e in self.enemies:
                    e.update()
                self.enemies = [e for e in self.enemies if e.active]

                self._collisions()

                for ex in self.explosions:
                    ex.update()
                self.explosions = [ex for ex in self.explosions if ex.active]

                self._check_level()

            # --- Draw ---
            self.screen.fill(BLACK)

            for star in self.stars:
                star.update()
                star.draw(self.screen)

            for e in self.enemies:
                e.draw(self.screen)

            for ex in self.explosions:
                ex.draw(self.screen)

            self.player.draw(self.screen)
            self._draw_hud()

            if self.state == 'game_over':
                self._draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
