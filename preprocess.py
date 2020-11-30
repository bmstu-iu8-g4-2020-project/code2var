#!/usr/bin/python
import fnmatch
import os
import pickle
import random
from enum import Enum

import pandas as pd

import config

from argparse import ArgumentParser
from collections import namedtuple
from typing import Optional, List, Callable

FreqDictLine = namedtuple("FreqDictLine", ["name", "frequency"])


class NetType(Enum):
    code2var = "var"
    code2vec = "vec"


def parse_vocab(path: str,
                limit: Optional[int] = None,
                filters: Optional[List[Callable]] = None):
    """
        Parse histogram files containing target|token|path aёёnd their frequency pairs.
        Creates word to frequency dicts for future uploading to the Vocab.

        Note that parsed file for token and path should be generated from functions with pre-limited targets to avoid
        redundant data in token and path freq_dicts.
    Args:
        path (): string contains path to file with parsed pairs "word frequency"
        limit (): optional hyper-parameter that should protect freq_dicts from being too big if minimal frequency is too low.
        filters (): functions used to filter inappropriate targets
    Raises:
        ValueError if file opened from path is empty or doesn't content any matching required pair line.
    Returns:
        dict containing words in keys and their frequencies in values.
    """
    if filters is None:
        # Move out of function as _default_filters = [...]
        # when "args" variable scope issues are addressed
        filters = [
            lambda line: line.frequency > 50,
        ]

    with open(path, "r") as file:
        word_to_freq = (line.rstrip("\n").split(" ") for line in file)
        word_to_freq = (FreqDictLine(line[0], int(line[1])) for line in word_to_freq if len(line) == 2)
        word_to_freq = filter(lambda line: all(f(line) for f in filters), word_to_freq)
        word_to_freq = sorted(word_to_freq, key=lambda line: line.frequency)
        word_to_freq = dict(word_to_freq[:limit])
    if len(word_to_freq) != 0:
        return word_to_freq
    raise ValueError(f"Empty or incorrect file given. Path: {path}")


def save_dictionaries(path_freq, target_freq_train, word_freq, output_filename):
    """
        Dumps generated word to frequency dictionaries to .c2v.dict file using pickle
    """
    output_file_path = output_filename + ".c2v.dict"
    with open(output_file_path, "wb") as file:
        pickle.dump(word_freq, file)
        pickle.dump(path_freq, file)
        pickle.dump(target_freq_train, file)
        print(f"Frequency dictionaries saved to: {output_filename}.c2v.dict")


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
            for idx, line in enumerate(file):
                contexts = line.rstrip('\n').split(" ")
                if len(contexts) == 0:
                    raise RuntimeError(f"One of lines in your file has wrong size. Line {idx}: {line}")
                target, contexts = contexts[0], contexts[1:]
                if target in target_freq:
                    if len(contexts) > max_contexts:
                        contexts = random.sample(contexts, max_contexts)
                    empty_filler = " " * (max_contexts - len(contexts))
                    output.write(f"{target} {' '.join(contexts)}{empty_filler}\n")
    print(f"processed {file_path}")
    print(f"generated {out_file_path}.csv")


def _find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result


def create_target_vocab(data_files: List[str], output_name: str, net_type: NetType):
    df = []
    for file_path in data_files:
        df.append(pd.read_csv(file_path, sep=" ", usecols=[0], names=["Target"], header=None))
        df[-1]["Frequency"] = 1
        df[-1] = df[-1].groupby("Target").sum().reset_index()
        df[-1]["Folders"] = 1
    vocab = pd.concat(df)
    vocab = vocab.groupby(["Target"]).sum().reset_index()
    vocab = vocab.query('Folders > 1')
    with open(output_name, "w") as file:
        for target, freq in zip(vocab["Target"], vocab["Frequency"]):
            file.write(f"{target} {freq}\n")


def process_net(data_dir_path: str, combined_data_path: str, output_name: str, net_type: NetType):
    """
        Process target files for train, test and validation datasets,
        generates token and path vocabs for training dataset.
    Args:

        data_dir_path (): path to folder where all .data.log files is stored.
        output_name (): the template filename that will be used to save the generated files.
        net_type (): vec or var.

    """
    target_filters = [
        lambda line: line.frequency > min_occurrences,
        # lambda line: "|" not in line.name,
        lambda line: len(line.name) > 2 or line.name in {"i", "j", "k", "e", "s", "o", "db", "fs", "it", "is", "in", "to"},
        lambda line: line.name not in {"element", "object", "variable", "var"},
    ]

    data_files = _find(f"*.{net_type.value}.data.log", data_dir_path)
    if len(data_files) == 0:
        raise RuntimeError(f"Given folder has no files with .{net_type.value}.data.log file extension.")

    target_vocab_path = f"{output_name}.{net_type.value}.target.vocab"
    token_vocab_path = f"{output_name}.{net_type.value}.token.vocab"
    path_vocab_path = f"{output_name}.{net_type.value}.path.vocab"
    create_target_vocab(data_files, target_vocab_path, net_type)

    target_freq = parse_vocab(target_vocab_path, filters=target_filters)

    process_file(file_path=combined_data_path,
                 max_contexts=args.max_contexts,
                 target_freq=target_freq,
                 out_file_path=f"{args.output_name}.{net_type.value}")

    # Generate token - frequency file to future parsing in parse_vocab.
    # Splits csv file by space remove path and generate frequency for each line.
    # csv is split instead of .code2vec/var because we don't want redundant tokens from not filtered functions to be included.
    os.system(f"cut -d' ' -f2- < {args.output_name}.{net_type.value}.csv | tr ' ' '\n' | cut -d',' -f1,3 | tr ',' '\n' | "
              "awk '{n[$0]++} END {for (i in n) print i,n[i]}' > " + token_vocab_path)
    # Generate path - frequency file to future parsing in parse_vocab.
    # Splits csv file by space remove tokens and generate frequency for each line.
    # csv is split instead of .code2vec/var because we don't want redundant paths from not filtered functions to be included.
    os.system(f"cut -d' ' -f2- < {args.output_name}.{net_type.value}.csv | tr ' ' '\n' | cut -d',' -f2 | "
              "awk '{n[$0]++} END {for (i in n) print i,n[i]}' > " + path_vocab_path)
    path_freq = parse_vocab(path_vocab_path, config.config.MAX_NUMBER_OF_WORDS_IN_FREQ_DICT, filters=[lambda _: True])
    word_freq = parse_vocab(token_vocab_path)

    save_dictionaries(target_freq_train=target_freq, path_freq=path_freq,
                      word_freq=word_freq,
                      output_filename=f"{args.output_name}.{net_type.value}")


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--data_dir",
                        dest="data_dir",
                        help="path to directory containing extracted path in .data.log files",
                        required=True)
    parser.add_argument("--combined_file",
                        dest="combined_file",
                        help="path to concatenation of all .data.log file",
                        required=True)
    parser.add_argument("--max_contexts",
                        dest="max_contexts",
                        type=int,
                        default=200,
                        required=False)
    parser.add_argument("--net",
                        dest="net",
                        help="var or vec for code2var or code2vec",
                        required=True)
    parser.add_argument("--occurrences",
                        dest="min_occurrences",
                        required=False,
                        type=int,
                        default=0)
    parser.add_argument("--min_folders",
                        dest="min_folders",
                        help="Minimal folders number for target to be found for passing filter.",
                        type=int,
                        default=0)
    parser.add_argument("--output_name",
                        dest="output_name",
                        metavar="FILE",
                        required=True,
                        default='data')
    args = parser.parse_args()

    net: NetType = NetType(args.net)
    min_occurrences = args.min_occurrences
    min_folders = args.min_folders

    process_net(args.data_dir, args.combined_file, args.output_name, net_type=net)
