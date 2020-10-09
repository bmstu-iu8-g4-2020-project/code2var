from typing import Callable, Optional

import time


# TODO(Mocurin): Add docstrings
def lambda_logger(f1: Optional[Callable] = None,
                  f2: Optional[Callable] = None,
                  timefmt='%H:%M:%S:', verbose=True):
    def logging_decorator(function):
        if not verbose: return function

        def executor(*args, **kwargs):
            s1 = f1(*args, **kwargs) if f1 else None
            if s1: print(' '.join([time.strftime(timefmt), str(s1)]))
            res = function(*args, **kwargs)
            s2 = f2(*args, res=res, **kwargs) if f2 else None
            if s2: print(' '.join([time.strftime(timefmt), str(s2)]))
            return res

        return executor

    return logging_decorator


def string_logger(s1: Optional[str] = None,
                  s2: Optional[str] = None,
                  *args, **kwargs):
    return lambda_logger(lambda *_, **__: s1 if s1 else None,
                         lambda *_, **__: s2 if s2 else None,
                         *args, **kwargs)
