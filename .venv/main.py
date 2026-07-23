import json
import os
import random
from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.core.window import Window
from kivy.animation import Animation

KV = '''
ScreenManager:
    id: sm

    # --- HOME SCREEN ---
    MDScreen:
        name: "home"
        BoxLayout:
            orientation: "vertical"
            MDTopAppBar:
                title: "German Vocab Builder"
                elevation: 2
                right_action_items: [["theme-light-dark", lambda x: app.toggle_theme()]]

            ScrollView:
                MDList:
                    id: deck_list

            MDBottomAppBar:
                MDTopAppBar:
                    title: "Reset All Progress"
                    icon: "refresh"
                    type: "bottom"
                    on_action_button: app.reset_progress()

    # --- FLASHCARD SCREEN ---
    MDScreen:
        name: "flashcards"
        BoxLayout:
            orientation: "vertical"
            MDTopAppBar:
                id: deck_title
                title: "Study Mode"
                left_action_items: [["arrow-left", lambda x: app.go_home()]]
                elevation: 0

            MDProgressBar:
                id: progress_bar
                value: 0
                color: app.theme_cls.primary_color

            FloatLayout:
                MDCard:
                    id: flashcard
                    size_hint: .85, .52
                    pos_hint: {"center_x": .5, "center_y": .62}
                    elevation: 3
                    radius: [16, 16, 16, 16]
                    padding: "16dp"
                    on_release: app.flip_card()

                    RelativeLayout:
                        # Dynamic Status Badge
                        MDIcon:
                            id: mastery_badge
                            icon: "help-circle"
                            pos_hint: {"right": 1, "top": 1}
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            opacity: 0

                        MDLabel:
                            id: card_text
                            text: ""
                            theme_text_color: "Primary"
                            halign: "center"
                            valign: "center"
                            markup: True

                # Dedicated "Show Example" Button (Appears only when translation is visible)
                MDRaisedButton:
                    id: example_btn
                    text: "Show Example"
                    elevation: 1
                    opacity: 0
                    disabled: True
                    size_hint_x: 0.85
                    pos_hint: {"center_x": 0.5, "center_y": 0.32}
                    on_release: app.toggle_example()

                # Three-Button State Selection Layout
                BoxLayout:
                    orientation: "horizontal"
                    size_hint_x: 0.85
                    size_hint_y: None
                    height: "48dp"
                    pos_hint: {"center_x": 0.5, "center_y": 0.12}
                    spacing: "10dp"

                    MDRaisedButton:
                        text: "Didn't Know"
                        md_bg_color: 0.8, 0.2, 0.2, 1 
                        size_hint_x: 1
                        on_release: app.mark_state("review")

                    MDRaisedButton:
                        text: "Not Sure"
                        md_bg_color: 0.9, 0.6, 0.1, 1 
                        size_hint_x: 1
                        on_release: app.mark_state("not_sure")

                    MDRaisedButton:
                        text: "Knew It"
                        md_bg_color: 0.2, 0.7, 0.2, 1 
                        size_hint_x: 1
                        on_release: app.mark_state("mastered")
'''


class FlashcardApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress_file = "progress.json"
        self.word_states = self.load_progress()

        try:
            with open("vocabulary.json", "r", encoding="utf-8") as f:
                self.vocabulary = json.load(f)
        except FileNotFoundError:
            print("Error: vocabulary.json not found! Using fallback data.")
            self.vocabulary = {
                "Level A1": {
                    "Deck 1": [
                        {"de": "der Hund", "en": "the dog", "de_sentence": "Der Hund bellt laut.",
                         "en_sentence": "The dog barks loudly."},
                        {"de": "die Katze", "en": "the cat", "de_sentence": "Die Katze schläft.",
                         "en_sentence": "The cat is sleeping."}
                    ]
                }
            }

        self.active_deck = []
        self.current_word = None

        # States: 0 = Front (German only), 1 = Translation shown, 2 = Translation + Sentence shown
        self.card_state = 0

    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                data = json.load(f).get("word_states", {})
                if isinstance(data, list):
                    return {word: "mastered" for word in data}
                return data
        return {}

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump({"word_states": self.word_states}, f)

    def reset_progress(self):
        self.word_states = {}
        self.save_progress()
        self.on_start()

    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.theme_style = "Light"
        Window.size = (400, 700)
        return Builder.load_string(KV)

    def toggle_theme(self):
        if self.theme_cls.theme_style == "Light":
            self.theme_cls.theme_style = "Dark"
        else:
            self.theme_cls.theme_style = "Light"

    def on_start(self):
        from kivymd.uix.list import OneLineIconListItem, IconLeftWidget
        deck_list = self.root.ids.deck_list
        deck_list.clear_widgets()

        for level, decks in self.vocabulary.items():
            for deck_name, words in decks.items():
                mastered_count = sum(1 for w in words if self.word_states.get(w['de']) == "mastered")
                total_count = len(words)

                item_text = f"{level} - {deck_name} ({mastered_count}/{total_count} mastered)"

                item = OneLineIconListItem(text=item_text,
                                           on_release=lambda x, l=level, d=deck_name: self.start_deck(l, d))
                icon = IconLeftWidget(icon="check-circle" if mastered_count == total_count else "folder")
                item.add_widget(icon)
                deck_list.add_widget(item)

    def start_deck(self, level, deck_name):
        self.active_deck = self.vocabulary[level][deck_name]
        if not self.active_deck:
            return

        self.select_next_word()
        self.set_card_text()
        self.root.current = "flashcards"

    def go_home(self):
        self.on_start()
        self.root.current = "home"

    def animate_transition(self, data_change_callback):
        card = self.root.ids.flashcard
        anim_out = Animation(opacity=0, duration=0.15)

        def on_invisible(*args):
            data_change_callback()
            self.set_card_text()
            Animation(opacity=1, duration=0.15).start(card)

        anim_out.bind(on_complete=on_invisible)
        anim_out.start(card)

    def select_next_word(self):
        self.card_state = 0  # Reset card to front

        weights = []
        for word in self.active_deck:
            state = self.word_states.get(word['de'], 'unseen')
            if state == 'review':
                weights.append(10)
            elif state == 'unseen':
                weights.append(6)
            elif state == 'not_sure':
                weights.append(4)
            elif state == 'mastered':
                weights.append(1)

        self.current_word = random.choices(self.active_deck, weights=weights, k=1)[0]

        mastered_count = sum(1 for w in self.active_deck if self.word_states.get(w['de']) == 'mastered')
        total_count = len(self.active_deck)

        self.root.ids.progress_bar.value = (mastered_count / total_count) * 100
        self.root.ids.deck_title.title = f"Mastery: {mastered_count}/{total_count}"

    def get_colored_word(self, word_de):
        word_lower = word_de.lower()
        if word_lower.startswith("der "):
            return f"[color=#2196F3]{word_de}[/color]"
        elif word_lower.startswith("die "):
            return f"[color=#E91E63]{word_de}[/color]"
        elif word_lower.startswith("das "):
            return f"[color=#4CAF50]{word_de}[/color]"
        return word_de

    def set_card_text(self):
        word = self.current_word
        state = self.word_states.get(word['de'], 'unseen')
        badge = self.root.ids.mastery_badge

        if state == 'unseen':
            badge.opacity = 0
        else:
            badge.opacity = 1
            if state == 'mastered':
                badge.icon = "check-decagram"
                badge.text_color = (0.2, 0.7, 0.2, 1)
            elif state == 'not_sure':
                badge.icon = "help-circle"
                badge.text_color = (0.9, 0.6, 0.1, 1)
            elif state == 'review':
                badge.icon = "close-octagon"
                badge.text_color = (0.8, 0.2, 0.2, 1)

        colored_de = self.get_colored_word(word['de'])
        has_sentence = bool(word.get('de_sentence') and str(word.get('de_sentence')).strip() != "")

        # Manage visibility of the "Show Example" button
        if self.card_state == 0:
            self.root.ids.card_text.text = f"[size=32sp][b]{colored_de}[/b][/size]"
            self.root.ids.example_btn.opacity = 0
            self.root.ids.example_btn.disabled = True

        elif self.card_state == 1:
            self.root.ids.card_text.text = (
                f"[size=28sp][b]{colored_de}[/b][/size]\n\n"
                f"[size=20sp]{word['en']}[/size]"
            )
            # Only show the button if sentences exist for this word
            if has_sentence:
                self.root.ids.example_btn.opacity = 1
                self.root.ids.example_btn.disabled = False
                self.root.ids.example_btn.text = "Show Example"

        elif self.card_state == 2:
            self.root.ids.card_text.text = (
                f"[size=22sp][b]{colored_de}[/b] - {word['en']}[/size]\n\n"
                f"[size=15sp][i]{word['de_sentence']}[/i]\n"
                f"{word['en_sentence']}[/size]"
            )
            if has_sentence:
                self.root.ids.example_btn.opacity = 1
                self.root.ids.example_btn.disabled = False
                self.root.ids.example_btn.text = "Hide Example"

    def flip_card(self):
        # Tapping the card cycles between Front (0) and Translation (1)
        def toggle_side():
            if self.card_state == 0:
                self.card_state = 1
            else:
                self.card_state = 0

        self.animate_transition(toggle_side)

    def toggle_example(self):
        # Button action specifically to toggle the sentence view (State 1 <-> State 2)
        if self.card_state == 1:
            self.card_state = 2
        elif self.card_state == 2:
            self.card_state = 1
        self.set_card_text()

    def mark_state(self, new_state):
        word_de = self.current_word["de"]
        self.word_states[word_de] = new_state
        self.save_progress()
        self.animate_transition(self.select_next_word)


if __name__ == '__main__':
    FlashcardApp().run()