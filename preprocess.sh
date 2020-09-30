#!/usr/bin/env bash
# Copyright 2020 RKulagin
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
THREADS=64
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


FUNCTIONS_VOCABULARY=dataset/${DATASET_NAME}/${DATASET_NAME}.train.functions.vocab
LEAVES_VOCABULARY=dataset/${DATASET_NAME}/${DATASET_NAME}.train.leaves.vocab
PATH_VOCABULARY=dataset/${DATASET_NAME}/${DATASET_NAME}.train.path.vocab
# Script

mkdir -p dataset
mkdir -p dataset/${DATASET_NAME}

cd JavaExtractor/JPredict/ && mvn clean install && cd ../..


if [ ${OBFUSCATING} = true ]
then
  echo "Obfuscating files"
  # TODO (RKulagin): create obfuscation
fi

# Extract AST path for code2vec
echo "Processing train files from "${TRAIN_FILES_DIR}
${PYTHON} JavaExtractor/extract.py -maxlen ${MAX_PATH_LENGTH} -maxwidth ${MAX_PATH_WIDTH} -j ${EXTRACTOR_JAR} \
  --dir ${TRAIN_FILES_DIR} --obfuscate true > ${TRAIN_PATH_VEC}
echo "Done. Generated ${TRAIN_PATH_VEC}"

echo "Processing test files from "${TEST_FILES_DIR}
${PYTHON} JavaExtractor/extract.py -maxlen ${MAX_PATH_LENGTH} -maxwidth ${MAX_PATH_WIDTH} -j ${EXTRACTOR_JAR} \
  --dir ${TEST_FILES_DIR} --obfuscate true > ${TEST_PATH_VEC}
echo "Done. Generated ${TEST_PATH_VEC}"

echo "Processing train files from "${VALIDATION_FILES_DIR}
${PYTHON} JavaExtractor/extract.py -maxlen ${MAX_PATH_LENGTH} -maxwidth ${MAX_PATH_WIDTH} -j ${EXTRACTOR_JAR} \
  --dir ${VALIDATION_FILES_DIR} --obfuscate true > ${VALIDATION_PATH_VEC}
echo "Done. Generated ${VALIDATION_PATH_VEC}"

# Extract AST path for code2var
echo "Processing train files from "${TRAIN_FILES_DIR}
${PYTHON} JavaExtractor/extract.py -maxlen ${MAX_PATH_LENGTH} -maxwidth ${MAX_PATH_WIDTH} -j ${EXTRACTOR_JAR} \
  --dir ${TRAIN_FILES_DIR} --only_for_vars true  --obfuscate true> ${TRAIN_PATH_VAR}
echo "Done. Generated ${TRAIN_PATH_VAR}"

echo "Processing test files from "${TEST_FILES_DIR}
${PYTHON} JavaExtractor/extract.py -maxlen ${MAX_PATH_LENGTH} -maxwidth ${MAX_PATH_WIDTH} -j ${EXTRACTOR_JAR} \
  --dir ${TEST_FILES_DIR} --only_for_vars true --obfuscate true> ${TEST_PATH_VAR}
echo "Done. Generated ${TEST_PATH_VAR}"

echo "Processing train files from "${VALIDATION_FILES_DIR}
${PYTHON} JavaExtractor/extract.py -maxlen ${MAX_PATH_LENGTH} -maxwidth ${MAX_PATH_WIDTH} -j ${EXTRACTOR_JAR} \
  --dir ${VALIDATION_FILES_DIR} --only_for_vars true --obfuscate true> ${VALIDATION_PATH_VAR}
echo "Done. Generated ${VALIDATION_PATH_VAR}"


# Generate vocabularies for train code2vec

echo "Generating vocabularies from ${TRAIN_PATH_VEC}"
cut -d ' ' -f1 < ${TRAIN_PATH_VEC} | awk '{n[$0]++} END {for (i in n) print i,n[i]}' > ${FUNCTIONS_VOCABULARY}
cut -d' ' -f2- < ${TRAIN_PATH_VEC} | tr ' ' '\n' | cut -d',' -f1,3 | tr ',' '\n' | \
awk '{n[$0]++} END {for (i in n) print i,n[i]}' > ${LEAVES_VOCABULARY}
cut -d' ' -f2- < ${TRAIN_PATH_VEC} | tr ' ' '\n' | cut -d',' -f2 | \
awk '{n[$0]++} END {for (i in n) print i,n[i]}' > ${PATH_VOCABULARY}

# Preprocess for code2vec

chmod +x preprocess.py

${PYTHON} preprocess.py --train_data_vec ${TRAIN_PATH_VEC} --test_data_vec ${TEST_PATH_VEC} \
  --val_data_vec ${VALIDATION_PATH_VEC} --train_data_var ${TRAIN_PATH_VAR} --test_data_var ${TEST_PATH_VAR} \
  --val_data_var ${VALIDATION_PATH_VAR}   --max_contexts ${MAX_CONTEXTS} \
  --word_vocab_size ${WORD_VOCABULARY_SIZE} --path_vocab_size ${PATH_VOCABULARY_SIZE} \
  --target_vocab_size ${TARGET_VOCABULARY_SIZE} --target_histogram ${FUNCTIONS_VOCABULARY} \
  --word_histogram ${LEAVES_VOCABULARY} --path_histogram ${PATH_VOCABULARY} \
  --output_name dataset/${DATASET_NAME}/${DATASET_NAME} --net code2vec

# Preprocess for code2var