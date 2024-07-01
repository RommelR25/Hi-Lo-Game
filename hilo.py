from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.core.audio import SoundLoader
from kivy.uix.image import AsyncImage
from kivy.animation import Animation
from kivy.uix.scrollview import ScrollView
import random
import os
import sqlite3

# Define custom classes and widgets
class CustomMDTextField(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0.25, 0, 1)  # Dark green background color
        self.foreground_color = (0, 1, 0, 1)     # Green text color

class CustomLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.halign = 'center'
        self.valign = 'middle'
        self.bind(size=self._update_text_size)

    def _update_text_size(self, *_):
        self.text_size = self.size

class Cards:
    suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    values = list(range(1, 14))

    def __init__(self):
        self.deck = [(value, suit) for suit in self.suits for value in self.values]
        random.shuffle(self.deck)

    def draw_card(self):
        if self.deck:
            return self.deck.pop()
        else:
            return None

    def get_card_image_path(self, value, suit):
        filename = f"{value}.png"
        return os.path.join("images", suit, filename)

class HiLoGame(MDScreen):
    def on_enter_pressed(self, user_text):
        app = MDApp.get_running_app()
        player_data = app.load_player_data(user_text)

        if player_data:
            # Player exists, load their money
            self.manager.get_screen('second').ids.greeting.text = "Welcome back, " + user_text + "!"
            self.manager.current = 'second'
        else:
            # New player, initialize money and save their name
            app.save_player_data(user_text, 10000)
            self.manager.get_screen('second').ids.greeting.text = "Welcome, " + user_text + "!"
            self.manager.current = 'second'

class SecondPage(MDScreen):
    def start_game(self):
        app = MDApp.get_running_app()
        player_name = app.root.get_screen('first').ids.name_input.text
        if player_name:
            app.root.get_screen('play').start_game(player_name)
            app.root.current = 'play'

    def goto_settings(self):
        self.manager.current = 'settings'  # Navigate to the 'settings' screen

    def goto_leaderboard(self):
        self.manager.current = 'leaderboard'  # Navigate to the 'leaderboard' screen

class PlayPage(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cards = Cards()
        self.current_card = None
        self.next_card = None
        self.money = 10000  # Initialize money to $10,000
        self.sfx = SoundLoader.load('SFX.mp3')
        self.player_name = None  # Store player's name

    def start_game(self, player_name):
        self.player_name = player_name
        self.money = 10000  # Reset money to initial value
        self.cards = Cards()
        self.current_card = self.cards.draw_card()
        self.next_card = self.cards.draw_card()
        self.update_card_images()
        self.ids.result_label.text = ""  # Clear result label

    def reshuffle(self):
        self.cards = Cards()  # Reshuffle the deck
        self.current_card = self.cards.draw_card()
        self.next_card = self.cards.draw_card()
        self.update_card_images()
        self.ids.result_label.text = ""  # Clear result label

    def guess_higher(self):
        if MDApp.get_running_app().sfx_enabled and self.sfx:
            self.sfx.play()
        self.flip_card(True)

    def guess_lower(self):
        if MDApp.get_running_app().sfx_enabled and self.sfx:
            self.sfx.play()
        self.flip_card(False)

    def flip_card(self, guess_higher):
        if self.current_card is None:
            return
        anim = Animation(scale_x=0, duration=0.2)
        anim.bind(on_complete=lambda *args: self.update_card_image_source(guess_higher))
        anim.start(self.ids.current_card_image)

    def update_card_image_source(self, guess_higher):
        if self.next_card is None:
            self.ids.result_label.text = "No more cards in the deck!"
            return

        if (guess_higher and self.next_card[0] > self.current_card[0]) or (
                not guess_higher and self.next_card[0] < self.current_card[0]):
            result = "Correct!"
            self.money += 500
        else:
            result = "Incorrect!"
            self.money -= 500

        self.current_card = self.next_card
        self.next_card = self.cards.draw_card()
        self.update_card_images()

        self.ids.result_label.text = result
        self.ids.money_label.text = f"Money: ${self.money}"
        anim = Animation(scale_x=1, duration=0.2)
        anim.start(self.ids.current_card_image)

        # Save player's money after each update
        app = MDApp.get_running_app()
        app.save_player_data(self.player_name, self.money)
        # Update leaderboard with the new score
        app.root.get_screen('leaderboard').add_score(self.money)

    def update_card_images(self):
        if self.current_card:
            value, suit = self.current_card
            self.ids.current_card_image.source = self.cards.get_card_image_path(value, suit)

        # Always set next_card_image to the back of the card
        self.ids.next_card_image.source = "images/back_card.png"

class SettingsPage(MDScreen):
    pass

class LeaderboardPage(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scores = []

    def on_pre_enter(self, *args):
        self.update_leaderboard()

    def add_score(self, score):
        self.scores.append(score)
        self.scores.sort(reverse=True)
        self.update_leaderboard()

    def update_leaderboard(self):
        leaderboard_layout = self.ids.leaderboard_layout
        leaderboard_layout.clear_widgets()

        # Fetch player data from the database and display in the leaderboard
        conn = sqlite3.connect(HiLoApp.database)
        c = conn.cursor()
        c.execute('SELECT * FROM players ORDER BY money DESC')
        players = c.fetchall()
        conn.close()

        for idx, player in enumerate(players, 1):
            leaderboard_layout.add_widget(
                CustomLabel(text=f"{idx}. {player[1]} - Money: ${player[2]}", font_size=30, size_hint_y=None, height=dp(30))
            )

        # Calculate the height based on the number of players
        leaderboard_layout.height = dp(30) * len(players)


class WindowManager(ScreenManager):
    pass

class HiLoApp(MDApp):
    sfx_enabled = True  # Add a class attribute for SFX state
    database = 'hilo.db'  # Database file name

    def build(self):
        self.music = SoundLoader.load('BGM.mp3')
        if self.music:
            self.music.loop = True
            self.music.play()
        self.init_database()  # Initialize SQLite database
        return Builder.load_file("hilo.kv")

    def init_database(self):
        # Create a connection to the SQLite database
        conn = sqlite3.connect(self.database)
        c = conn.cursor()

        # Create a table to store player data if it doesn't exist
        c.execute('''CREATE TABLE IF NOT EXISTS players
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT,
                      money INTEGER)''')

        conn.commit()
        conn.close()

    def save_player_data(self, name, money):
        # Save player data to SQLite database
        conn = sqlite3.connect(self.database)
        c = conn.cursor()

        # Check if the player exists in the database
        c.execute('SELECT * FROM players WHERE name=?', (name,))
        player = c.fetchone()

        if player:
            # Update existing player's money
            c.execute('UPDATE players SET money=? WHERE name=?', (money, name))
        else:
            # Insert new player's data
            c.execute('INSERT INTO players (name, money) VALUES (?, ?)', (name, money))

        conn.commit()
        conn.close()

    def load_player_data(self, name):
        # Load player data from SQLite database
        conn = sqlite3.connect(self.database)
        c = conn.cursor()

        c.execute('SELECT * FROM players WHERE name=?', (name,))
        player = c.fetchone()

        conn.close()

        if player:
            return {'name': player[1], 'money': player[2]}
        else:
            return None

    def on_bgm_slider_value(self, instance, value):
        if value > 0:
            if not self.music.state == 'play':
                self.music.play()
            self.music.volume = value / 100
        else:
            self.music.stop()

    def on_sfx_slider_value(self, instance, value):
        self.sfx_enabled = value > 0

    def on_stop(self):
        if self.music:
            self.music.stop()

if __name__ == "__main__":
    HiLoApp().run()
