import math
from hotloop import hotloop

@hotloop
def accumulate_haversine_distance(lats: list[float], lons: list[float]) -> float:
    n: int = len(lats)
    if n <= 1:
        return 0.0

    total_dist: float = 0.0
    r: float = 6371.0
    rad_factor: float = 3.141592653589793 / 180.0

    for i in range(1, n):
        lat1: float = lats[i - 1] * rad_factor
        lon1: float = lons[i - 1] * rad_factor
        lat2: float = lats[i] * rad_factor
        lon2: float = lons[i] * rad_factor

        dlat: float = lat2 - lat1
        dlon: float = lon2 - lon1

        half_dlat: float = dlat * 0.5
        half_dlon: float = dlon * 0.5

        sin_dlat: float = math.sin(half_dlat)
        sin_dlon: float = math.sin(half_dlon)

        a: float = sin_dlat * sin_dlat + math.cos(lat1) * math.cos(lat2) * sin_dlon * sin_dlon
        if a > 1.0:
            a = 1.0
        elif a < 0.0:
            a = 0.0

        c: float = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        total_dist = total_dist + r * c

    return total_dist
