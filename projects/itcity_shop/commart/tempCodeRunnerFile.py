    try:
                getattr(self, attr).set(input[key])
            except KeyError:
                getattr(self, attr).set("-")
