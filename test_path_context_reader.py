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
    config.config.TRAINING_FREQ_DICTS_PATH = "dataset/java-small/java-small.c2v.dict"
    c2v_vocabs = Code2VecVocabs()
    pcr = PathContextReader(is_train=True, vocabs=c2v_vocabs,
                            csv_path="dataset/java-small/java-small.train_vec.csv")
    dataset = pcr.get_dataset()
    for line in dataset:
        assert line[0].shape[0] == line[1].shape[0]
        assert line[1].shape == line[2].shape
        assert line[2].shape == line[3].shape
