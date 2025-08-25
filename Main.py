import pygame
import random
import sys
from typing import Tuple

# -------------------------
# Configuration & Constants
# -------------------------
WIDTH, HEIGHT = 900, 700
FPS = 60

GRID_ROWS = 5
GRID_COLS = 5
CELL_SIZE = 100
GRID_W = GRID_COLS * CELL_SIZE
GRID_H = GRID_ROWS * CELL_SIZE

GRID_OFFSET_X = (WIDTH - GRID_W) // 2
GRID_OFFSET_Y = 120  # leaves room for top HUD

LIGHT_BROWN = (181, 101, 29)   # hole border
DARK_BROWN = (101, 67, 33)     # hole fill
GREEN = (34, 139, 34)          # grass
GREEN_DARK = (26, 105, 26)     # grass texture
YELLOW = (255, 215, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
UI_BG = (20, 20, 20)

START_VISIBLE_TIME = 1.0
START_HIDDEN_TIME = 1.0
MIN_TIME = 0.3
TIME_DELTA_PER_10PTS = 0.1

RABBIT_BASE_SIZE = 40  # sprite pixel grid size (before scaling)
RABBIT_TARGET_SIZE = 80  # final display size in pixels
RABBIT_ANIM_FPS = 6  # simple 2-frame toggle when visible
CLICK_TOLERANCE = 0.15  # 15%

STATE_START = "START"
STATE_PLAY = "PLAY"
STATE_CONFIRM_QUIT = "CONFIRM_QUIT"
STATE_GAME_OVER = "GAME_OVER"

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rabbit Click — 5x5 Grid")
clock = pygame.time.Clock()

# Fonts
FONT_LG = pygame.font.Font(None, 72)
FONT_MD = pygame.font.Font(None, 48)
FONT_SM = pygame.font.Font(None, 36)

# Create a dedicated random number generator for the grass texture
# to avoid interfering with the gameplay's randomness.
grass_rng = random.Random(42)

# ---------------------------------
# Utility: Text with Outline/Border
# ---------------------------------
def draw_text_with_outline(surface, text, font, center, inner_color=WHITE, outline_color=YELLOW, outline_thickness=2):
    # Render outline by drawing text multiple times around center
    x, y = center
    base = font.render(text, True, inner_color)
    outline = font.render(text, True, outline_color)
    for dx in range(-outline_thickness, outline_thickness + 1):
        for dy in range(-outline_thickness, outline_thickness + 1):
            if dx == 0 and dy == 0:
                continue
            rect = outline.get_rect(center=(x + dx, y + dy))
            surface.blit(outline, rect)
    rect = base.get_rect(center=(x, y))
    surface.blit(base, rect)

# -------------------------
# Button Component (Pixel)
# -------------------------
class Button:
    def __init__(self, rect: pygame.Rect, label: str, bg=YELLOW, fg=BLACK, font=FONT_MD):
        self.rect = rect
        self.label = label
        self.bg = bg
        self.fg = fg
        self.font = font

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=8)
        text_surf = self.font.render(self.label, True, self.fg)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_hover(self, pos):
        return self.rect.collidepoint(pos)

# -------------------------
# Pixel-Art Rabbit Generator
# -------------------------
def make_rabbit_frames() -> Tuple[pygame.Surface, pygame.Surface]:
    """
    Build two 16x16 pixel-art frames and scale them up with nearest-neighbor.
    Frame B slightly changes ears/eyes (simple 'blink/wiggle' effect).
    """
    # Define colors
    transparent = (0, 0, 0, 0)
    body = (235, 235, 235, 255)
    shade = (200, 200, 200, 255)
    ear = (255, 180, 180, 255)
    eye = (40, 40, 40, 255)
    nose = (255, 120, 120, 255)

    def new_canvas():
        return pygame.Surface((16, 16), pygame.SRCALPHA)

    def plot(px, x, y, c):
        px.set_at((x, y), c)

    def paint_body(px, ear_shift=0):
        # Simple chibi rabbit: head big circle-ish, ears up, small body.
        # We'll place pixels manually for crispness.
        # Head/Body blob
        for y in range(4, 13):
            for x in range(3, 13):
                plot(px, x, y, body)
        # Shading (right-bottom)
        for y in range(8, 13):
            for x in range(9, 13):
                plot(px, x, y, shade)
        # Ears
        ear_x = 5
        ear_y = 1 + ear_shift
        for y in range(0, 5):
            plot(px, ear_x, ear_y + y, body)
            plot(px, ear_x + 1, ear_y + y, ear)
        ear_x2 = 9
        for y in range(0, 5):
            plot(px, ear_x2, ear_y + y, body)
            plot(px, ear_x2 + 1, ear_y + y, ear)
        # Eyes
        plot(px, 6, 7 + (1 - ear_shift), eye)
        plot(px, 10, 7 + (1 - ear_shift), eye)
        # Nose
        plot(px, 8, 9, nose)

        # Feet hint
        plot(px, 5, 12, shade)
        plot(px, 10, 12, shade)

    a = new_canvas()
    b = new_canvas()
    paint_body(a, ear_shift=0)
    paint_body(b, ear_shift=1)

    def scale_nn(surf):
        return pygame.transform.scale(surf, (RABBIT_TARGET_SIZE, RABBIT_TARGET_SIZE))

    return scale_nn(a), scale_nn(b)

RABBIT_FRAME_A, RABBIT_FRAME_B = make_rabbit_frames()

# -------------------------
# Grass Texture Generator
# -------------------------
def draw_grass(surface):
    surface.fill(GREEN)
    # Subtle pixel clusters for texture using the dedicated grass RNG
    for _ in range(1400):
        x = grass_rng.randint(0, WIDTH - 2)
        y = grass_rng.randint(0, HEIGHT - 2)
        if not (GRID_OFFSET_X <= x < GRID_OFFSET_X + GRID_W and GRID_OFFSET_Y <= y < GRID_OFFSET_Y + GRID_H):
            surface.fill(GREEN_DARK, pygame.Rect(x, y, 2, 2))

# -------------------------
# Grid / Holes Rendering
# -------------------------
def draw_grid(surface):
    # Dark soil boxes with light-brown border
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            x = GRID_OFFSET_X + c * CELL_SIZE
            y = GRID_OFFSET_Y + r * CELL_SIZE
            pygame.draw.rect(surface, LIGHT_BROWN, (x, y, CELL_SIZE, CELL_SIZE), width=6)
            pygame.draw.rect(surface, DARK_BROWN, (x + 6, y + 6, CELL_SIZE - 12, CELL_SIZE - 12))

def hole_to_rect(row, col):
    x = GRID_OFFSET_X + col * CELL_SIZE
    y = GRID_OFFSET_Y + row * CELL_SIZE
    return pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)

def rabbit_rect_at(row, col):
    cell = hole_to_rect(row, col)
    # center the rabbit inside the hole
    rx = cell.centerx - RABBIT_TARGET_SIZE // 2
    ry = cell.centery - RABBIT_TARGET_SIZE // 2
    return pygame.Rect(rx, ry, RABBIT_TARGET_SIZE, RABBIT_TARGET_SIZE)

def inflate_for_tolerance(rect, tol=CLICK_TOLERANCE):
    extra_w = rect.width * tol
    extra_h = rect.height * tol
    return pygame.Rect(rect.x - extra_w, rect.y - extra_h, rect.width + 2 * extra_w, rect.height + 2 * extra_h)

# -------------------------
# Game Core
# -------------------------
class Game:
    def __init__(self):
        self.state = STATE_START
        self.score = 0
        self.visible_time = START_VISIBLE_TIME
        self.hidden_time = START_HIDDEN_TIME

        self.rabbit_visible = False
        self.current_row = 0
        self.current_col = 0

        self.state_timer_ms = 0  # tracks elapsed in current visible/hidden phase
        self.last_tick = pygame.time.get_ticks()

        # UI Buttons
        self.btn_start = Button(pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 - 40, 240, 80), "Start")
        self.btn_quit = Button(pygame.Rect(WIDTH - 150, HEIGHT - 70, 120, 50), "Quit")
        self.btn_yes = Button(pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 20, 120, 50), "Yes")
        self.btn_no = Button(pygame.Rect(WIDTH // 2 + 30, HEIGHT // 2 + 20, 120, 50), "No")
        self.btn_restart = Button(pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 40, 240, 70), "Restart")

        self.anim_timer = 0
        self.anim_frame = 0  # 0 or 1

    def reset(self):
        self.state = STATE_START
        self.score = 0
        self.visible_time = START_VISIBLE_TIME
        self.hidden_time = START_HIDDEN_TIME
        self.rabbit_visible = False
        self.state_timer_ms = 0
        self.last_tick = pygame.time.get_ticks()
        self.anim_timer = 0
        self.anim_frame = 0

    def start_play(self):
        self.state = STATE_PLAY
        self.score = 0
        self.visible_time = START_VISIBLE_TIME
        self.hidden_time = START_HIDDEN_TIME
        self._choose_new_hole()
        self.rabbit_visible = True
        self.state_timer_ms = 0
        self.last_tick = pygame.time.get_ticks()
        self.anim_timer = 0
        self.anim_frame = 0

    def _choose_new_hole(self):
        # Find a new hole that is different from the current one.
        # This now works correctly because the global random generator is not being reset.
        while True:
            new_row = random.randint(0, GRID_ROWS - 1)
            new_col = random.randint(0, GRID_COLS - 1)
            if (new_row, new_col) != (self.current_row, self.current_col):
                self.current_row = new_row
                self.current_col = new_col
                break

    def update_timers(self):
        now = pygame.time.get_ticks()
        dt = now - self.last_tick
        self.last_tick = now
        self.state_timer_ms += dt

        # Rabbit animation toggle
        if self.rabbit_visible:
            self.anim_timer += dt
            frame_interval = int(1000 / RABBIT_ANIM_FPS)
            if self.anim_timer >= frame_interval:
                self.anim_timer = 0
                self.anim_frame = 1 - self.anim_frame

        if self.rabbit_visible:
            if self.state_timer_ms >= int(self.visible_time * 1000):
                self.rabbit_visible = False
                self.state_timer_ms = 0
        else:
            if self.state == STATE_PLAY and self.state_timer_ms >= int(self.hidden_time * 1000):
                self._choose_new_hole()
                self.rabbit_visible = True
                self.state_timer_ms = 0

    def register_click(self, pos):
        if self.state == STATE_PLAY:
            # Quit button?
            if self.btn_quit.rect.collidepoint(pos):
                self.state = STATE_CONFIRM_QUIT
                return

            if self.rabbit_visible:
                rrect = rabbit_rect_at(self.current_row, self.current_col)
                hitbox = inflate_for_tolerance(rrect)
                if hitbox.collidepoint(pos):
                    # Successful hit
                    self.score += 1
                    if self.score % 10 == 0:
                        self.visible_time = max(MIN_TIME, self.visible_time - TIME_DELTA_PER_10PTS)
                        self.hidden_time = max(MIN_TIME, self.hidden_time - TIME_DELTA_PER_10PTS)
                    # Immediately hide and continue cycle
                    self.rabbit_visible = False
                    self.state_timer_ms = 0
                    return
            # Miss → Game Over
            self.state = STATE_GAME_OVER

        elif self.state == STATE_START:
            if self.btn_start.rect.collidepoint(pos):
                self.start_play()

        elif self.state == STATE_CONFIRM_QUIT:
            if self.btn_yes.rect.collidepoint(pos):
                pygame.quit()
                sys.exit(0)
            if self.btn_no.rect.collidepoint(pos):
                self.state = STATE_PLAY

        elif self.state == STATE_GAME_OVER:
            if self.btn_restart.rect.collidepoint(pos):
                self.start_play()

    # -------------------------
    # Rendering (per state)
    # -------------------------
    def render(self, surface):
        # Background grass + grid
        draw_grass(surface)
        draw_grid(surface)

        if self.state == STATE_START:
            self._render_hud(surface, show_score=False)
            self._render_center_title(surface, "Rabbit Click")
            self.btn_start.draw(surface)

        elif self.state == STATE_PLAY:
            self._render_hud(surface, show_score=True)
            self._render_rabbit(surface)
            self.btn_quit.draw(surface)

        elif self.state == STATE_CONFIRM_QUIT:
            self._render_hud(surface, show_score=True)
            self._render_rabbit(surface)
            self.btn_quit.draw(surface)
            self._render_confirm_modal(surface)

        elif self.state == STATE_GAME_OVER:
            self._render_hud(surface, show_score=False)
            self._render_center_title(surface, f"Game Over — Score: {self.score}")
            self.btn_restart.draw(surface)

    def _render_hud(self, surface, show_score=True):
        # Top HUD strip (subtle bar)
        pygame.draw.rect(surface, UI_BG, (0, 0, WIDTH, 90))
        if show_score:
            draw_text_with_outline(surface, f"Score: {self.score}", FONT_MD, (WIDTH // 2, 45))

    def _render_center_title(self, surface, title):
        draw_text_with_outline(surface, title, FONT_LG, (WIDTH // 2, HEIGHT // 2 - 60))

    def _render_rabbit(self, surface):
        if not self.rabbit_visible:
            return
        rrect = rabbit_rect_at(self.current_row, self.current_col)
        frame = RABBIT_FRAME_A if self.anim_frame == 0 else RABBIT_FRAME_B
        surface.blit(frame, rrect)

    def _render_confirm_modal(self, surface):
        # Dim the background slightly
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        # Modal box
        modal_rect = pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 90, 440, 180)
        pygame.draw.rect(surface, (240, 240, 240), modal_rect, border_radius=10)
        pygame.draw.rect(surface, (160, 160, 160), modal_rect, width=3, border_radius=10)

        # Text
        text = FONT_MD.render("Are you sure?", True, BLACK)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 25))
        surface.blit(text, text_rect)

        self.btn_yes.draw(surface)
        self.btn_no.draw(surface)

# -------------------------
# Main Loop
# -------------------------
def main():
    game = Game()
    while True:
        clock.tick(FPS)

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                game.register_click(event.pos)

        # Update
        if game.state in (STATE_PLAY, STATE_CONFIRM_QUIT):
            # Only advance timers while in PLAY; keep rabbit frozen under confirm
            if game.state == STATE_PLAY:
                game.update_timers()

        # Render
        game.render(screen)
        pygame.display.flip()

if __name__ == "__main__":
    main()