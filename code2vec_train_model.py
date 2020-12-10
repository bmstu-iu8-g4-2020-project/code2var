import csv
import config
import numpy as np
import os
import tensorflow as tf

from abc import ABC
from argparse import ArgumentParser
from tensorflow.python.framework import config as tf_config
from tensorflow.python.keras.utils import tf_utils
from typing import List
from path_context_reader import PathContextReader
from vocabulary import Code2VecVocabs


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
            self.model.compile(optimizer=tf.keras.optimizers.Adam(), metrics=['accuracy'],
                               loss=tf.keras.losses.SparseCategoricalCrossentropy())
            # self.vector_model.compile()
            print(self.model.summary())

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
        config.config.CREATE_VOCAB = True
        config.config.TRAINING_FREQ_DICTS_PATH = f"dataset/{args.dataset_name}/{args.dataset_name}.{args.net}.c2v.dict"
        c2v_vocabs = Code2VecVocabs()
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
                         path_vocab_size=PATH_VOCAB_SIZE)

        checkpoint_path = f"{args.checkpoints_dir}/" + "cp-{epoch:04d}-{val_loss:.2f}.hdf5"
        checkpoint_dir = os.path.dirname(checkpoint_path)

        callbacks = [tf.keras.callbacks.ModelCheckpoint(filepath=checkpoint_path,
                                                        save_weights_only=True,
                                                        save_best_only=True,
                                                        monitor='accuracy',
                                                        verbose=1),
                     tf.keras.callbacks.TensorBoard(log_dir='./logs'),

                     tf.keras.callbacks.CSVLogger('training.log')
                     ]
        if val_dataset is None:
            model.train(dataset, 100, callbacks)
        else:
            model.train(dataset, 100, callbacks, validation_data=val_dataset)

    if args.run:
        model = code2vec(token_vocab_size=config.config.NET_TOKEN_SIZE,
                         target_vocab_size=config.config.NET_TARGET_SIZE,
                         path_vocab_size=config.config.NET_PATH_SIZE)
        model.load_weights("training/cp-0023.hdf5")

        config.config.CREATE_VOCAB = True
        config.config.TRAINING_FREQ_DICTS_PATH = f"dataset/java-small/java-small.var.c2v.dict"
        c2v_vocabs = Code2VecVocabs()
        pcr = PathContextReader(is_train=False, vocabs=c2v_vocabs,
                                csv_path=f"tmp_data_for_code2var/data.var.csv")
        dataset = pcr.get_dataset()
        for line, target in dataset:
            result = model(line)
            prediction_index = result.numpy().argsort().astype(np.int32)
            prediction_index = prediction_index[0][:-6:-1]
            prediction = c2v_vocabs.target_vocab.get_index_to_word_lookup_table().lookup(tf.constant(prediction_index))
            print(target.numpy(), "->", prediction.numpy())
            with open("tmp_data_for_code2var/result.csv", 'a', encoding='utf8') as file:
                writer = csv.writer(file)
                writer.writerow(np.concatenate([target.numpy().astype("U"), prediction.numpy().astype('U')]))
