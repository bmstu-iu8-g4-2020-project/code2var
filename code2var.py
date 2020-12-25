import csv
import config
import numpy as np
import os
import tensorflow as tf

from abc import ABC
from argparse import ArgumentParser
from tensorflow.python.framework import config as tf_config
from tensorflow.python.keras.utils import tf_utils, metrics_utils
from typing import List, Optional, Callable
from path_context_reader import PathContextReader
from preprocess import NetType
from vocabulary import Code2VecVocabs
from functools import reduce


class Precision(tf.metrics.Metric):
    FilterType = Callable[[tf.Tensor, tf.Tensor], tf.Tensor]

    def __init__(self,
                 index_to_word_table: Optional[tf.lookup.StaticHashTable] = None,
                 topk_predicted_words=None,
                 predicted_words_filters: Optional[List[FilterType]] = None,
                 subtokens_delimiter: str = '|', name=None, dtype=None):
        super(Precision, self).__init__(name=name, dtype=dtype)
        self.true = self.add_weight('true', shape=(), initializer=tf.zeros_initializer)
        self.total = self.add_weight('total', shape=(), initializer=tf.zeros_initializer)
        self.index_to_word_table = index_to_word_table
        self.topk_predicted_words = topk_predicted_words
        self.predicted_words_filters = predicted_words_filters
        self.subtokens_delimiter = subtokens_delimiter

    @tf.function
    def _get_top_predicted_words(self, predictions, k):
        return tf.nn.top_k(predictions, k=k, sorted=True).indices

    def update_state(self, true_target_word, predictions, sample_weight=None):
        """Accumulates true positive, false positive and false negative statistics."""
        if sample_weight is not None:
            raise NotImplemented("WordsSubtokenMetricBase with non-None `sample_weight` is not implemented.")

        top_predicted_words = self._get_top_predicted_words(predictions, 5)
        self.true.assign_add(tf.keras.backend.sum(tf.cast(tf.equal(true_target_word, top_predicted_words), tf.float32)))
        self.total.assign_add(tf.keras.backend.sum(tf.cast(tf.equal(true_target_word, true_target_word), tf.float32)))

    def result(self):
        return tf.math.divide_no_nan(self.true, self.total)

    def reset_states(self):
        for v in self.variables:
            tf.keras.backend.set_value(v, 0)


class GPUEmbedding(tf.keras.layers.Embedding):
    """Fixes problem with tf.keras.layers.Embedding. Original one does not want to work with GPU in Eager Mode."""

    @tf_utils.shape_type_conversion
    def build(self, input_shape):
        self.embeddings = self.add_weight(
            shape=(self.input_dim, self.output_dim),
            initializer=self.embeddings_initializer,
            name="embeddings",
            regularizer=self.embeddings_regularizer,
            constraint=self.embeddings_constraint,
            trainable=True
        )
        self.built = True


class code2vec(tf.keras.Model, ABC):
    def __init__(self,
                 token_vocab_size,
                 target_vocab_size,
                 path_vocab_size,
                 custom_metrics: List,
                 max_contexts=config.config.MAX_CONTEXTS,
                 token_embed_dim=config.config.TOKEN_EMBED_DIMENSION,
                 path_embed_dim=config.config.PATH_EMBED_DIMENSION,
                 dropout_keep_rate=config.config.DROPOUT_KEEP_RATE):
        super(code2vec, self).__init__()
        self.max_contexts: int = max_contexts
        self.token_vocab_size: int = token_vocab_size
        self.target_vocab_size: int = target_vocab_size
        self.path_vocab_size: int = path_vocab_size
        self.token_embed_dim: int = token_embed_dim
        self.path_embed_dim: int = path_embed_dim
        self.dropout_rate: float = 1 - dropout_keep_rate
        self.code_embed_dim: int = 2 * self.token_embed_dim + self.path_embed_dim
        self.custom_metrics = custom_metrics
        self.history = None
        self.model = None  # TODO (RKulagin): look at tf github and check, how they store models
        self.vector_model = None

    def build_model(self, **kwargs):
        if self.model is None:
            input_source_token_embed = tf.keras.Input(shape=(self.max_contexts,), name="input_source_token")
            input_target_token_embed = tf.keras.Input(shape=(self.max_contexts,), name="input_target_token")
            token_embed = GPUEmbedding(input_dim=self.token_vocab_size,
                                       output_dim=self.token_embed_dim,
                                       embeddings_initializer='uniform',
                                       dtype=tf.float32,
                                       name="token_embed")
            token_source_embed_model = tf.keras.Sequential([input_source_token_embed, token_embed])
            token_target_embed_model = tf.keras.Sequential([input_target_token_embed, token_embed])
            input_paths_embed = tf.keras.Input(shape=(self.max_contexts,), name="input_paths")
            paths_embed = GPUEmbedding(input_dim=self.path_vocab_size,
                                       output_dim=self.path_embed_dim,
                                       dtype=tf.float32,
                                       embeddings_initializer='uniform',
                                       name="paths_embed")
            path_embed_model = tf.keras.Sequential([input_paths_embed, paths_embed])
            concatenated_embeds = tf.keras.layers.Concatenate(name="concatenated_embeds")(
                [token_source_embed_model.output, path_embed_model.output, token_target_embed_model.output])

            dropped_embeds = tf.keras.layers.Dropout(self.dropout_rate)(concatenated_embeds)
            flatten_embeds = tf.keras.layers.Reshape((-1, self.code_embed_dim), name="flatten_embeds")(dropped_embeds)
            combined_context_vector = tf.keras.layers.Dense(self.code_embed_dim, activation='sigmoid',
                                                            name="combined_context_vector")(flatten_embeds)
            context_weights = tf.keras.layers.Dense(1, activation='softmax', name="context_weights")(
                combined_context_vector)
            attention_weights = tf.keras.layers.Reshape((-1, self.max_contexts, 1), name="attention_weights")(
                context_weights)

            batched_embed = tf.keras.layers.Reshape((-1, self.max_contexts, self.code_embed_dim),
                                                    name="batched_embed")(combined_context_vector)
            code_vectors = tf.keras.layers.Multiply()([batched_embed, attention_weights])
            code_vectors = tf.keras.backend.squeeze(code_vectors, axis=1)
            code_vectors = tf.keras.backend.sum(code_vectors, axis=1)
            dropped_code_vectors = tf.keras.layers.Dropout(self.dropout_rate)(code_vectors)
            possible_targets = tf.keras.layers.Dense(self.target_vocab_size, activation="softmax",
                                                     name="possible_targets")(dropped_code_vectors)

            inputs = [token_source_embed_model.input, path_embed_model.input, token_target_embed_model.input]
            self.model = tf.keras.Model(inputs=inputs, outputs=possible_targets)
            self.vector_model = tf.keras.Model(inputs=inputs, outputs=code_vectors)
            self.model.compile(optimizer=tf.keras.optimizers.Adam(), metrics=[Precision()],
                               loss=tf.keras.losses.SparseCategoricalCrossentropy())
            # self.vector_model.compile()
            print(self.model.summary())
            tf.keras.utils.plot_model(self.model, show_shapes=True)

    @staticmethod
    def recall(y_true, y_pred):
        """Recall metric.

        Only computes a batch-wise average of recall.

        Computes the recall, a metric for multi-label classification of
        how many relevant items are selected.
        """

        true_positives = tf.keras.backend.sum(tf.keras.backend.round(
            tf.keras.backend.clip(tf.cast(
                tf.cast(tf.keras.backend.transpose(y_true), tf.dtypes.int64) == tf.keras.backend.argmax(y_pred, axis=1),
                tf.dtypes.float32), 0, 1)))
        possible_positives = tf.keras.backend.sum(tf.keras.backend.round(
            tf.keras.backend.clip(tf.cast(tf.keras.backend.argmax(y_true, axis=1) == tf.keras.backend.argmax(y_true, axis=1),
                                          tf.dtypes.float32), 0, 1)))
        # tf.keras.backend.print_tensor(
        #     tf.cast(tf.keras.backend.argmax(y_true, axis=1) == tf.keras.backend.argmax(y_pred, axis=1), tf.dtypes.float32))
        # tf.keras.backend.print_tensor(
        #
        #     tf.cast(tf.keras.backend.argmax(y_true, axis=1) == tf.keras.backend.argmax(y_true, axis=1), tf.dtypes.float32))
        # tf.keras.backend.print_tensor(
        #     true_positives)
        # tf.keras.backend.print_tensor(
        #     possible_positives)
        # tf.keras.backend.print_tensor(y_true)
        # tf.keras.backend.print_tensor(tf.keras.backend.argmax(y_true, axis=1))
        # tf.keras.backend.print_tensor(tf.keras.backend.argmax(y_pred, axis=1))
        recall = true_positives / (possible_positives + tf.keras.backend.epsilon())
        return recall

    @staticmethod
    def f1(y_true, y_pred):
        return tf.keras.backend.sum(
            tf.cast(tf.keras.backend.argmax(y_true, axis=1) == tf.keras.backend.argmax(y_pred, axis=1), tf.dtypes.int32))

    def get_vector(self, inputs):
        return self.vector_model(inputs)

    def train(self,
              dataset,
              epochs,
              callbacks: List[tf.keras.callbacks.Callback],
              **kwargs):
        if self.model is None:
            self.build_model()
        if tf_config.list_logical_devices('GPU'):
            with tf.device("/device:GPU:0"):
                self.history = self.model.fit(dataset, epochs=epochs, callbacks=callbacks, **kwargs)

    def load_weights(self, *args, **kwargs):
        if self.model is None:
            self.build_model()
        self.model.load_weights(*args, **kwargs)

    def evaluate(self,
                 *args, **kwargs):
        if self.model is None:
            self.build_model()
        self.model.evaluate(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.model(*args, **kwargs)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dataset",
                        dest="dataset_name",
                        help="dataset name",
                        required=True)
    parser.add_argument("--train",
                        dest="train",
                        type=bool,
                        help="train net?",
                        required=False,
                        default=False)
    parser.add_argument("--test",
                        dest="test",
                        type=bool,
                        help="test net on test dataset?",
                        required=False,
                        default=False)
    parser.add_argument("--run",
                        dest="run",
                        type=bool,
                        help="run net on given dataset and output predictions",
                        required=False,
                        default=False)
    parser.add_argument("--checkpoints_dir",
                        dest="checkpoints_dir",
                        help="Dir for checkpoints",
                        required=False,
                        default="training")
    parser.add_argument("--net",
                        dest="net",
                        help="net destination type var or vec",
                        required=False,
                        default="vec")
    args = parser.parse_args()

    print("Num GPUs Available: ", len(tf.config.experimental.list_physical_devices('GPU')))
    if args.train:
        print(f"dataset/{args.dataset_name}/{args.dataset_name}.{args.net}.csv")
        c2v_vocabs = Code2VecVocabs(net=NetType(args.net))
        pcr = PathContextReader(is_train=True, vocabs=c2v_vocabs,
                                csv_path=f"dataset/{args.dataset_name}/{args.dataset_name}.{args.net}.csv")
        dataset = pcr.get_dataset()
        val_dataset, test_dataset = pcr.get_subdatasets()
        # init lookups

        c2v_vocabs.target_vocab.get_word_to_index_lookup_table()
        c2v_vocabs.token_vocab.get_word_to_index_lookup_table()
        c2v_vocabs.path_vocab.get_word_to_index_lookup_table()

        TOKEN_VOCAB_SIZE = c2v_vocabs.token_vocab.lookup_table_word_to_index.size().numpy()
        TARGET_VOCAB_SIZE = c2v_vocabs.target_vocab.lookup_table_word_to_index.size().numpy()
        PATH_VOCAB_SIZE = c2v_vocabs.path_vocab.lookup_table_word_to_index.size().numpy()
        tf.random.set_seed(42)
        model = code2vec(token_vocab_size=TOKEN_VOCAB_SIZE,
                         target_vocab_size=TARGET_VOCAB_SIZE,
                         path_vocab_size=PATH_VOCAB_SIZE,
                         custom_metrics=["accuracy"])

        checkpoint_path = f"{args.checkpoints_dir}/" + "cp-{epoch:04d}-{loss:.2f}.hdf5"
        checkpoint_dir = os.path.dirname(checkpoint_path)

        callbacks = [tf.keras.callbacks.ModelCheckpoint(filepath=checkpoint_path,
                                                        save_weights_only=True,
                                                        save_best_only=True,
                                                        monitor='accuracy',
                                                        verbose=1),
                     tf.keras.callbacks.TensorBoard(log_dir='./logs'),

                     tf.keras.callbacks.CSVLogger('training.log')
                     ]
        model.train(dataset, 100, callbacks, validation_data=val_dataset, validation_freq=3)

    if args.run:
        tokens_numbers, target_numbers, path_numbers = 0, 0, 0
        model_path = ""
        if args.net == "vec":
            tokens_numbers = config.config.VEC_NET_TOKEN_SIZE
            target_numbers = config.config.VEC_NET_TARGET_SIZE
            path_numbers = config.config.VEC_NET_PATH_SIZE
            model_path = "cp-0006-3.17/cp-0006-3.17.hdf5"
            # model_path = "training-med-vec-cutted/cp-0010-3.02.hdf5"
        elif args.net == "var":
            tokens_numbers = config.config.VAR_NET_TOKEN_SIZE
            target_numbers = config.config.VAR_NET_TARGET_SIZE
            path_numbers = config.config.VAR_NET_PATH_SIZE
            # model_path = "training/cp-0023.hdf5"
            model_path = "training-sm-var/cp-0002-2.67.hdf5"
        model = code2vec(token_vocab_size=tokens_numbers,
                         target_vocab_size=target_numbers,
                         path_vocab_size=path_numbers,
                         custom_metrics=["accuracy"])
        # model.load_weights("training-code2var-vec/cp-0002-1.91.hdf5")
        model.load_weights(model_path)

        c2v_vocabs = Code2VecVocabs(NetType(args.net))
        pcr = PathContextReader(is_train=False, vocabs=c2v_vocabs,
                                csv_path=f"tmp_data_for_code2var/data.{args.net}.csv")
        dataset = pcr.get_dataset()
        for line, target in dataset:
            result = model(line)
            prediction_index = result.numpy().argsort().astype(np.int32)
            prediction_index = prediction_index[0][:-1 - config.config.NUMBER_OF_PREDICTIONS:-1]
            prediction = c2v_vocabs.target_vocab.get_index_to_word_lookup_table().lookup(tf.constant(prediction_index))
            print(target.numpy(), "->", prediction.numpy())
            with open(f"tmp_data_for_code2var/result.{args.net}.csv", 'a', encoding='utf8') as file:
                writer = csv.writer(file)
                writer.writerow(np.concatenate([target.numpy().astype("U"), prediction.numpy().astype('U')]))
