from argparse import Namespace
from itertools import chain
import tensorflow as tf
import pytest
import typing
import config
from path_context_reader import PathContextReader
from vocabulary import Code2VecVocabs


def test_get_dataset():
    config.config.CREATE_VOCAB = True
    config.config.VEC_TRAINING_FREQ_DICTS_PATH = "dataset/java-small.c2v.dict"
    c2v_vocabs = Code2VecVocabs()
    pcr = PathContextReader(is_train=True, vocabs=c2v_vocabs,
                            csv_path="dataset/java-small.train_vec.csv")
    dataset = pcr.get_dataset()
    it = iter(dataset)
    it = it.get_next()
    assert it.target_index.shape[0] == it.path_source_token_indices.shape[0]

