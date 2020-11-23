#!/usr/bin/python

import itertools
import multiprocessing
import os
import shutil
import subprocess
from threading import Timer
import sys
from argparse import ArgumentParser


def get_immediate_subdirectories(a_dir):
    return ((os.path.join(a_dir, name)) for name in os.listdir(a_dir)
            if os.path.isdir(os.path.join(a_dir, name)))


TMP_DIR = ""


def ParallelExtractDir(args, dir):
    ExtractFeaturesForDir(args, dir, "")


def ExtractFeaturesForDir(args, dir, prefix):
    command = ["java", "-cp", args.jar, "JavaExtractor.App",
               "--max_path_length", str(args.max_path_length), "--max_path_width",
               str(args.max_path_width),
               "--dir", dir, "--num_threads", str(args.num_threads)]
    suffix = ".vec.data.log"
    if args.only_vars:
        command += ["--variables"]
        suffix = ".var.data.log"
    if args.obfuscate:
        command += ["--obfuscate"]

    # print command
    # os.system(" ".join(command))
    # print(" ".join(command))
    kill = lambda process: process.kill()
    outputFileName = TMP_DIR + prefix + dir.split("/")[-1]
    failed = False
    with open(outputFileName, "a") as outputFile:
        with open(prefix + dir + suffix, 'a') as o:
            print(command)
            sp = subprocess.Popen(command, stdout=o, stderr=subprocess.PIPE)

        while sp.poll() is None:  # sp.poll() returns None while subprocess is running
            print(sp.stderr.readline())

        print("Ended: ", command)


def ExtractFeaturesForDirsList(args, dirs):
    global TMP_DIR
    TMP_DIR = "./tmp/feature_extractor%d/" % (os.getpid())
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR, ignore_errors=True)
    os.makedirs(TMP_DIR)
    try:
        p = multiprocessing.Pool(1)
        p.starmap(ParallelExtractDir, zip(itertools.repeat(args), list(dirs)))
        output_files = os.listdir(TMP_DIR)
        for f in output_files:
            os.system("cat %s/%s" % (TMP_DIR, f))
    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-maxlen", "--max_path_length", dest="max_path_length",
                        required=False, default=8)
    parser.add_argument("-maxwidth", "--max_path_width", dest="max_path_width",
                        required=False, default=2)
    parser.add_argument("-threads", "--num_threads", dest="num_threads",
                        required=False, default=8)
    parser.add_argument("-j", "--jar", dest="jar", required=True)
    parser.add_argument("-d", "--dir", dest="dir", required=False)
    parser.add_argument("-file", "--file", dest="file", required=False)
    parser.add_argument("--only_for_vars", dest="only_vars", required=False,
                        default=False)
    parser.add_argument("--obfuscate", dest="obfuscate", required=False,
                        default=False)
    args = parser.parse_args()

    if args.file is not None:
        command = ["java -cp", args.jar, "JavaExtractor.App", "--max_path_length ",
                   str(args.max_path_length), "--max_path_width",
                   str(args.max_path_width),
                   "--file", args.file]
        if args.only_vars:
            command += ["--only_for_vars"]
        if args.obfuscate:
            command += ["--obfuscate"]
        os.system(" ".join(command))
    elif args.dir is not None:
        subdirs = get_immediate_subdirectories(args.dir)
        to_extract = subdirs
        if sys.getsizeof(subdirs) == 0:
            to_extract = [args.dir.rstrip("/")]
        ExtractFeaturesForDirsList(args, to_extract)
