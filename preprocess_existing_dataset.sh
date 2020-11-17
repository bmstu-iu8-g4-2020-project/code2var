#!/usr/bin/env bash
# Copyright 2020 RKulagin
set -e

DATASET_NAME=java-small

# List of constants
MAX_CONTEXTS=300
WORD_VOCABULARY_SIZE=1301130
PATH_VOCABULARY_SIZE=1301130
TARGET_VOCABULARY_SIZE=118170

PYTHON=python3

if [ $# -eq 0 ]
  then
    MIN_OCCURRENCES=1
  else
    MIN_OCCURRENCES=$1
fi


TRAIN_PATH_VEC=dataset/${DATASET_NAME}/${DATASET_NAME}.train.paths.code2vec
TEST_PATH_VEC=dataset/${DATASET_NAME}/${DATASET_NAME}.test.paths.code2vec
VALIDATION_PATH_VEC=dataset/${DATASET_NAME}/${DATASET_NAME}.validation.paths.code2vec

#TRAIN_PATH_VAR=dataset/${DATASET_NAME}/${DATASET_NAME}.train.paths.code2var
#TEST_PATH_VAR=dataset/${DATASET_NAME}/${DATASET_NAME}.test.paths.code2var
#VALIDATION_PATH_VAR=dataset/${DATASET_NAME}/${DATASET_NAME}.validation.paths.code2var
TRAIN_PATH_VAR=empty
TEST_PATH_VAR=empty
VALIDATION_PATH_VAR=empty

FUNCTIONS_VOCABULARY_TRAIN=dataset/${DATASET_NAME}/${DATASET_NAME}.train.functions.vocab
FUNCTIONS_VOCABULARY_TEST=dataset/${DATASET_NAME}/${DATASET_NAME}.test.functions.vocab
FUNCTIONS_VOCABULARY_VAL=dataset/${DATASET_NAME}/${DATASET_NAME}.validation.functions.vocab
LEAVES_VOCABULARY=dataset/${DATASET_NAME}/${DATASET_NAME}.train.leaves.vocab
PATH_VOCABULARY=dataset/${DATASET_NAME}/${DATASET_NAME}.train.path.vocab

# Generate vocabularies for train code2vec

echo "Generating vocabularies from ${TRAIN_PATH_VEC}"
cut -d ' ' -f1 < ${TRAIN_PATH_VEC} | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > ${FUNCTIONS_VOCABULARY_TRAIN}
cut -d ' ' -f1 < ${TEST_PATH_VEC} | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > ${FUNCTIONS_VOCABULARY_TEST}
cut -d ' ' -f1 < ${VALIDATION_PATH_VEC} | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > ${FUNCTIONS_VOCABULARY_VAL}

# Preprocess for code2vec

chmod +x preprocess.py

${PYTHON} preprocess.py --train_data_vec ${TRAIN_PATH_VEC} --test_data_vec ${TEST_PATH_VEC} \
  --val_data_vec ${VALIDATION_PATH_VEC} --train_data_var ${TRAIN_PATH_VAR} --test_data_var ${TEST_PATH_VAR} \
  --val_data_var ${VALIDATION_PATH_VAR}   --max_contexts ${MAX_CONTEXTS} \
  --word_vocab_size ${WORD_VOCABULARY_SIZE} --path_vocab_size ${PATH_VOCABULARY_SIZE} \
  --target_vocab_size ${TARGET_VOCABULARY_SIZE} --target_histogram_train ${FUNCTIONS_VOCABULARY_TRAIN} --target_histogram_test ${FUNCTIONS_VOCABULARY_TEST} --target_histogram_val ${FUNCTIONS_VOCABULARY_VAL} \
  --word_histogram ${LEAVES_VOCABULARY} --path_histogram ${PATH_VOCABULARY} \
  --output_name dataset/${DATASET_NAME}/${DATASET_NAME} --net code2vec --occurrences $MIN_OCCURRENCES
