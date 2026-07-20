"""Inference-safe utils package exports.

Training / viz symbols stay out of eager imports so enhancer inference
does not pull deepspeed or matplotlib on tiny hosts.
"""


def __getattr__(name: str):
    if name == "global_leader_only":
        from .distributed import global_leader_only

        return global_leader_only
    if name == "setup_logging":
        from .logging import setup_logging

        return setup_logging
    if name in ("save_mels", "tree_map"):
        from .utils import save_mels, tree_map

        return save_mels if name == "save_mels" else tree_map
    if name == "Engine":
        from .engine import Engine

        return Engine
    if name == "gather_attribute":
        from .engine import gather_attribute

        return gather_attribute
    if name == "TrainLoop":
        from .train_loop import TrainLoop

        return TrainLoop
    if name == "is_global_leader":
        from .train_loop import is_global_leader

        return is_global_leader
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
