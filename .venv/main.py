import json
import os
from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.core.window import Window
import random
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

            ScrollView:
                MDList:
                    id: deck_list
                    # Decks will be populated dynamically in Python

            # Bottom bar for resetting progress during testing
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
                    size_hint: .85, .6
                    pos_hint: {"center_x": .5, "center_y": .55}
                    elevation: 2
                    padding: "24dp"
                    orientation: "vertical"
                    on_release: app.flip_card()

                    MDLabel:
                        id: card_text
                        text: ""
                        theme_text_color: "Primary"
                        font_style: "H4"
                        halign: "center"
                        valign: "center"
                        markup: True

                MDRaisedButton:
                    text: "I didn't know it"
                    md_bg_color: 0.8, 0.2, 0.2, 1
                    pos_hint: {"center_x": .3, "center_y": .12}
                    on_release: app.mark_review()

                MDRaisedButton:
                    text: "I knew it"
                    md_bg_color: 0.2, 0.6, 0.2, 1
                    pos_hint: {"center_x": .7, "center_y": .12}
                    on_release: app.mark_mastered()
'''


class FlashcardApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress_file = "progress.json"
        self.mastered_words = self.load_progress()

        # Load vocabulary dynamically from the JSON file
        try:
            with open("vocabulary.json", "r", encoding="utf-8") as f:
                self.vocabulary = json.load(f)
        except FileNotFoundError:
            print("Error: vocabulary.json not found! Please create it.")
            self.vocabulary = {}

        self.session_queue = []
        self.total_session_words = 0
        self.is_front = True

    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f).get("mastered", [])
        return []

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump({"mastered": self.mastered_words}, f)

    def reset_progress(self):
        self.mastered_words = []
        self.save_progress()
        self.on_start()  # Refresh the UI

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        Window.size = (400, 700)
        return Builder.load_string(KV)

    def on_start(self):
        # Dynamically build the home screen list based on the dictionary
        from kivymd.uix.list import OneLineListItem, IconLeftWidget, OneLineIconListItem

        deck_list = self.root.ids.deck_list
        deck_list.clear_widgets()

        for level, decks in self.vocabulary.items():
            for deck_name, words in decks.items():
                # Calculate how many words are mastered in this specific deck
                mastered_count = sum(1 for w in words if w['de'] in self.mastered_words)
                total_count = len(words)

                item_text = f"{level} - {deck_name} ({mastered_count}/{total_count} mastered)"

                item = OneLineIconListItem(text=item_text,
                                           on_release=lambda x, l=level, d=deck_name: self.start_deck(l, d))
                icon = IconLeftWidget(icon="folder" if mastered_count < total_count else "check-circle")
                item.add_widget(icon)
                deck_list.add_widget(item)

    def start_deck(self, level, deck_name):
        # Queue up only the unmastered words for this session
        deck_words = self.vocabulary[level][deck_name]
        self.session_queue = [w for w in deck_words if w['de'] not in self.mastered_words]
        random.shuffle(self.session_queue)
        if not self.session_queue:
            print("Deck already mastered!")
            return

        self.total_session_words = len(self.session_queue)
        self.is_front = True
        self.update_card_ui()
        self.root.current = "flashcards"

    def go_home(self):
        self.on_start()  # Refresh the mastered counts
        self.root.current = "home"

    def update_card_ui(self):
        if len(self.session_queue) == 0:
            self.root.ids.deck_title.title = "Session Complete!"
            self.root.ids.card_text.text = "[b]Awesome job![/b]\nYou mastered all words in this session."
            self.root.ids.progress_bar.value = 100
            return

        # Update Progress Bar
        words_left = len(self.session_queue)
        progress_pct = ((self.total_session_words - words_left) / self.total_session_words) * 100
        self.root.ids.progress_bar.value = progress_pct
        self.root.ids.deck_title.title = f"Words left: {words_left}"

        # The current word is always the first one in the queue
        word = self.session_queue[0]

        if self.is_front:
            self.root.ids.card_text.text = f"[size=32sp][b]{word['de']}[/b][/size]"
        else:
            self.root.ids.card_text.text = (
                f"[size=32sp][b]{word['de']}[/b][/size]\n\n"
                f"[size=22sp]{word['en']}[/size]\n\n"
                f"[size=16sp][i]{word['de_sentence']}[/i]\n"
                f"{word['en_sentence']}[/size]"
            )

    def flip_card(self):
        if len(self.session_queue) > 0:
            self.is_front = not self.is_front
            self.update_card_ui()

    def mark_mastered(self):
        if len(self.session_queue) > 0:
            # Remove word from queue and save to mastered list
            word = self.session_queue.pop(0)
            self.mastered_words.append(word["de"])
            self.save_progress()

            self.is_front = True
            self.update_card_ui()

    def mark_review(self):
        if len(self.session_queue) > 0:
            # Pop the word from the front and put it at the back of the queue
            word = self.session_queue.pop(0)
            self.session_queue.append(word)

            self.is_front = True
            self.update_card_ui()


if __name__ == '__main__':
    FlashcardApp().run()