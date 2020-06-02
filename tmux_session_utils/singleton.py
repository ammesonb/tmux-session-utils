"""
A decorator that makes a class a singleton
"""

# pylint: disable=too-few-public-methods
class Singleton:
    """
    A singleton class
    """

    instances = {}

    def __new__(cls, clz=None):
        """
        Returns a new instance ONLY if one does not already exist
        """
        if clz is None:
            if cls.__name__ not in Singleton.instances:
                Singleton.instances[cls.__name__] = object.__new__(cls)
            return Singleton.instances[cls.__name__]

        Singleton.instances[clz.__name__] = clz()
        Singleton.first = clz
        return type(clz.__name__, (Singleton,), dict(clz.__dict__))
