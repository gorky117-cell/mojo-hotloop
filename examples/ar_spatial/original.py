import math
from hotloop import hotloop

@hotloop
def find_closest_point_to_ray(
    xs: list[float],
    ys: list[float],
    zs: list[float],
    ray_ox: float,
    ray_oy: float,
    ray_oz: float,
    ray_dx: float,
    ray_dy: float,
    ray_dz: float,
) -> int:
    n: int = len(xs)
    if n == 0 or len(ys) != n or len(zs) != n:
        return -1

    dir_len_sq: float = ray_dx * ray_dx + ray_dy * ray_dy + ray_dz * ray_dz
    if dir_len_sq <= 0.0:
        return -1

    inv_len: float = 1.0 / math.sqrt(dir_len_sq)
    dx: float = ray_dx * inv_len
    dy: float = ray_dy * inv_len
    dz: float = ray_dz * inv_len

    best_idx: int = -1
    min_dist_sq: float = 1e30

    for i in range(n):
        vx: float = xs[i] - ray_ox
        vy: float = ys[i] - ray_oy
        vz: float = zs[i] - ray_oz

        # Projection along ray
        t: float = vx * dx + vy * dy + vz * dz
        if t < 0.0:
            t = 0.0

        wx: float = vx - t * dx
        wy: float = vy - t * dy
        wz: float = vz - t * dz

        dist_sq: float = wx * wx + wy * wy + wz * wz
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            best_idx = i

    return best_idx
