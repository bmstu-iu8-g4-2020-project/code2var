#!/usr/bin/env bash
# Copyright 2020 RKulagin

PYTHON=python3
if [ $# -eq 0 ]
  then
    echo "No dataset name provided"
    exit 1
fi
if [ $# -eq 2 ]
  then
    CHECKPOINTS_DIR_PARAM = --checkpoints_dir $2
fi
DATASET_NAME=$1
${PYTHON} code2vec_train_model.py --dataset $DATASET_NAME $CHECKPOINTS_DIR_PARAM --net var --train true