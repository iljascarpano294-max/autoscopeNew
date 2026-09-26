"""Dictionary with attribute-style access, following the reference shape."""


class DictMixin(dict):
    __setattr__ = dict.__setitem__

    def __getattr__(self, key: str) -> object:
        try:
            return dict.__getitem__(self, key)
        except KeyError as error:
            raise AttributeError(key) from error
