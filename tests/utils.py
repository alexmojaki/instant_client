from contextlib import contextmanager

import pytest


@contextmanager
def raises_with_cause(original_type, cause_type, message):
    with pytest.raises(original_type) as e:
        yield
    cause = e.value.__cause__
    assert isinstance(cause, cause_type)
    assert str(cause) == message
