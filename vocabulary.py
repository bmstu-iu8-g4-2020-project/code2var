import pickle
from argparse import Namespace
import tensorflow as tf

import config

from typing import List, Optional, Dict, BinaryIO, NamedTuple, Set


class Vocab:
    """Implements vocabulary for code2vec model"""

    def __init__(self, words: List[str],
                 special_words: Optional[Namespace] = Namespace()):
        """words - """
        self.word_to_index = {word: i for i, word in
                              enumerate([*special_words.__dict__.items(), *words])}
        self.index_to_word = {i: word for word, i in self.word_to_index.items()}
        self.number_of_special = len(special_words.__dict__)
        self.lookup_table_word_to_index = None
        self.lookup_table_index_to_word = None

    @classmethod
    def create_from_freq_dict(cls, freq_dict: Dict[str, int]):
        sorted_by_occurrences = sorted(freq_dict, key=lambda word: freq_dict[word])
        if len(
                sorted_by_occurrences) > config.config.MAX_NUMBER_OF_WORDS_IN_FREQ_DICT:
            sorted_by_occurrences = sorted_by_occurrences[
                                    :config.config.MAX_NUMBER_OF_WORDS_IN_FREQ_DICT]
        print("Creating vocab from frequency dictionary of",
              len(sorted_by_occurrences), "elements")
        return cls(words=sorted_by_occurrences)

    @classmethod
    def load_from_file(cls, file: BinaryIO,
                       special_words: Optional[Namespace] = Namespace()):
        print("Loading from file...")
        w_t_i = pickle.load(file)
        i_t_w = pickle.load(file)
        special_words_size = pickle.load(file)
        if special_words_size != len(special_words.__dict__):
            raise RuntimeError(
                "Wrong special words providen: expected length: " + str(
                    special_words_size) + ", but " + str(
                    len(special_words.__dict__)) + " were given")
        vocab = Vocab([], special_words)
        vocab.index_to_word = i_t_w
        vocab.word_to_index = w_t_i
        for idx, word in enumerate(special_words.__dict__.keys()):
            vocab.word_to_index[word] = idx
            vocab.index_to_word[idx] = word
        print("Loaded vocab of", len(vocab.word_to_index), "elements")
        return vocab

    def save_to_file(self, file: BinaryIO):
        print("Saving vocab to file...")
        w_t_i_wo_special = {word: i for word, i in self.word_to_index.items() if
                            i >= self.number_of_special}
        i_t_w_wo_special = {i: word for i, word in self.index_to_word.items() if
                            i >= self.number_of_special}
        pickle.dump(w_t_i_wo_special, file)
        pickle.dump(i_t_w_wo_special, file)
        pickle.dump(self.number_of_special, file)
        print("Vocab successfully saved")

    @staticmethod
    def create_word_to_index_lookup_table(word_to_index: Dict[str, int],
                                          default_value: int):
        return tf.lookup.StaticHashTable(
            tf.lookup.KeyValueTensorInitializer(list(word_to_index.keys()),
                                                list(word_to_index.values()),
                                                key_dtype=tf.string,
                                                value_dtype=tf.int32),
            default_value=tf.constant(default_value, tf.int32))

    @staticmethod
    def create_index_to_word_lookup_table(index_to_word: Dict[int, str],
                                          default_value: str):
        return tf.lookup.StaticHashTable(
            tf.lookup.KeyValueTensorInitializer(list(index_to_word.keys()),
                                                list(index_to_word.values()),
                                                key_dtype=tf.int32,
                                                value_dtype=tf.string),
            default_value=tf.constant(default_value, tf.string))

    def get_word_to_index_lookup_table(self) -> tf.lookup.StaticHashTable:
        if self.lookup_table_word_to_index is None:
            self.lookup_table_word_to_index = self.create_word_to_index_lookup_table(
                self.word_to_index,
                config.config.DEFAULT_INT32_LOOKUP_VALUE)
        return self.lookup_table_word_to_index

    def get_index_to_word_lookup_table(self) -> tf.lookup.StaticHashTable:
        if self.lookup_table_index_to_word is None:
            self.lookup_table_index_to_word = self.create_index_to_word_lookup_table(
                self.index_to_word,
                config.config.DEFAULT_STRING_LOOKUP_VALUE)
        return self.lookup_table_index_to_word


WordFreqDictType = Dict[str, int]


class Code2VecFreqDicts(NamedTuple):
    token_freq_dict: WordFreqDictType
    path_freq_dict: WordFreqDictType
    target_freq_dict: WordFreqDictType


class Code2VecVocabs:
    def __init__(self):
        self.already_saved_paths: Set[str] = set()
        self.token_vocab: Optional[Vocab] = None
        self.path_vocab: Optional[Vocab] = None
        self.target_vocab: Optional[Vocab] = None

        if config.config.CREATE_VOCAB:
            self._create()
        else:
            self._load(config.config.CODE2VEC_VOCABS_PATH)

    def _create(self):
        print("Creating vocab from", config.config.TRAINING_FREQ_DICTS_PATH)
        freq_dicts = self._load_freq_dicts()
        print("Creating token vocab")
        self.token_vocab = Vocab.create_from_freq_dict(freq_dicts.token_freq_dict)
        print("Created token vocab")
        print("Creating path vocab")
        self.path_vocab = Vocab.create_from_freq_dict(freq_dicts.path_freq_dict)
        print("Created path vocab")
        print("Creating target vocab")
        self.target_vocab = Vocab.create_from_freq_dict(freq_dicts.target_freq_dict)
        print("Created target vocab")
        print("Created all vocabs")

    def _load_freq_dicts(self):
        with open(config.config.TRAINING_FREQ_DICTS_PATH, "rb") as file:
            print("Loading frequency dicts from",
                  config.config.TRAINING_FREQ_DICTS_PATH)
            print("Loading token freq dict")
            token_freq_dict = pickle.load(file)
            print("Loading path freq dict")
            path_freq_dict = pickle.load(file)
            print("Loading target freq dict")
            target_freq_dict = pickle.load(file)
        return Code2VecFreqDicts(token_freq_dict=token_freq_dict,
                                 path_freq_dict=path_freq_dict,
                                 target_freq_dict=target_freq_dict)

    def save(self, path: str):
        if path not in self.already_saved_paths:
            with open(path, "wb") as file:
                print("Saving Code2VecVocabs to", path)
                self.target_vocab.save_to_file(file)
                self.path_vocab.save_to_file(file)
                self.token_vocab.save_to_file(file)
            self.already_saved_paths.add(path)

    def _load(self, path: str):
        with open(path, "rb") as file:
            print("Loading Code2VecVocabs from", path)
            print("Loading target vocab")
            self.target_vocab = Vocab.load_from_file(file)
            print("Loaded target vocab")
            print("Loading path vocab")
            self.path_vocab = Vocab.load_from_file(file)
            print("Loaded path vocab")
            print("Loading token vocab")
            self.token_vocab = Vocab.load_from_file(file)
            print("Loaded token vocab")
            self.already_saved_paths.add(path)
