import pytest

from app.pipeline.cleaning.base import BaseCleaner

def test_base_cleaner_is_abstract():
    with pytest.raises(TypeError):
        BaseCleaner()