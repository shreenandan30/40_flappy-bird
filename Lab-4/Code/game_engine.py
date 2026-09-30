from pathlib import Path

import pygame
from .bird import Bird
from .pipe import Pipe

# Game Engine

WHITE = (255, 255, 255)
GREEN = (0, 150, 0)
YELLOW = (255, 220, 80)
DIFFICULTIES = (
    ("Easy", 3, 190),
    ("Medium", 4, 150),
    ("Hard", 6, 120),
)

class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.pipe_interval = 90  # frames between pipe spawns
        self.font = pygame.font.SysFont("Arial", 30)
        self.game_over_font = pygame.font.SysFont("Arial", 56, bold=True)
        self.menu_font = pygame.font.SysFont("Arial", 30)
        self.instruction_font = pygame.font.SysFont("Arial", 18)
        self.game_over_overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        self.game_over_overlay.fill((0, 0, 0, 120))
        self.sounds = self._load_sounds()
        self.difficulty_index = 1
        self.menu_selection = 0
        self.exit_requested = False
        self._start_new_game()

    def _load_sounds(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound_dir = Path(__file__).resolve().parent.parent / "assets" / "sounds"
            return {
                name: pygame.mixer.Sound(str(sound_dir / f"{name}.wav"))
                for name in ("flap", "score", "death")
            }
        except pygame.error:
            return {}

    def _play_sound(self, name):
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def handle_event(self, event):
        if self.game_over:
            if event.type != pygame.KEYDOWN:
                return

            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.difficulty_index = (self.difficulty_index - 1) % len(DIFFICULTIES)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.difficulty_index = (self.difficulty_index + 1) % len(DIFFICULTIES)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.menu_selection = (self.menu_selection - 1) % 2
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.menu_selection = (self.menu_selection + 1) % 2
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.menu_selection == 0:
                    self._start_new_game()
                else:
                    self.exit_requested = True
            elif event.key == pygame.K_r:
                self._start_new_game()
            elif event.key == pygame.K_ESCAPE:
                self.exit_requested = True
            return

        # Flap is edge-triggered (KEYDOWN / MOUSEBUTTONDOWN), not held.
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or event.type == pygame.MOUSEBUTTONDOWN:
            self.bird.flap()
            self._play_sound("flap")

    def handle_input(self):
        # Reserved for continuously-held-key input; flapping is handled
        # in handle_event instead, so there's nothing to poll here.
        pass

    def _start_new_game(self):
        self.difficulty, self.pipe_speed, self.pipe_gap = DIFFICULTIES[self.difficulty_index]
        self.bird = Bird(self.width // 4, self.height // 2)
        self._spawn_timer = 0
        self.pipes = [Pipe(self.width + 100, self.height, gap=self.pipe_gap, speed=self.pipe_speed)]
        self.score = 0
        self.game_over = False
        self.menu_selection = 0

    def update(self):
        if self.game_over:
            return

        self.bird.update()

        if self.bird.y - self.bird.radius <= 0 or self.bird.y + self.bird.radius >= self.height:
            self.game_over = True
            self._play_sound("death")
            return

        self._spawn_timer += 1
        if self._spawn_timer >= self.pipe_interval:
            self._spawn_timer = 0
            self.pipes.append(Pipe(self.width, self.height, gap=self.pipe_gap, speed=self.pipe_speed))

        bird_rect = self.bird.rect()
        for pipe in self.pipes:
            pipe.move()

            if bird_rect.colliderect(pipe.top_rect()) or bird_rect.colliderect(pipe.bottom_rect()):
                self.game_over = True
                self._play_sound("death")
                return

            if not pipe.scored and pipe.x + pipe.width < self.bird.x:
                pipe.scored = True
                self.score += 1
                self._play_sound("score")

        self.pipes = [p for p in self.pipes if not p.off_screen()]

    def render(self, screen):
        for pipe in self.pipes:
            pygame.draw.rect(screen, GREEN, pipe.top_rect())
            pygame.draw.rect(screen, GREEN, pipe.bottom_rect())

        pygame.draw.circle(screen, WHITE, (int(self.bird.x), int(self.bird.y)), self.bird.radius)

        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        if self.game_over:
            screen.blit(self.game_over_overlay, (0, 0))

            game_over_text = self.game_over_font.render("GAME OVER", True, WHITE)
            final_score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
            center_x = self.width // 2
            center_y = self.height // 2
            screen.blit(game_over_text, game_over_text.get_rect(center=(center_x, center_y - 145)))
            screen.blit(final_score_text, final_score_text.get_rect(center=(center_x, center_y - 90)))

            difficulty_label = self.menu_font.render("Difficulty", True, WHITE)
            screen.blit(difficulty_label, difficulty_label.get_rect(center=(center_x, center_y - 35)))

            difficulty_texts = [
                self.menu_font.render(name, True, YELLOW if index == self.difficulty_index else WHITE)
                for index, (name, _, _) in enumerate(DIFFICULTIES)
            ]
            difficulty_spacing = 22
            total_width = sum(text.get_width() for text in difficulty_texts) + difficulty_spacing * (len(difficulty_texts) - 1)
            difficulty_x = center_x - total_width // 2
            for text in difficulty_texts:
                screen.blit(text, (difficulty_x, center_y - 12))
                difficulty_x += text.get_width() + difficulty_spacing

            for index, option in enumerate(("Play Again", "Exit")):
                selected = index == self.menu_selection
                label = f"> {option} <" if selected else option
                color = YELLOW if selected else WHITE
                option_text = self.menu_font.render(label, True, color)
                screen.blit(option_text, option_text.get_rect(center=(center_x, center_y + 50 + index * 45)))

            difficulty_hint = self.instruction_font.render("Left/Right: Difficulty  Up/Down: Menu", True, WHITE)
            action_hint = self.instruction_font.render("Enter: Select  R: Replay  Esc: Exit", True, WHITE)
            screen.blit(difficulty_hint, difficulty_hint.get_rect(center=(center_x, center_y + 145)))
            screen.blit(action_hint, action_hint.get_rect(center=(center_x, center_y + 170)))
