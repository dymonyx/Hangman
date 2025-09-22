import io
import random
import pytest
from contextlib import redirect_stdout
from unittest.mock import patch
import hangman_game.Hangman as hangman


# fixture for generating tmp words.txt file instead of a real one
@pytest.fixture
def words_file_factory(tmp_path, monkeypatch):
    def create(file_content):
        file = tmp_path / "words.txt"
        file.write_text(file_content, encoding="utf-8")
        monkeypatch.setattr(hangman, "WORDLIST_FILENAME", str(file))
        return file
    return create


# fixture for modeling input/ouput operations (beacuse it's a console game)
@pytest.fixture
def run_game():
    def fake_run(secret_word, user_inputs):
        buffer = io.StringIO()
        inputs = iter(user_inputs)

        def fake_input(_):
            return next(inputs)
        with redirect_stdout(buffer), patch("builtins.input", fake_input):
            hangman.hangman(secret_word)
        return buffer.getvalue()

    return fake_run


class TestHangman:
    @pytest.mark.parametrize("file_content, expected", [
        ("one two three\n", ["one", "two", "three"]),
        ("", []),
        ("one two three\nsecond line\n", ["one", "two", "three"]),
    ])
    def test_load_words_from_file(self, words_file_factory, file_content, expected):
        words_file_factory(file_content)
        words = hangman.loadWords()
        assert words == expected

    def test_choose_word_returns_random_choice_once(self):
        sample = ["door", "wall", "window"]
        with patch.object(random, "choice", return_value="window") as mock_choice:
            chosen = hangman.chooseWord(sample)
        assert chosen == "window"
        mock_choice.assert_called_once_with(sample)

    @pytest.mark.xfail(reason="isWordGuessed should use set(input letters) instead of len()")
    @pytest.mark.parametrize("secret, guessed", [
        ("moment", list("moent")),
        ("bool",  list("bol")),
        ("handmade", list("handme")),
    ])
    def test_is_word_guessed_should_accept_all_unique_letters(self, secret, guessed):
        assert hangman.isWordGuessed(secret, guessed) is True

    @pytest.mark.parametrize("secret, expected", [
        ("calorie", len("calorie")),
        ("wealth", len("wealth")),
        ("dog", len("dog")),
        ("a", len("a")),
        ("abcdefghijklmnopqrstuvwxyz", len("abcdefghijklmnopqrstuvwxyz")),
    ])
    def test_game_prints_correct_word_length(self, run_game, secret, expected):
        output = run_game(secret, list(secret))
        assert "Welcome to the game, Hangman!" in output
        assert f"I am thinking of a word that is {expected} letters long." in output

    def test_repeated_letters_does_not_consume_attempt(self, run_game):
        output = run_game("home", ["x", "x", "h", "o", "m", "e"])
        guess_lines = [line for line in output.splitlines()
                       if "guesses left" in line]
        assert "8 guesses left" in guess_lines[0]
        assert "7 guesses left" in guess_lines[1]

    def test_loss_message_contains_correct_word(self, run_game):
        output = run_game("cat", list("bdefghij"))
        assert "Sorry, you ran out of guesses." in output
        assert "The word was else." in output
        assert "cat" in output

    @pytest.mark.parametrize("letters_guessed, expected_remaining", [
        (list("abc"), 23),
        ([], 26),
        (list("abcdefghijklmnopqrstuvwxyz"), 0),
    ])
    def test_getAvailableLetters_various_sets(self, letters_guessed, expected_remaining):
        result = hangman.getAvailableLetters(letters_guessed)
        for letter in letters_guessed:
            assert letter not in result
        assert len(result) == expected_remaining
        assert all(l in "abcdefghijklmnopqrstuvwxyz" for l in result)
        assert len(set(result)) == len(result)

    @pytest.mark.xfail(reason="game crashes with invalid inputs")
    @pytest.mark.parametrize("invalid_inputs", [
        ["1", "2", "3"],
        ["!", "@", "#"],
        ["A", "B", "C"],
    ])
    def test_hangman_invalid_symbols(self, run_game, invalid_inputs):
        secret = "dog"
        output = run_game(secret, invalid_inputs + list("dog"))
        assert "Congratulations, you won!" in output
