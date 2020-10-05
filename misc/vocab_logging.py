from config import config
from misc.logging import string_logger, lambda_logger

# TODO(Mocurin): Add docstrings

_verbose = False
_timefmt = '%H:%M:%S:'


def enable_logging():
    global _verbose
    _verbose = True


def change_timefmt(timefmt):
    global _timefmt
    _timefmt = timefmt


# TODO(Mocurin): Decide on whether lambda or true function definition are better
# Method name to respective logging decorator mapper
_methods = {'create_from_freq_dict':
                lambda_logger(lambda *args, **kwargs: f"Creating vocab from frequency dictionary of "
                                                      f"{min(len(args[1]), config.MAX_NUMBER_OF_WORDS_IN_FREQ_DICT)}"
                                                      f" elements",
                              None,
                              _timefmt, _verbose),
            'load_from_file':
                lambda_logger(lambda *args, **kwargs: f"Loading from file...",
                              lambda *args, **kwargs: f"Loaded vocabulary of {len(kwargs['res'].word_to_index)}"
                                                      f" elements",
                              _timefmt, _verbose),
            'save':
                lambda_logger(lambda *args, **kwargs: f"Saving Code2VecVocabs to {args[1]}"
                                                      if args[1] not in args[0].already_saved_paths else None,
                              None,
                              _timefmt, _verbose),
            '_load':
                lambda_logger(lambda *args, **kwargs: f"Loading Code2VecVocabs from {args[1]}",
                              None,
                              _timefmt, _verbose),
            'save_to_file':
                string_logger(f"Saving vocabulary to file...",
                              f"Vocabulary successfully saved",
                              _timefmt, _verbose),
            '_load_freq_dicts':
                string_logger(f"Loading frequency dicts from {config.TRAINING_FREQ_DICTS_PATH}",
                              None,
                              _timefmt, _verbose),
            '_create':
                string_logger(f"Creating vocab from {config.TRAINING_FREQ_DICTS_PATH}",
                              f"Created all vocabularies",
                              _timefmt, _verbose),
            }


# Essentially decorator factory
def logged_vocab_method(method_name):
    return _methods[method_name]
