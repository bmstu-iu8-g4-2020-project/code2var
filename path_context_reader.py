import math
from typing import NamedTuple, Optional
from vocabulary import Code2VecVocabs

import tensorflow as tf
import pandas as pd


class ReaderInputTensors(NamedTuple):
    """
    Used mostly for convenient-and-clear access to input parts (by their names).
    """
    path_source_token_indices: tf.Tensor
    path_indices: tf.Tensor
    path_target_token_indices: tf.Tensor
    target_index: Optional[tf.Tensor] = None
    target_string: Optional[tf.Tensor] = None
    path_source_token_strings: Optional[tf.Tensor] = None
    path_strings: Optional[tf.Tensor] = None
    path_target_token_strings: Optional[tf.Tensor] = None


class PathContextReader:
    """
    Parses Code2VecVocabs to acceptable for code2vec and code2var tensors
    """

    def __init__(self, vocabs: Code2VecVocabs, csv_path: str,
                 repeat_dataset: bool = False):
        self.vocabs = vocabs
        self.csv_path = csv_path
        self.dataset: Optional[tf.data.Dataset] = None

    def get_dataset(self) -> tf.data.Dataset:
        """Returns suitable dataset for code2vec and code2var"""
        if self.dataset is None:
            self.dataset = self._generate_dataset()
        return self.dataset

    def _generate_dataset(self) -> tf.data.Dataset:
        """Generates dataset for code2vec|code2var from vocabs"""
        self._read_input_tensors()

    def _read_input_tensors(self) -> ReaderInputTensors:
        data = pd.read_csv(self.csv_path, sep=' ', header=None)
        data_tensors = [self._generate_input_tensor(line) for line in
                        data.values]


    def _generate_input_tensor(self, line) -> ReaderInputTensors:
        """Parses line to ReaderInputTensors"""
        target = tf.constant(line[0], dtype=tf.string)
        target_index = self.vocabs.target_vocab.get_word_to_index_lookup_table().lookup(
            target)

        p_s, p, p_t = [], [], []
        for context in line[1:]:
            if type(context) == str:
                (path_source, path, path_target) = context.split(",")
                p_s.append(path_source)
                p.append(path)
                p_t.append(path_target)
            # else:
            #     p_s.append("")
            #     p.append(0)
            #     p_t.append("")
        path_sources, paths, path_targets = tf.constant(p_s), \
                                            tf.constant(p), tf.constant(p_t)
        path_sources_lookup = self.vocabs.token_vocab.get_lookup_index(
            path_sources)
        paths_lookup = self.vocabs.token_vocab.get_lookup_index(
            path_sources)
        path_targets_lookup = self.vocabs.token_vocab.get_lookup_index(
            path_targets)
        return ReaderInputTensors(
            target_string=target,
            target_index=target_index,
            path_source_token_strings=path_sources,
            path_strings=paths,
            path_target_token_strings=path_targets,
            path_source_token_indices=path_sources_lookup,
            path_indices=paths_lookup,
            path_target_token_indices=path_targets_lookup,
        )
