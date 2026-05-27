import pygame
import random
import sys
import math

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# ─── Constants ────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 900
SCREEN_HEIGHT = 600
FPS           = 60

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


# ══════════════════════════════════════════════════════════════════════════════
#  SOUND MANAGER  — procedural audio via numpy, gracefully silent without it
# ══════════════════════════════════════════════════════════════════════════════
class SoundManager:
    def __init__(self):
        self.enabled = False
        self._sounds: dict = {}
        self._init()

    def _init(self):
        if not _HAS_NUMPY:
            return
        try:
            pygame.mixer.pre_init(22050, -16, 2, 512)
            pygame.mixer.init()
            sr = 22050
            self._sounds = {
                'shoot':   self._sine(sr, 820,  0.07, decay=35, vol=0.22),
                'boom':    self._noise(sr, 0.30, decay=9,  vol=0.55),
                'hit':     self._sine(sr, 200,  0.18, decay=12, vol=0.45),
                'powerup': self._rising(sr, 440, 880, 0.35, vol=0.40),
                'shield_break': self._sine(sr, 300, 0.25, decay=8, vol=0.50),
            }
            self._play_ambient(sr)
            self.enabled = True
        except Exception:
            pass

    # ── waveform builders ──────────────────────────────────────────────────
    @staticmethod
    def _to_sound(arr: 'np.ndarray') -> pygame.mixer.Sound:
        data = np.ascontiguousarray(
            np.column_stack([arr, arr]).astype(np.int16)
        )
        return pygame.sndarray.make_sound(data)

    def _sine(self, sr, freq, dur, decay=8.0, vol=0.35):
        t = np.linspace(0, dur, int(sr * dur), False)
        w = np.sin(2 * np.pi * freq * t) * np.exp(-decay * t) * vol * 32767
        return self._to_sound(w)

    def _noise(self, sr, dur, decay=10.0, vol=0.4):
        n = int(sr * dur)
        t = np.linspace(0, dur, n, False)
        w = np.random.uniform(-1, 1, n) * np.exp(-decay * t) * vol * 32767
        return self._to_sound(w)

    def _rising(self, sr, f0, f1, dur, vol=0.35):
        n = int(sr * dur)
        t = np.linspace(0, dur, n, False)
        freq = f0 + (f1 - f0) * (t / dur)
        w = np.sin(2 * np.pi * np.cumsum(freq) / sr)
        w = w * np.exp(-2 * t) * vol * 32767
        return self._to_sound(w)

    def _play_ambient(self, sr=22050):
        dur = 5.0
        n   = int(sr * dur)
        t   = np.linspace(0, dur, n, False)
        wave = (np.sin(2*np.pi*55*t)  * 0.30
              + np.sin(2*np.pi*82*t)  * 0.20
              + np.sin(2*np.pi*110*t) * 0.12
              + np.sin(2*np.pi*165*t) * 0.08)
        wave *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.4 * t)  # LFO
        fl    = int(sr * 0.5)
        fade  = np.ones(n)
        fade[:fl] = np.linspace(0, 1, fl)
        fade[-fl:]= np.linspace(1, 0, fl)
        wave = (wave * fade * 32767 * 0.45).astype(np.int16)
        snd  = pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack([wave, wave])))
        snd.set_volume(0.35)
        snd.play(-1)   # loop forever

    def play(self, name: str):
        if self.enabled and name in self._sounds:
            self._sounds[name].play()


# ══════════════════════════════════════════════════════════════════════════════
#  STARS  — parallax scrolling background
# ══════════════════════════════════════════════════════════════════════════════
class Star:
    def __init__(self):
        self._reset(anywhere=True)

    def _reset(self, anywhere=False):
        self.x      = random.randint(0, SCREEN_WIDTH) if anywhere else SCREEN_WIDTH + 4
        self.y      = random.randint(0, SCREEN_HEIGHT)
        self.speed  = random.uniform(0.8, 4.0)
        self.radius = 1 if self.speed < 2 else (2 if self.speed < 3.2 else 3)
        self.bright = random.randint(120, 255)

    def update(self):
        self.x -= self.speed
        if self.x < 0:
            self._reset()

    def draw(self, surf):
        pygame.draw.circle(surf, (self.bright,)*3,
                           (int(self.x), int(self.y)), self.radius)


# ══════════════════════════════════════════════════════════════════════════════
#  BULLETS
# ══════════════════════════════════════════════════════════════════════════════
class Bullet:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.speed     = 14
        self.W, self.H = 18, 5
        self.active    = True

    def update(self):
        self.x += self.speed
        if self.x > SCREEN_WIDTH + 20:
            self.active = False

    def draw(self, surf):
        ix, iy = int(self.x), int(self.y)
        pygame.draw.rect(surf, YELLOW, (ix, iy-2, self.W, self.H))
        pygame.draw.rect(surf, WHITE,  (ix+4, iy-1, self.W-8, 3))

    def get_rect(self):
        return pygame.Rect(self.x, self.y-2, self.W, self.H)


class EnemyBullet:
    def __init__(self, x, y, angle_deg=180):
        self.x, self.y = float(x), float(y)
        rad = math.radians(angle_deg)
        spd = 6
        self.vx, self.vy = math.cos(rad)*spd, math.sin(rad)*spd
        self.active = True
        self.R = 5

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x < -20 or self.y < -20 or self.y > SCREEN_HEIGHT + 20:
            self.active = False

    def draw(self, surf):
        pygame.draw.circle(surf, RED,    (int(self.x), int(self.y)), self.R)
        pygame.draw.circle(surf, ORANGE, (int(self.x), int(self.y)), self.R-2)

    def get_rect(self):
        return pygame.Rect(self.x-self.R, self.y-self.R, self.R*2, self.R*2)


# ══════════════════════════════════════════════════════════════════════════════
#  POWER-UPS
# ══════════════════════════════════════════════════════════════════════════════
class PowerUp:
    """
    Four types:
      'double' — double-shot for 10 s        (yellow)
      'shield' — absorbs one hit             (cyan)
      'slow'   — enemies half-speed for 5 s  (purple)
      'life'   — +1 HP                       (red)
    """
    CONFIGS = {
        'double': dict(color=YELLOW,          label='2×',  duration=600, desc='Double Shot'),
        'shield': dict(color=CYAN,            label='SHD', duration=0,   desc='Shield'),
        'slow':   dict(color=PURPLE,          label='SLW', duration=300, desc='Slow Time'),
        'life':   dict(color=(220, 80, 100),  label='+HP', duration=0,   desc='Extra Life'),
    }

    def __init__(self, x, y, kind=None):
        self.kind    = kind or random.choice(list(self.CONFIGS.keys()))
        cfg          = self.CONFIGS[self.kind]
        self.color   = cfg['color']
        self.label   = cfg['label']
        self.duration = cfg['duration']
        self.desc    = cfg['desc']
        self.x, self.y = float(x), float(y)
        self.vx      = -2.0
        self.vy      = random.uniform(-0.8, 0.8)
        self.angle   = 0.0
        self.active  = True
        self.R       = 15

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.angle += 4
        if self.y < self.R or self.y > SCREEN_HEIGHT - self.R:
            self.vy *= -1
        if self.x < -40:
            self.active = False

    def draw(self, surf, font_s):
        if not self.active:
            return
        x, y = int(self.x), int(self.y)

        # Pulsing glow aura
        pulse = int(4 * math.sin(math.radians(self.angle * 3)))
        for r, alpha in [(self.R + pulse + 7, 50), (self.R + pulse + 3, 90)]:
            s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
            surf.blit(s, (x-r, y-r))

        # Spinning ring
        angle_rad = math.radians(self.angle)
        for i in range(6):
            a = angle_rad + i * math.pi / 3
            px = x + int((self.R+1) * math.cos(a))
            py = y + int((self.R+1) * math.sin(a))
            pygame.draw.circle(surf, WHITE, (px, py), 2)

        pygame.draw.circle(surf, self.color, (x, y), self.R)
        pygame.draw.circle(surf, WHITE,      (x, y), self.R, 2)

        t = font_s.render(self.label, True, BLACK)
        surf.blit(t, t.get_rect(center=(x, y)))

    def get_rect(self):
        return pygame.Rect(self.x-self.R, self.y-self.R, self.R*2, self.R*2)


# ══════════════════════════════════════════════════════════════════════════════
#  PLAYER
# ══════════════════════════════════════════════════════════════════════════════
class Player:
    MAX_HP = 5

    def __init__(self):
        self.x, self.y   = 120.0, float(SCREEN_HEIGHT // 2)
        self.speed        = 5
        self.health       = 3
        self.shoot_cd     = 0
        self.shoot_delay  = 14
        self.inv_frames   = 0
        self.just_shot    = False
        self.bullets: list[Bullet] = []
        # power-up state
        self.double_timer = 0   # frames left for double shot
        self.slow_timer   = 0   # frames left for slow time
        self.has_shield   = False

    def update(self, keys):
        if keys[pygame.K_UP]    or keys[pygame.K_w]: self.y -= self.speed
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self.y += self.speed
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.x += self.speed

        self.x = max(30, min(SCREEN_WIDTH // 2, self.x))
        self.y = max(30, min(SCREEN_HEIGHT - 30, self.y))

        if self.shoot_cd > 0:
            self.shoot_cd -= 1

        self.just_shot = False
        if keys[pygame.K_SPACE] and self.shoot_cd == 0:
            self._shoot()

        if self.inv_frames   > 0: self.inv_frames   -= 1
        if self.double_timer > 0: self.double_timer -= 1
        if self.slow_timer   > 0: self.slow_timer   -= 1

        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.active]

    def _shoot(self):
        bx = self.x + 32
        if self.double_timer > 0:
            self.bullets.append(Bullet(bx, self.y - 9))
            self.bullets.append(Bullet(bx, self.y + 9))
        else:
            self.bullets.append(Bullet(bx, self.y))
        self.shoot_cd  = self.shoot_delay
        self.just_shot = True

    def take_damage(self) -> bool:
        if self.has_shield:
            self.has_shield = False
            self.inv_frames = 30
            return False          # shield absorbed — no real damage
        if self.inv_frames == 0:
            self.health -= 1
            self.inv_frames = 90
            return True
        return False

    def apply_powerup(self, kind: str):
        if kind == 'double':
            self.double_timer = 600
        elif kind == 'shield':
            self.has_shield   = True
        elif kind == 'slow':
            self.slow_timer   = 300
        elif kind == 'life':
            self.health = min(self.health + 1, self.MAX_HP)

    @property
    def slow_active(self) -> bool:
        return self.slow_timer > 0

    def draw(self, surf):
        if self.inv_frames > 0 and (self.inv_frames // 5) % 2 == 0:
            return
        x, y = int(self.x), int(self.y)

        # Shield aura
        if self.has_shield:
            r = 38
            s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 200, 255, 55), (r, r), r)
            surf.blit(s, (x-r, y-r))
            pygame.draw.circle(surf, CYAN, (x, y), r, 2)

        # Wings
        wing_top = [(x-22,y-10),(x-5,y-26),(x+12,y-6)]
        wing_bot = [(x-22,y+10),(x-5,y+26),(x+12,y+6)]
        pygame.draw.polygon(surf, BLUE,       wing_top)
        pygame.draw.polygon(surf, BLUE,       wing_bot)
        pygame.draw.polygon(surf, (0,60,180), wing_top, 1)
        pygame.draw.polygon(surf, (0,60,180), wing_bot, 1)

        # Body
        body = [(x-28,y+12),(x+32,y),(x-28,y-12)]
        body_col = CYAN if self.double_timer == 0 else YELLOW
        pygame.draw.polygon(surf, body_col,       body)
        pygame.draw.polygon(surf, (0,160,210),    body, 1)

        # Engine flame (animated)
        fl = random.randint(12, 22)
        pygame.draw.polygon(surf, ORANGE, [(x-28,y-5),(x-28-fl,y),(x-28,y+5)])
        pygame.draw.polygon(surf, YELLOW, [(x-28,y-2),(x-28-fl//2,y),(x-28,y+2)])

        # Cockpit
        pygame.draw.circle(surf, WHITE, (x+12, y), 6)
        pygame.draw.circle(surf, CYAN,  (x+12, y), 4)

        # Double-shot rails (visual cue)
        if self.double_timer > 0:
            pygame.draw.line(surf, YELLOW, (x, y-26), (x+36, y-26), 1)
            pygame.draw.line(surf, YELLOW, (x, y+26), (x+36, y+26), 1)

        for b in self.bullets:
            b.draw(surf)

    def get_rect(self):
        return pygame.Rect(self.x-26, self.y-13, 52, 26)


# ══════════════════════════════════════════════════════════════════════════════
#  ENEMY
# ══════════════════════════════════════════════════════════════════════════════
class Enemy:
    TYPES = {
        'fighter': dict(speed=(3.0,5.5), hp=1, w=42, h=26, score=100,
                        shoot_cd=(70,140), drop=0.20),
        'scout':   dict(speed=(5.5,8.5), hp=1, w=30, h=20, score=150,
                        shoot_cd=(90,180), drop=0.20),
        'heavy':   dict(speed=(1.5,2.8), hp=3, w=56, h=38, score=300,
                        shoot_cd=(50,100), drop=0.45),
    }

    def __init__(self, kind: str):
        cfg = self.TYPES[kind]
        self.kind  = kind
        self.hp    = cfg['hp']
        self.max_hp= cfg['hp']
        self.W, self.H = cfg['w'], cfg['h']
        self.score_val   = cfg['score']
        self.drop_chance = cfg['drop']
        self.x = float(SCREEN_WIDTH + self.W)
        self.y = float(random.randint(50, SCREEN_HEIGHT-50))
        self.speed = random.uniform(*cfg['speed'])
        self.vy    = random.uniform(-1.2, 1.2)
        lo, hi = cfg['shoot_cd']
        self.shoot_timer = random.randint(lo, hi)
        self.shoot_range = (lo, hi)
        self.bullets: list[EnemyBullet] = []
        self.active = True

    def update(self, time_scale: float = 1.0):
        self.x -= self.speed * time_scale
        self.y += self.vy   * time_scale
        if self.y < 40 or self.y > SCREEN_HEIGHT - 40:
            self.vy *= -1
        if self.x < -self.W - 20:
            self.active = False

        self.shoot_timer -= time_scale
        if self.shoot_timer <= 0:
            lo, hi = self.shoot_range
            self.shoot_timer = random.randint(lo, hi)
            bx = self.x - self.W // 2
            if self.kind == 'heavy':
                for ang in [175, 180, 185]:
                    self.bullets.append(EnemyBullet(bx, self.y, ang))
            else:
                self.bullets.append(EnemyBullet(bx, self.y))

        for b in self.bullets:
            b.update()
        self.bullets = [b for b in self.bullets if b.active]

    def take_hit(self) -> bool:
        self.hp -= 1
        return self.hp <= 0

    def should_drop(self) -> bool:
        return random.random() < self.drop_chance

    def draw(self, surf):
        x, y = int(self.x), int(self.y)

        if self.kind == 'fighter':
            pygame.draw.polygon(surf, RED,     [(x+20,y),(x-20,y-13),(x-20,y+13)])
            pygame.draw.polygon(surf, DARK_RED,[(x-10,y-13),(x+2,y-26),(x+12,y-5)])
            pygame.draw.polygon(surf, DARK_RED,[(x-10,y+13),(x+2,y+26),(x+12,y+5)])
            pygame.draw.circle(surf, ORANGE, (x+18,y), 4)
            pygame.draw.circle(surf, YELLOW, (x+18,y), 2)

        elif self.kind == 'scout':
            pygame.draw.polygon(surf, PURPLE, [(x+14,y),(x-14,y-10),(x-14,y+10)])
            pygame.draw.circle(surf, WHITE, (x+4,y), 4)
            pygame.draw.circle(surf, PURPLE,(x+4,y), 2)

        else:   # heavy
            pygame.draw.ellipse(surf, ORANGE,     (x-27,y-18,56,38))
            pygame.draw.ellipse(surf, (200,90,0), (x-13,y-10,28,22))
            pygame.draw.rect(surf, GRAY, (x+15,y-22,18,6))
            pygame.draw.rect(surf, GRAY, (x+15,y+16, 18,6))
            pygame.draw.circle(surf, YELLOW, (x+26,y), 7)
            pygame.draw.circle(surf, ORANGE, (x+26,y), 4)
            # HP bar
            bw = 44
            filled = max(0, int(bw * self.hp / self.max_hp))
            pygame.draw.rect(surf, DARK_GRAY, (x-22,y-30, bw,6))
            pygame.draw.rect(surf, GREEN,     (x-22,y-30, filled,6))

        for b in self.bullets:
            b.draw(surf)

    def get_rect(self):
        return pygame.Rect(self.x-self.W//2, self.y-self.H//2, self.W, self.H)


# ══════════════════════════════════════════════════════════════════════════════
#  EXPLOSION
# ══════════════════════════════════════════════════════════════════════════════
class Explosion:
    def __init__(self, x, y, big=False):
        self.x, self.y = x, y
        self.max_r  = 45 if big else 25
        self.frame  = 0
        self.total  = 22
        self.active = True
        self.sparks = [(random.uniform(0, math.tau), random.uniform(1.5, 4.5))
                       for _ in range(12 if big else 6)]

    def update(self):
        self.frame += 1
        if self.frame >= self.total:
            self.active = False

    def draw(self, surf):
        t = self.frame / self.total
        r = int(self.max_r * math.sin(t * math.pi))
        if r <= 0:
            return
        pygame.draw.circle(surf, (255, int(180*(1-t)), 0), (int(self.x), int(self.y)), r)
        if r > 5:
            pygame.draw.circle(surf, (255, 255, int(200*(1-t))), (int(self.x), int(self.y)), r//2)
        for ang, spd in self.sparks:
            sx = self.x + math.cos(ang) * spd * self.frame
            sy = self.y + math.sin(ang) * spd * self.frame
            pygame.draw.circle(surf, YELLOW, (int(sx), int(sy)), 2)


# ══════════════════════════════════════════════════════════════════════════════
#  GAME
# ══════════════════════════════════════════════════════════════════════════════
class Game:
    WEIGHTS = {
        1: {'fighter':8,'scout':2,'heavy':0},
        2: {'fighter':6,'scout':3,'heavy':1},
        3: {'fighter':5,'scout':3,'heavy':2},
    }

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("🚀 Space Shooter")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock  = pygame.time.Clock()
        self.font   = pygame.font.Font(None, 36)
        self.font_b = pygame.font.Font(None, 74)
        self.font_s = pygame.font.Font(None, 24)
        self.sounds = SoundManager()
        self._reset()

    def _reset(self):
        self.player      = Player()
        self.enemies:    list[Enemy]     = []
        self.powerups:   list[PowerUp]   = []
        self.explosions: list[Explosion] = []
        self.stars       = [Star() for _ in range(180)]
        self.score       = 0
        self.level       = 1
        self.kills       = 0
        self.kills_level = 10
        self.spawn_timer = 0
        self.spawn_delay = 90
        self.state       = 'playing'

    # ── spawning ──────────────────────────────────────────────────────────────
    def _spawn_enemy(self):
        lv = min(self.level, 3)
        w  = self.WEIGHTS[lv]
        kind = random.choices(list(w.keys()), list(w.values()))[0]
        self.enemies.append(Enemy(kind))

    # ── collisions ────────────────────────────────────────────────────────────
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
                        self.score   += enemy.score_val
                        self.kills   += 1
                        self.explosions.append(Explosion(enemy.x, enemy.y, big=True))
                        self.sounds.play('boom')
                        enemy.active = False
                        if enemy.should_drop():
                            self.powerups.append(PowerUp(enemy.x, enemy.y))
                    else:
                        self.explosions.append(Explosion(enemy.x, enemy.y))
                    break

        # Enemy bullets vs player
        for enemy in self.enemies:
            for eb in enemy.bullets:
                if eb.active and eb.get_rect().colliderect(p_rect):
                    eb.active = False
                    absorbed  = not self.player.has_shield
                    damaged   = self.player.take_damage()
                    if not absorbed:
                        self.sounds.play('shield_break')
                    elif damaged:
                        self.sounds.play('hit')
                        self.explosions.append(Explosion(self.player.x, self.player.y))

        # Enemy ram vs player
        for enemy in self.enemies:
            if enemy.active and enemy.get_rect().colliderect(p_rect):
                enemy.active = False
                self.explosions.append(Explosion(enemy.x, enemy.y, big=True))
                self.sounds.play('boom')
                absorbed = not self.player.has_shield
                if self.player.take_damage():
                    if absorbed:
                        self.sounds.play('hit')
                    self.explosions.append(Explosion(self.player.x, self.player.y))
                elif not absorbed:
                    self.sounds.play('shield_break')

        # Player picks up power-ups
        for pu in self.powerups:
            if pu.active and pu.get_rect().colliderect(p_rect):
                pu.active = False
                self.player.apply_powerup(pu.kind)
                self.sounds.play('powerup')

        if self.player.health <= 0:
            self.state = 'game_over'

    # ── level progression ─────────────────────────────────────────────────────
    def _check_level(self):
        if self.kills >= self.kills_level * self.level:
            self.level       += 1
            self.spawn_delay  = max(28, 90 - self.level * 10)

    # ── HUD ───────────────────────────────────────────────────────────────────
    def _draw_hud(self):
        self.screen.blit(self.font.render(f"Score: {self.score}", True, WHITE),  (10, 10))
        self.screen.blit(self.font.render(f"Level: {self.level}", True, YELLOW), (10, 44))

        # Lives (ship silhouettes)
        self.screen.blit(self.font_s.render("Lives:", True, WHITE), (SCREEN_WIDTH-200, 12))
        for i in range(self.player.MAX_HP):
            if i < self.player.health:
                col = CYAN if self.player.has_shield else RED
            else:
                col = DARK_GRAY
            cx = SCREEN_WIDTH - 140 + i * 28
            cy = 22
            pygame.draw.polygon(self.screen, col,
                                [(cx-12,cy+6),(cx+14,cy),(cx-12,cy-6)])

        # Kill-progress bar (centre top)
        bx, by, bw, bh = SCREEN_WIDTH//2-80, 8, 160, 14
        thresh = self.kills_level * self.level
        filled = min(bw, int(bw * self.kills / thresh)) if thresh else bw
        pygame.draw.rect(self.screen, DARK_GRAY, (bx, by, bw, bh))
        pygame.draw.rect(self.screen, GREEN,     (bx, by, filled, bh))
        pygame.draw.rect(self.screen, GRAY,      (bx, by, bw, bh), 1)
        pt = self.font_s.render(f"{self.kills}/{thresh}", True, WHITE)
        self.screen.blit(pt, pt.get_rect(center=(SCREEN_WIDTH//2, by+bh+10)))

        # Active power-ups row (bottom left)
        self._draw_active_powerups()

        # Controls hint (bottom centre)
        hint = self.font_s.render("WASD / Arrows — move    SPACE — shoot", True, GRAY)
        self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, SCREEN_HEIGHT-26))

    def _draw_active_powerups(self):
        """Show badges + countdown bars for currently active power-ups."""
        items = []
        if self.player.double_timer > 0:
            items.append(('2x SHOT', YELLOW, self.player.double_timer, 600))
        if self.player.has_shield:
            items.append(('SHIELD',  CYAN,   1, 1))
        if self.player.slow_timer > 0:
            items.append(('SLOW',    PURPLE, self.player.slow_timer, 300))

        x0 = 10
        y0 = SCREEN_HEIGHT - 58
        for label, col, remaining, total in items:
            bw = 90
            pygame.draw.rect(self.screen, (25,25,35), (x0, y0, bw, 26), border_radius=5)
            pygame.draw.rect(self.screen, col,        (x0, y0, bw, 26), 1, border_radius=5)
            t = self.font_s.render(label, True, col)
            self.screen.blit(t, t.get_rect(center=(x0+bw//2, y0+10)))
            # Timer bar along bottom of badge
            bar = max(0, int(bw * remaining / total)) if total > 1 else bw
            pygame.draw.rect(self.screen, col, (x0, y0+23, bar, 3))
            x0 += bw + 6

    def _draw_slow_tint(self):
        """Subtle blue tint when slow-time is active."""
        tint = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        tint.fill((60, 30, 160, 20))
        self.screen.blit(tint, (0, 0))

    # ── game-over screen ──────────────────────────────────────────────────────
    def _draw_game_over(self):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 165))
        self.screen.blit(ov, (0, 0))

        def ctr(surf, y):
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, y)))

        ctr(self.font_b.render("GAME  OVER",           True, RED),    SCREEN_HEIGHT//2 - 80)
        ctr(self.font.render(f"Score: {self.score}",   True, WHITE),  SCREEN_HEIGHT//2 - 10)
        ctr(self.font.render(f"Level: {self.level}",   True, YELLOW), SCREEN_HEIGHT//2 + 35)
        ctr(self.font.render("R — restart   Q — quit", True, CYAN),   SCREEN_HEIGHT//2 + 100)

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        pygame.quit(); sys.exit()
                    if event.key == pygame.K_r and self.state == 'game_over':
                        self._reset()

            if self.state == 'playing':
                keys = pygame.key.get_pressed()
                self.player.update(keys)

                if self.player.just_shot:
                    self.sounds.play('shoot')

                # Enemy time-scale (slow power-up)
                ts = 0.45 if self.player.slow_active else 1.0

                # Spawn
                self.spawn_timer += 1
                if self.spawn_timer >= self.spawn_delay:
                    self._spawn_enemy()
                    self.spawn_timer = 0

                for e in self.enemies:
                    e.update(ts)
                self.enemies = [e for e in self.enemies if e.active]

                for pu in self.powerups:
                    pu.update()
                self.powerups = [pu for pu in self.powerups if pu.active]

                self._collisions()

                for ex in self.explosions:
                    ex.update()
                self.explosions = [ex for ex in self.explosions if ex.active]

                self._check_level()

            # ── Draw ──────────────────────────────────────────────────────────
            self.screen.fill(BLACK)

            for star in self.stars:
                star.update()
                star.draw(self.screen)

            if self.player.slow_active:
                self._draw_slow_tint()

            for e in self.enemies:
                e.draw(self.screen)

            for pu in self.powerups:
                pu.draw(self.screen, self.font_s)

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
