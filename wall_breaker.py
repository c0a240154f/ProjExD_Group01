import pygame as pg
import sys
import os
import random

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# --- 定数設定 ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 20
BALL_RADIUS = 10
BLOCK_WIDTH = 75
BLOCK_HEIGHT = 30
FPS = 60

# 色定義
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (200, 0, 200)

# --- クラス定義 ---
class Paddle:
    def __init__(self):
        self.rect = pg.Rect(
            (SCREEN_WIDTH - PADDLE_WIDTH) // 2,
            SCREEN_HEIGHT - PADDLE_HEIGHT - 20,
            PADDLE_WIDTH,
            PADDLE_HEIGHT
        )
        self.speed = 10

    def update(self, keys):
        if keys[pg.K_a]:
            self.rect.move_ip(-self.speed, 0)
        if keys[pg.K_d]:
            self.rect.move_ip(self.speed, 0)
        self.rect.left = max(self.rect.left, 0)
        self.rect.right = min(self.rect.right, SCREEN_WIDTH)

    def draw(self, screen):
        pg.draw.rect(screen, BLUE, self.rect)

class Ball:
    def __init__(self):
        self.rect = pg.Rect(
            SCREEN_WIDTH // 2 - BALL_RADIUS,
            SCREEN_HEIGHT - PADDLE_HEIGHT - 50,
            BALL_RADIUS * 2,
            BALL_RADIUS * 2
        )
        self.vx = random.choice([-5, 5])
        self.vy = -5
        self.speed = 5

    def update(self, paddle, blocks):
        self.rect.move_ip(self.vx, self.vy)
        # 壁との反射
        if self.rect.top < 0:
            self.vy *= -1
            self.rect.top = 0
        if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
            self.vx *= -1
            if self.rect.left < 0: self.rect.left = 0
            if self.rect.right > SCREEN_WIDTH: self.rect.right = SCREEN_WIDTH
        # パドルとの反射
        if self.rect.colliderect(paddle.rect):
            self.vy *= -1
            self.rect.bottom = paddle.rect.top
            center_diff = self.rect.centerx - paddle.rect.centerx
            self.vx = (center_diff / (PADDLE_WIDTH / 2)) * self.speed
            if abs(self.vx) < 1: self.vx = 1 if self.vx >= 0 else -1
        # ブロックとの衝突
        collided_block = self.rect.collidelist(blocks)
        if collided_block != -1:
            block = blocks.pop(collided_block)
            self.vy *= -1
            return True, block
        return False, None

    def draw(self, screen):
        pg.draw.circle(screen, WHITE, self.rect.center, BALL_RADIUS)

    def is_out_of_bounds(self):
        return self.rect.top > SCREEN_HEIGHT

class Block(pg.Rect):
    def __init__(self, x, y, color):
        super().__init__(x, y, BLOCK_WIDTH, BLOCK_HEIGHT)
        self.color = color

    def draw(self, screen):
        pg.draw.rect(screen, self.color, self)

# --- Item3：爆弾・助っ人こうかとん ---
class Item3:
    def __init__(self, x, y, item_type):
        self.item_type = item_type
        self.speed = 3
        self.active = False
        self.image = None
        size = 20
        self.rect = pg.Rect(x - size//2, y - size//2, size, size)
        self.vx = -7  # 右から左
        self.row_y = y
        self.life = 0
        self.color = RED if item_type == "bomb" else PURPLE

    def update(self, blocks=None):
        if not self.active:
            self.rect.move_ip(0, self.speed)
        else:
            self.rect.move_ip(self.vx, 0)
            if blocks:
                # 横方向で重なったブロックだけ削除
                for block in blocks[:]:
                    if abs(block.centery - self.row_y) < BLOCK_HEIGHT // 2 and \
                       block.left < self.rect.right and block.right > self.rect.left:
                        blocks.remove(block)
            self.life -= 1
            if self.life <= 0 or self.rect.right < 0:
                self.active = False

    def draw(self, screen):
        if self.active and self.image:
            screen.blit(self.image, self.rect)
        else:
            pg.draw.rect(screen, self.color, self.rect)

    def check_collision(self, paddle_rect):
        return self.rect.colliderect(paddle_rect)

    def activate(self, blocks):
        if self.item_type == "bomb":
            if not blocks: return
            target = random.choice(blocks)
            destroyed = []
            for block in blocks[:]:
                if abs(block.centerx - target.centerx) <= BLOCK_WIDTH + 5 and \
                   abs(block.centery - target.centery) <= BLOCK_HEIGHT + 5:
                    destroyed.append(block)
            for b in destroyed:
                blocks.remove(b)
        else:
            try:
                self.image = pg.image.load("koukaton.jpg")
                self.image = pg.transform.scale(self.image, (50, 50))
            except:
                self.image = None
            self.active = True
            self.life = 200
            # 一番上の行から右端に出現
            if blocks:
                rows = sorted(list(set(block.centery for block in blocks)))
                self.row_y = rows[0]
                self.rect.centery = self.row_y
            self.rect.right = SCREEN_WIDTH

# --- メイン処理 ---
def main():
    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pg.display.set_caption("ブロック崩し（こうかとん助っ人付き）")
    clock = pg.time.Clock()
    font = pg.font.Font(None, 50)

    paddle = Paddle()
    ball = Ball()
    blocks = []
    items3 = []

    block_colors = [RED, YELLOW, GREEN, BLUE]
    for y in range(4):
        for x in range(10):
            blocks.append(Block(
                x * (BLOCK_WIDTH + 5) + 20,
                y * (BLOCK_HEIGHT + 5) + 30,
                block_colors[y % len(block_colors)]
            ))

    score = 0
    game_over = False
    game_clear = False

    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_r and (game_over or game_clear):
                    main()
                    return

        if not game_over and not game_clear:
            keys = pg.key.get_pressed()
            paddle.update(keys)
            block_hit, destroyed_block = ball.update(paddle, blocks)
            if block_hit:
                score += 10
                # 特殊アイテムドロップ
                if random.random() < 1:
                    item_type3 = random.choice(["bomb", "helper"])
                    item3 = Item3(destroyed_block.centerx, destroyed_block.centery, item_type3)
                    items3.append(item3)

            for item3 in items3[:]:
                item3.update(blocks if item3.active else None)
                if not item3.active:
                    if item3.check_collision(paddle.rect):
                        item3.activate(blocks)
                        if item3.item_type == "bomb":
                            items3.remove(item3)
                    elif item3.rect.top > SCREEN_HEIGHT:
                        items3.remove(item3)

            if ball.is_out_of_bounds(): game_over = True
            if not blocks: game_clear = True

        # 描画
        screen.fill(BLACK)
        paddle.draw(screen)
        ball.draw(screen)
        for block in blocks: block.draw(screen)
        for item3 in items3: item3.draw(screen)

        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (20, 20))

        if game_over:
            over_text = font.render("GAME OVER - Press R to Restart", True, RED)
            screen.blit(over_text, (100, SCREEN_HEIGHT // 2))
        elif game_clear:
            clear_text = font.render("GAME CLEAR! - Press R to Restart", True, YELLOW)
            screen.blit(clear_text, (100, SCREEN_HEIGHT // 2))

        pg.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
