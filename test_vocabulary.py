from argparse import Namespace
from itertools import chain

import pytest

from vocabulary import Vocab


def test_create_from_freq_dict():
    freq_dict = {"a": 2, "c": 10, "int": 100, "A": 1}
    vocab = Vocab.create_from_freq_dict(freq_dict)
    assert {word: i for i, word in
            enumerate([*Namespace().__dict__.keys(), 'A', 'a', 'c', 'int'])} == vocab.word_to_index
    assert {i: word for i, word in
            enumerate([*Namespace().__dict__.keys(), 'A', 'a', 'c', 'int'])} == vocab.index_to_word


def test_save_load_vocab():
    freq_dict = {"a": 2, "c": 10, "int": 100, "A": 1}
    vocab = Vocab.create_from_freq_dict(freq_dict)
    with open("dump_vocab.v.c2v", 'wb') as file:
        vocab.save_to_file(file)
    with open("dump_vocab.v.c2v", 'rb') as file:
        new_vocab = Vocab.load_from_file(file)
    assert vocab.word_to_index == new_vocab.word_to_index
    assert vocab.index_to_word == new_vocab.index_to_word
