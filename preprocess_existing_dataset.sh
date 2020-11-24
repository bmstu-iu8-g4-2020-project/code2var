#!/usr/bin/env bash
set -e

DATASET_NAME=java-small

TRAIN_FILES_DIR=dataset/${DATASET_NAME}/training/
VALIDATION_FILES_DIR=dataset/${DATASET_NAME}/validation/
TEST_FILES_DIR=dataset/${DATASET_NAME}/test/

if [ ${DATASET_NAME} == java-small ] && [ ! -d ${TRAIN_FILES_DIR} ]
 then
   chmod +x scripts/download_dataset.sh
   pwd
  scripts/download_dataset.sh
fi

# List of constants
MAX_CONTEXTS=300
WORD_VOCABULARY_SIZE=1301136 # As in original c2v. I don't know why this value
PATH_VOCABULARY_SIZE=911417
TARGET_VOCABULARY_SIZE=261245
THREADS=1
MAX_PATH_LENGTH=8
MAX_PATH_WIDTH=2
OBFUSCATING=true

PYTHON=python3

EXTRACTOR_JAR=JavaExtractor/JPredict/target/JavaExtractor-0.0.1-SNAPSHOT.jar


TRAIN_PATH_VEC=dataset/${DATASET_NAME}/${DATASET_NAME}.train.paths.code2vec
TEST_PATH_VEC=dataset/${DATASET_NAME}/${DATASET_NAME}.test.paths.code2vec
VALIDATION_PATH_VEC=dataset/${DATASET_NAME}/${DATASET_NAME}.validation.paths.code2vec

TRAIN_PATH_VAR=dataset/${DATASET_NAME}/${DATASET_NAME}.train.paths.code2var
TEST_PATH_VAR=dataset/${DATASET_NAME}/${DATASET_NAME}.test.paths.code2var
VALIDATION_PATH_VAR=dataset/${DATASET_NAME}/${DATASET_NAME}.validation.paths.code2var


FUNCTIONS_VOCABULARY_TRAIN=dataset/${DATASET_NAME}/${DATASET_NAME}.train.functions.vocab
FUNCTIONS_VOCABULARY_TEST=dataset/${DATASET_NAME}/${DATASET_NAME}.test.functions.vocab
FUNCTIONS_VOCABULARY_VAL=dataset/${DATASET_NAME}/${DATASET_NAME}.validation.functions.vocab

LEAVES_VOCABULARY_VEC=dataset/${DATASET_NAME}/${DATASET_NAME}.train.leaves.vocab
PATH_VOCABULARY_VEC=dataset/${DATASET_NAME}/${DATASET_NAME}.train.path.vocab

VARIABLES_VOCABULARY_TRAIN=dataset/${DATASET_NAME}/${DATASET_NAME}.train.variables.vocab
VARIABLES_VOCABULARY_TEST=dataset/${DATASET_NAME}/${DATASET_NAME}.test.variables.vocab
VARIABLES_VOCABULARY_VAL=dataset/${DATASET_NAME}/${DATASET_NAME}.validation.variables.vocab
LEAVES_VOCABULARY_VAR=dataset/${DATASET_NAME}/${DATASET_NAME}.var.train.leaves.vocab
PATH_VOCABULARY_VAR=dataset/${DATASET_NAME}/${DATASET_NAME}.var.train.path.vocab


# Generate vocabularies for code2vec
find ${TRAIN_FILES_DIR} -name '*.data.log' -exec cat {} > ${TRAIN_PATH_VAR} \;

#echo "Generating vocabularies from ${TRAIN_PATH_VEC}"
#cut -d ' ' -f1 < ${TRAIN_PATH_VEC} | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > ${FUNCTIONS_VOCABULARY_TRAIN}
#cut -d ' ' -f1 < ${TEST_PATH_VEC} | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > ${FUNCTIONS_VOCABULARY_TEST}
#cut -d ' ' -f1 < ${VALIDATION_PATH_VEC} | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > ${FUNCTIONS_VOCABULARY_VAL}
#
## Generate vocabularies for code2vec
#echo "Generating target histogram from ${TRAIN_PATH_VAR}"
#cut -d ' ' -f1 < $TRAIN_PATH_VAR | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > $VARIABLES_VOCABULARY_TRAIN
#cut -d ' ' -f1 < $TEST_PATH_VAR | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > $VARIABLES_VOCABULARY_TEST
#cut -d ' ' -f1 < $VALIDATION_PATH_VAR | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > $VARIABLES_VOCABULARY_VAL


# Preprocess for code2vec

chmod +x preprocess.py

${PYTHON} preprocess.py --data_dir dataset/${DATASET_NAME} --combined_file ${TRAIN_PATH_VAR} --max_contexts ${MAX_CONTEXTS} \
  --output_name dataset/${DATASET_NAME}/${DATASET_NAME} --net var

