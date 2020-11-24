from argparse import Namespace
from itertools import chain
import tensorflow as tf
import pytest
import typing
import config
from vocabulary import Vocab, Code2VecVocabs


def test_create_from_freq_dict():
    freq_dict = {"a": 2, "c": 10, "int": 100, "A": 1}
    vocab = Vocab.create_from_freq_dict(freq_dict)
    assert {word: i for i, word in
            enumerate(['NOTHING', 'A', 'a', 'c', 'int'])} == vocab.word_to_index
    assert {i: word for i, word in
            enumerate(['NOTHING', 'A', 'a', 'c', 'int'])} == vocab.index_to_word


def test_save_load_vocab():
    freq_dict = {"a": 2, "c": 10, "int": 100, "A": 1}
    vocab = Vocab.create_from_freq_dict(freq_dict)
    with open("dump_vocab.v.c2v", 'wb') as file:
        vocab.save_to_file(file)
    with open("dump_vocab.v.c2v", 'rb') as file:
        new_vocab = Vocab.load_from_file(file)
    assert vocab.word_to_index == new_vocab.word_to_index
    assert vocab.index_to_word == new_vocab.index_to_word


def test_create_lookup_table():
    freq_dict = {"a": 2, "c": 10, "int": 100, "A": 1}
    vocab = Vocab.create_from_freq_dict(freq_dict)
    w_t_i_lookup_table = vocab.get_word_to_index_lookup_table()
    i_t_w_lookup_table = vocab.get_index_to_word_lookup_table()
    for index, word in enumerate(["NOTHING", *sorted([freq_dict.keys()], key=lambda key: freq_dict[key])]):
        assert w_t_i_lookup_table.lookup(tf.constant(word, dtype=tf.string)).numpy() == index
        assert i_t_w_lookup_table.lookup(tf.constant(index, dtype=tf.int32)) == tf.constant(word,
                                                                                            dtype=tf.string)


def test_create_c2v_vocab():
    config.config.CREATE_VOCAB = True
    config.config.TRAINING_FREQ_DICTS_PATH = "dataset/java-small.c2v.dict"
    c2v_vocabs = Code2VecVocabs()
    c2v_vocabs.save("dump_c2v_vocabs.c2v.vocabs")


def test_load_c2v_vocab():
    config.config.CREATE_VOCAB = False
    config.config.CODE2VEC_VOCABS_PATH = "dump_c2v_vocabs.c2v.vocabs"
    c2v_vocabs = Code2VecVocabs()
