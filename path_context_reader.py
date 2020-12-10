import tensorflow as tf
import config

from typing import NamedTuple, Optional
from vocabulary import Code2VecVocabs


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

    def __init__(self,
                 vocabs: Code2VecVocabs,
                 csv_path: str,
                 is_train: bool,
                 repeat_dataset: bool = False):
        self.is_train = is_train
        self.repeat = repeat_dataset
        self.vocabs = vocabs
        self.csv_path = csv_path
        self.dataset: Optional[tf.data.Dataset] = None
        self.val_dataset: Optional[tf.data.Dataset] = None
        self.test_dataset: Optional[tf.data.Dataset] = None

        self.vocabs.token_vocab.create_word_lookup()
        self.vocabs.path_vocab.create_word_lookup()
        self.vocabs.target_vocab.create_word_lookup()

    def get_dataset(self) -> tf.data.Dataset:
        """Returns suitable dataset for code2vec and code2var"""
        if self.dataset is None:
            self.dataset = self._generate_dataset()
        return self.dataset

    @staticmethod
    def _parse_reader_input_tensor(tensor):
        return ((tensor.path_source_token_indices,
                 tensor.path_indices,
                 tensor.path_target_token_indices),
                tensor.target_index)

    def _generate_dataset(self) -> tf.data.Dataset:
        """Generates dataset for code2vec|code2var from vocabs"""
        dataset = tf.data.experimental.CsvDataset(self.csv_path,
                                                  [""] * (config.config.MAX_CONTEXTS + 1),
                                                  field_delim=" ",
                                                  use_quote_delim=False)
        if self.is_train:
            self.val_dataset = dataset.take(config.config.VALIDATION_SIZE)
            self.test_dataset = dataset.skip(config.config.VALIDATION_SIZE).take(config.config.TEST_SIZE)
            dataset = dataset.skip(config.config.VALIDATION_SIZE + config.config.TEST_SIZE)
            if self.repeat:
                dataset = dataset.repeat()
            if not self.repeat and config.config.NUM_TRAIN_EPOCHS > 1:
                dataset = dataset.repeat(config.config.NUM_TRAIN_EPOCHS)
            dataset = dataset.shuffle(config.config.SHUFFLE_BUFFER_SIZE,
                                      reshuffle_each_iteration=True)

        dataset = dataset.map(self._generate_input_tensors)
        if self.repeat:
            dataset = dataset.repeat()

        if self.is_train:

            dataset = dataset.map(self._parse_reader_input_tensor)
            self.val_dataset = self.val_dataset.map(self._generate_input_tensors)
            self.test_dataset = self.test_dataset.map(self._generate_input_tensors)

            self.val_dataset = self.val_dataset.map(self._parse_reader_input_tensor).batch(1)
            self.test_dataset = self.test_dataset.map(self._parse_reader_input_tensor).batch(1)
            dataset = dataset.batch(config.config.BATCH_SIZE)
        else:
            dataset = dataset.map(lambda x: (((x.path_source_token_indices,
                                               x.path_indices,
                                               x.path_target_token_indices),
                                              x.target_index), x.target_string))
            dataset = dataset.batch(1)
        return dataset

    @tf.function
    def _generate_input_tensors(self, *line):
        """Parses line to ReaderInputTensors"""
        target = line[0]
        target_index = self.vocabs.target_vocab.get_word_to_index_lookup_table().lookup(target)

        contexts = tf.strings.split(tf.stack(line[1:]), sep=",").to_tensor()

        path_sources = tf.slice(contexts, [0, 0], [-1, 1])
        paths = tf.slice(contexts, [0, 1], [-1, 1])
        path_targets = tf.slice(contexts, [0, 2], [-1, 1])

        path_sources_lookup = self.vocabs.token_vocab.get_lookup_index(path_sources)
        paths_lookup = self.vocabs.path_vocab.get_lookup_index(paths)
        path_targets_lookup = self.vocabs.token_vocab.get_lookup_index(path_targets)

        return ReaderInputTensors(target_index=target_index,
                                  path_source_token_indices=path_sources_lookup,
                                  path_indices=paths_lookup,
                                  path_target_token_indices=path_targets_lookup,
                                  path_source_token_strings=path_sources,
                                  path_strings=paths,
                                  path_target_token_strings=path_targets,
                                  target_string=target)

    def get_subdatasets(self):
        return self.val_dataset, self.test_dataset
