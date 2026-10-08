"""Owned diagnostic codes; never retain an external exception or submitted value."""


class PreflightError(ValueError):
    def __init__(self, phase, code, field=None):
        self.phase = phase
        self.code = code
        self.field = field
        super().__init__(f"{phase}: {code}" + (f" ({field})" if field else ""))
