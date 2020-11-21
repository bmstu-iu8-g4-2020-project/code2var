#!/usr/bin/python
import os
import pickle
import random
import config

from argparse import ArgumentParser
from typing import Optional, List


def parse_vocab(path: str, min_frequency: int = 1, limit: Optional[int] = None):
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
        word_to_freq = filter(lambda x: len(x) == 2 and int(x[1]) > int(min_frequency) and "|" not in x[0], word_to_freq)
        word_to_freq = sorted(word_to_freq, key=lambda line: line[1])
        word_to_freq = dict(word_to_freq[:limit])
    if len(word_to_freq) != 0:
        return word_to_freq
    raise ValueError("Empty or incorrect file given. Path: " + path)


def save_dictionaries(path_freq, target_freq_train, target_freq_test, target_freq_val, word_freq, output_filename):
    """
        Dumps generated word to frequency dictionaries to .c2v.dict file using pickle
    """
    output_file_path = output_filename + ".c2v.dict"
    with open(output_file_path, "wb") as file:
        pickle.dump(word_freq, file)
        pickle.dump(path_freq, file)
        pickle.dump(target_freq_train, file)
        pickle.dump(target_freq_test, file)
        pickle.dump(target_freq_val, file)
        print("Frequency dictionaries saved to: " + output_filename + ".c2v.dict")


def process_file(file_path, max_contexts, out_file_path, target_freq=None):
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
                if target_freq is None or target in target_freq:
                    if len(contexts) > max_contexts:
                        contexts = random.sample(contexts, max_contexts)
                    empty_filler = " " * (max_contexts - len(contexts))
                    output.write(f"{target} {' '.join(contexts)}{empty_filler}\n")
    print("processed file + " + file_path)
    print("generated file + " + out_file_path + ".csv")


def process_net(target_histogram_train: str,
                target_histogram_test: str,
                target_histogram_val: str,
                word_histogram_path: str,
                path_histogram_path: str,
                data_paths: List[str],
                data_roles: List[str],
                net_type: str):
    """
        Process target files for train, test and validation datasets,
        generates token and path vocabs|histograms for training dataset.
    Args:
        target_histogram_train (): path to file contains pairs (target, frequency) separated by space for train dataset
        target_histogram_test (): path to file contains pairs (target, frequency) separated by space for test dataset
        target_histogram_val (): path to file contains pairs (target, frequency) separated by space for validation dataset
        word_histogram_path (): path to file where pairs (token, frequency) should be saved
        path_histogram_path (): path to file where pairs (path, frequency) should be saved
        data_paths (): list of paths to files containing extracted AST paths
        NOTE! data_paths should have length 3 for train, test and validation files
        data_roles (): list of names for data in data_path
        net_type (): vec or var

    """
    target_freq_train = parse_vocab(target_histogram_train, min_frequency=args.min_occurrences)
    target_freq_test = parse_vocab(target_histogram_test, min_frequency=args.min_occurrences)
    target_freq_val = parse_vocab(target_histogram_val, min_frequency=args.min_occurrences)

    assert len(data_paths) == 3
    assert len(data_roles) == 3

    for data_path, data_role in zip(data_paths, data_roles):
        process_file(file_path=data_path,
                     max_contexts=args.max_contexts,
                     target_freq=target_freq_train,
                     out_file_path=f"{args.output_name}.{data_role}")

    # Generate token - frequency file to future parsing in parse_vocab.
    # Splits csv file by space remove path and generate frequency for each line.
    # csv is split instead of .code2vec/var because we don't want redundant tokens from not filtered functions to be included.
    os.system(f"cut -d' ' -f2- < {args.output_name}.train_{net_type}.csv | tr ' ' '\n' | cut -d',' -f1,3 | tr ',' '\n' | "
              "awk '{n[$0]++} END {for (i in n) print i,n[i]}' > " + f"{word_histogram_path}")
    # Generate path - frequency file to future parsing in parse_vocab.
    # Splits csv file by space remove tokens and generate frequency for each line.
    # csv is split instead of .code2vec/var because we don't want redundant paths from not filtered functions to be included.
    os.system(f"cut -d' ' -f2- < {args.output_name}.train_{net_type}.csv | tr ' ' '\n' | cut -d',' -f2 | "
              "awk '{n[$0]++} END {for (i in n) print i,n[i]}' > " + f"{path_histogram_path}")
    path_freq = parse_vocab(path_histogram_path)
    word_freq = parse_vocab(word_histogram_path)

    save_dictionaries(target_freq_train=target_freq_train, target_freq_test=target_freq_test,
                      target_freq_val=target_freq_val, path_freq=path_freq,
                      word_freq=word_freq,
                      output_filename=f"{args.output_name}.{net_type}")


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--train_data_vec", dest="train_data_path_vec",
                        required=False)
    parser.add_argument("--test_data_vec", dest="test_data_path_vec",
                        required=False)
    parser.add_argument("--val_data_vec", dest="val_data_path_vec",
                        required=False)
    parser.add_argument("--train_data_var", dest="train_data_path_var",
                        required=False)
    parser.add_argument("--test_data_var", dest="test_data_path_var",
                        required=False)
    parser.add_argument("--val_data_var", dest="val_data_path_var",
                        required=False)
    parser.add_argument("--max_contexts", dest="max_contexts", type=int,
                        default=300)
    parser.add_argument("--word_histogram_vec", dest="word_histogram_vec",
                        metavar="FILE")
    parser.add_argument("--path_histogram_vec", dest="path_histogram_vec",
                        metavar="FILE")
    parser.add_argument("--target_histogram_train", dest="target_histogram_train_vec",
                        metavar="FILE")
    parser.add_argument("--target_histogram_test", dest="target_histogram_test_vec",
                        metavar="FILE")
    parser.add_argument("--target_histogram_val", dest="target_histogram_val_vec",
                        metavar="FILE")
    parser.add_argument("--word_histogram_var", dest="word_histogram_var",
                        metavar="FILE")
    parser.add_argument("--path_histogram_var", dest="path_histogram_var",
                        metavar="FILE")
    parser.add_argument("--target_histogram_train_var", dest="target_histogram_train_var",
                        metavar="FILE")
    parser.add_argument("--target_histogram_test_var", dest="target_histogram_test_var",
                        metavar="FILE")
    parser.add_argument("--target_histogram_val_var", dest="target_histogram_val_var",
                        metavar="FILE")
    parser.add_argument("--net", dest="net")
    parser.add_argument("--output_name", dest="output_name", metavar="FILE",
                        required=True,
                        default='data')
    parser.add_argument("--occurrences", dest="min_occurrences", type=int, default=0)
    parser.add_argument("--single_dataset", dest="single_dataset", type=bool, default=False)
    args = parser.parse_args()

    train_data_path_vec = args.train_data_path_vec
    test_data_path_vec = args.test_data_path_vec
    val_data_path_vec = args.val_data_path_vec
    train_data_path_var = args.train_data_path_var
    test_data_path_var = args.test_data_path_var
    val_data_path_var = args.val_data_path_var

    if not args.single_dataset:
        if args.net == "code2vec":
            process_net(args.target_histogram_train_vec,
                        args.target_histogram_test_vec,
                        args.target_histogram_val_vec,
                        args.word_histogram_vec,
                        args.path_histogram_vec,
                        [test_data_path_vec, val_data_path_vec, train_data_path_vec],
                        ['test_vec', 'val_vec', 'train_vec'],
                        net_type="vec")

        if args.net == "code2var":
            process_net(args.target_histogram_train_var,
                        args.target_histogram_test_var,
                        args.target_histogram_val_var,
                        args.word_histogram_var,
                        args.path_histogram_var,
                        [test_data_path_var, val_data_path_var, train_data_path_var],
                        ['test_var', 'val_var', 'train_var'],
                        net_type="var")
    else:
        if args.net == "code2var":
            process_file(test_data_path_var, args.max_contexts, args.output_name)
