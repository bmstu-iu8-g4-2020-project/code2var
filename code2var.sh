#!/usr/bin/env bash
# Copyright 2020 RKulagin

PYTHON=python3
if [ $# -eq 0 ]
  then
    echo "No file provided"
    exit 1
fi

FILE=$1

mkdir tmp_data_for_code2var/
cp $FILE tmp_data_for_code2var/file.java

chmod +x preprocess_single_file.sh
./preprocess_single_file.sh tmp_data_for_code2var/file.java tmp_data_for_code2var

${PYTHON} code2var.py --net var --dataset java-small --run true > tmp_data_for_code2var/code2var.log

java -cp JavaExtractor/JPredict/target/JavaExtractor-0.0.1-SNAPSHOT.jar JavaExtractor.App --file $FILE

rm -rf tmp_data_for_code2var/