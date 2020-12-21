#!/usr/bin/env bash
# Copyright 2020 RKulagin

PYTHON=python3
if [ $# -eq 0 ]
  then
    echo "No dataset name provided"
    exit 1
fi
DATASET_NAME=$1

if [ $# -eq 2 ]
  then
    CHECKPOINTS_DIR=$2
    mkdir $2
    ${PYTHON} code2var.py --dataset $DATASET_NAME --checkpoints_dir $CHECKPOINTS_DIR --net vec --train true
  else
    ${PYTHON} code2var.py --dataset $DATASET_NAME --net var --train true
fi
