#!/usr/bin/env bash

wget https://s3.amazonaws.com/code2seq/datasets/java-small.tar.gz
mkdir -p dataset/java-small
tar -C dataset/ -xzf java-small.tar.gz
pwd
ls -a
rm -rf java-small.tar.gz