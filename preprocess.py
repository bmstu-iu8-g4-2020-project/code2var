#!/usr/bin/python
import os
import pickle
import random
import config

from argparse import ArgumentParser
from typing import Optional


def parse_vocab(path, min_frequency=1, limit: Optional[int] = None):
    """
        Parse histogram files containing target|token|path and their frequency pairs.
        Creates word to frequency dicts for future uploading to the Vocab.

        Note that parsed file for token and path should be generated from functions with pre-limited targets to avoid
        redundant data in token and path freq_dicts.
    Args:
        path (): string contains path to file with parsed pairs "word frequency"
        min_frequency (): integer value, value of hyper-parameter limiting number of occurrences required to be included
                            to the dict
        limit (): optional hyper-parameter that should protect freq_dicts from being too big if minimal frequency is too low.
    Raises:
        ValueError if file opened from path is empty or doesn't content any matching required pair line.
    Returns:
        dict containing words in keys and their frequencies in values.
    """

    with open(path, "r") as file:
        word_to_freq = (line.rstrip("\n").split(" ") for line in file)
        word_to_freq = filter(lambda x: len(x) == 2 and int(x[1]) > min_frequency, word_to_freq)
        word_to_freq = sorted(word_to_freq, key=lambda line: line[1])
        word_to_freq = dict(word_to_freq[:limit])
    if len(word_to_freq) != 0:
        return word_to_freq
    raise ValueError("Empty or incorrect file given. Path: " + path)


def save_dictionaries(path_freq, target_freq, word_freq, output_filename):
    """
        Dumps generated word to frequency dictionaries to .c2v.dict file using pickle
    """
    output_file_path = output_filename + ".c2v.dict"
    with open(output_file_path, "wb") as file:
        pickle.dump(word_freq, file)
        pickle.dump(path_freq, file)
        pickle.dump(target_freq, file)
        print("Frequency dictionaries saved to: " + output_filename + ".c2v.dict")


def process_file(file_path, max_contexts, out_file_path, target_freq):
    """
        Process file with AST paths, generate new csv file with correct number of context (each line should have similar
        number of tuple (leave, path, leave) even if it is empty
    Args:
        file_path (): path to file containing AST paths to be parsed
        max_contexts (): limit max number of paths in AST for each fucntion.
            Functions with lower number of paths will be filled with empty ones.
        out_file_path (): path to csv file that will be generated
        target_freq (): word to frequency dict that will filter functions before adding them to csv.
    Returns:
        None
    """
    with open(file_path, 'r') as file:
        with open(out_file_path + '.csv', 'w') as output:
            for line in file:
                contexts = line.rstrip('\n').split(" ")
                assert len(contexts) > 0
                target, contexts = contexts[0], contexts[1:]
                if target in target_freq:
                    if len(contexts) > max_contexts:
                        contexts = random.sample(contexts, max_contexts)
                    empty_filler = " " * (max_contexts - len(contexts))
                    output.write(f"{target} {' '.join(contexts)}{empty_filler}\n")
    print("processed file + " + file_path)
    print("generated file + " + out_file_path + ".csv")


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--train_data_vec", dest="train_data_path_vec",
                        required=True)
    parser.add_argument("--test_data_vec", dest="test_data_path_vec",
                        required=True)
    parser.add_argument("--val_data_vec", dest="val_data_path_vec",
                        required=True)
    parser.add_argument("--train_data_var", dest="train_data_path_var",
                        required=True)
    parser.add_argument("--test_data_var", dest="test_data_path_var",
                        required=True)
    parser.add_argument("--val_data_var", dest="val_data_path_var",
                        required=True)
    parser.add_argument("--max_contexts", dest="max_contexts", default=200,
                        required=False)
    parser.add_argument("--word_vocab_size", dest="word_vocab_size",
                        default=1301136, required=False)
    parser.add_argument("--path_vocab_size", dest="path_vocab_size",
                        default=911417, required=False)
    parser.add_argument("--target_vocab_size", dest="target_vocab_size",
                        default=261245, required=False)
    parser.add_argument("--word_histogram", dest="word_histogram",
                        metavar="FILE", required=True)
    parser.add_argument("--path_histogram", dest="path_histogram",
                        metavar="FILE", required=True)
    parser.add_argument("--target_histogram", dest="target_histogram",
                        metavar="FILE", required=True)
    parser.add_argument("--net", dest="net", required=True)
    parser.add_argument("--output_name", dest="output_name", metavar="FILE",
                        required=True,
                        default='data')
    args = parser.parse_args()

    train_data_path_vec = args.train_data_path_vec
    test_data_path_vec = args.test_data_path_vec
    val_data_path_vec = args.val_data_path_vec
    train_data_path_var = args.train_data_path_var
    test_data_path_var = args.train_data_path_var
    val_data_path_var = args.val_data_path_var

    target_freq = parse_vocab(args.target_histogram, limit=config.config.TARGET_VOCAB_SIZE)

    for data_path, data_role in zip(
            [test_data_path_vec, val_data_path_vec, train_data_path_vec],
            ['test_vec', 'val_vec', 'train_vec', 'test_var', 'val_var',
             'train_var']):
        process_file(file_path=data_path,
                     max_contexts=int(args.max_contexts),
                     target_freq=target_freq,
                     out_file_path=args.output_name + "." + data_role)

    # Generate token - frequency file to future parsing in parse_vocab.
    # Splits csv file by space remove path and generate frequency for each line.
    # csv is split instead of .code2vec because we don't want redundant tokens from not filtered functions to be included.
    os.system(
        f"cut -d' ' -f2- < {args.output_name + '.train_vec.csv'} | tr ' ' '\n' | cut -d',' -f1,3 | tr ',' '\n' | "
        "awk '{n[$0]++} END {for (i in n) print i,n[i]}' > " + f"{args.word_histogram}")
    # Generate path - frequency file to future parsing in parse_vocab.
    # Splits csv file by space remove tokens and generate frequency for each line.
    # csv is split instead of .code2vec because we don't want redundant paths from not filtered functions to be included.
    os.system(
        f"cut -d' ' -f2- < {args.output_name + '.train_vec.csv'} | tr ' ' '\n' | cut -d',' -f2 | "
        "awk '{n[$0]++} END {for (i in n) print i,n[i]}' > " + f"{args.path_histogram}")

    path_freq = parse_vocab(args.path_histogram)
    word_freq = parse_vocab(args.word_histogram)

    save_dictionaries(target_freq=target_freq, path_freq=path_freq,
                      word_freq=word_freq,
                      output_filename=args.output_name)
