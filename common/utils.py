import os

class Config:
    def __getattr__(self, name):
        value = os.getenv(name)
        if value is None:
            raise AttributeError(f"Config has no attribute '{name}'")
        return value