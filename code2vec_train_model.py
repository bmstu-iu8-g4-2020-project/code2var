import os
from typing import List

import tensorflow as tf
from tensorflow.python.framework import config as tf_config
from tensorflow.python.keras.utils import tf_utils

import config
from path_context_reader import PathContextReader
from vocabulary import Code2VecVocabs

import json


class GPUEmbedding(tf.keras.layers.Embedding):
    @tf_utils.shape_type_conversion
    def build(self, input_shape):
        self.embeddings = self.add_weight(
            shape=(self.input_dim, self.output_dim),
            initializer=self.embeddings_initializer,
            name="embeddings",
            regularizer=self.embeddings_regularizer,
            constraint=self.embeddings_constraint,
        )
        self.built = True


class code2vec(tf.keras.Model):
    def __init__(self, token_vocab_size, target_vocab_size, path_vocab_size, max_contexts=config.config.MAX_CONTEXTS,
                 embed_dim=config.config.EMBED_DIMENSION, dropout_keep_rate=config.config.DROPOUT_KEEP_RATE):
        super(code2vec, self).__init__()
        self.max_contexts: int = max_contexts
        self.token_vocab_size: int = token_vocab_size
        self.target_vocab_size: int = target_vocab_size
        self.path_vocab_size: int = path_vocab_size
        self.embed_dim: int = embed_dim
        self.dropout_rate: float = 1 - dropout_keep_rate
        self.code_embed_dim: int = 3 * self.embed_dim  # 2*leaves_embed_dim + path_embed_dim
        self.history = None
        self.model = None  # TODO (RKulagin): look at tf github and check, how they store models
        self.vector_model = None

    def build_model(self, **kwargs):
        if self.model is None:
            input_source_token_embed = tf.keras.Input(shape=(self.max_contexts,), name="input_source_token")
            input_target_token_embed = tf.keras.Input(shape=(self.max_contexts,), name="input_target_token")
            token_embed = GPUEmbedding(input_dim=self.token_vocab_size,
                                       output_dim=self.embed_dim,
                                       embeddings_initializer='uniform',
                                       dtype=tf.float32,
                                       name="token_embed")
            token_source_embed_model = tf.keras.Sequential([input_source_token_embed, token_embed])
            token_target_embed_model = tf.keras.Sequential([input_target_token_embed, token_embed])
            input_paths_embed = tf.keras.Input(shape=(self.max_contexts,), name="input_paths")
            paths_embed = GPUEmbedding(input_dim=self.path_vocab_size,
                                       output_dim=self.embed_dim,
                                       dtype=tf.float32,
                                       embeddings_initializer='uniform',
                                       name="paths_embed")
            path_embed_model = tf.keras.Sequential([input_paths_embed, paths_embed])
            concatenated_embeds = tf.keras.layers.Concatenate(name="concatenated_embeds")(
                [token_source_embed_model.output, path_embed_model.output, token_target_embed_model.output])

            droped_embeds = tf.keras.layers.Dropout(self.dropout_rate)(concatenated_embeds)
            flatten_embeds = tf.keras.layers.Reshape((-1, self.code_embed_dim), name="flatten_embeds")(droped_embeds)
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
            possible_targets = tf.keras.layers.Dense(self.target_vocab_size, activation="softmax",
                                                     name="possible_targets")(
                code_vectors)

            inputs = [token_source_embed_model.input, path_embed_model.input, token_target_embed_model.input]
            self.model = tf.keras.Model(inputs=inputs, outputs=possible_targets)
            self.vector_model = tf.keras.Model(inputs=inputs, outputs=code_vectors)
            self.model.compile(optimizer=tf.keras.optimizers.Adam(), metrics=['accuracy'],
                               loss=tf.keras.losses.SparseCategoricalCrossentropy())
            # self.vector_model.compile()
            print(self.model.summary())

    def get_vector(self, inputs):
        return self.vector_model(inputs)

    def train(self, dataset, epochs, callbacks: List[tf.keras.callbacks.ModelCheckpoint], **kwargs):
        if self.model is None:
            self.build_model()
        if tf_config.list_logical_devices('GPU'):
            with tf.device("/device:GPU:0"):
                self.history = self.model.fit(dataset, epochs=epochs, callbacks=callbacks, **kwargs)

    def load_weights(self,
                     filepath,
                     by_name=False,
                     skip_mismatch=False,
                     options=None):
        self.model.load_weights(filepath, by_name, skip_mismatch, options)

    def evaluate(self,
                 *args, **kwargs):
        if self.model is None:
            self.build_model()
        self.model.evaluate(*args, **kwargs)


if __name__ == "__main__":
    # tf.debugging.set_log_device_placement(True)
    print("Num GPUs Available: ", len(tf.config.experimental.list_physical_devices('GPU')))
    config.config.CREATE_VOCAB = True
    config.config.TRAINING_FREQ_DICTS_PATH = "dataset/java-small/java-small.c2v.dict"
    c2v_vocabs = Code2VecVocabs()
    pcr = PathContextReader(is_train=True, vocabs=c2v_vocabs, csv_path="dataset/java-small/java-small.train_vec.csv")
    dataset = pcr.get_dataset()
    # init lookups

    c2v_vocabs.target_vocab.get_word_to_index_lookup_table()
    c2v_vocabs.token_vocab.get_word_to_index_lookup_table()
    c2v_vocabs.path_vocab.get_word_to_index_lookup_table()

    TOKEN_VOCAB_SIZE = c2v_vocabs.token_vocab.lookup_table_word_to_index.size().numpy()
    TARGET_VOCAB_SIZE = c2v_vocabs.target_vocab.lookup_table_word_to_index.size().numpy()
    PATH_VOCAB_SIZE = c2v_vocabs.path_vocab.lookup_table_word_to_index.size().numpy()
    tf.random.set_seed(42)
    model = code2vec(token_vocab_size=TOKEN_VOCAB_SIZE, target_vocab_size=TARGET_VOCAB_SIZE,
                     path_vocab_size=PATH_VOCAB_SIZE)

    checkpoint_path = "training_1/cp-{epoch:04d}.hdf5"
    checkpoint_dir = os.path.dirname(checkpoint_path)

    cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=checkpoint_path,
                                                     save_weights_only=True,
                                                     save_best_only=True,
                                                     monitor='accuracy',
                                                     verbose=1)

    callbacks = [cp_callback, tf.keras.callbacks.TensorBoard(log_dir='./logs'),
                 tf.keras.callbacks.EarlyStopping(
                     monitor="loss",
                     min_delta=0.01,
                     mode="auto",
                 )]

    # config.config.TRAINING_FREQ_DICTS_PATH = "dataset-1/java-small/java-small.c2v.dict"
    val_pcr = PathContextReader(is_train=True, vocabs=c2v_vocabs,
                                csv_path="dataset/java-small/java-small.test_vec.csv")
    val_dataset = val_pcr.get_dataset()
    #
    model.evaluate(dataset)
    model.evaluate(val_dataset)
    model.train(dataset, 100, callbacks, validation_data=val_dataset)
    print(model.history.histor1)
    json.dump(model.history.history, open("training_1/code2vec_history.json", "w"))
    # model2 = code2vec(token_vocab_size=TOKEN_VOCAB_SIZE, target_vocab_size=TARGET_VOCAB_SIZE,
    #                   path_vocab_size=PATH_VOCAB_SIZE)
    #
    # model2.build_model()
    # model2.load_weights('training_2/cp-0035.hdf5')
    # it = iter(val_dataset)
    # for line in it:
    #     print(line)
    #     vectors = model2.get_vector(line)
    # import numpy as np
    #
    # res_arr =[[0 for j in range(6)] for i in range(6)]
    # for i in range(len(vectors)):
    #     for j in range(len(vectors)):
    #         res_arr[i][j] = np.dot(vectors[i], vectors[j]) / np.sqrt(
    #             np.dot(vectors[i], vectors[i]) * np.dot(vectors[j], vectors[j]))
    #
    # print(np.array(res_arr))
