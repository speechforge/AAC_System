import math
def softnorm(sc):
    m = max(sc); e = [math.exp(x - m) for x in sc]; z = sum(e); return [x / z for x in e]
