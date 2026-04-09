from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image

# scipy makes the "fill invalid pixels from nearest valid neighbors" step easy.
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree # pyright: ignore[reportAttributeAccessIssue]

from math import ceil

@dataclass
class TopoMap:
    image_path: str

    # These bounds are tuned to this specific image.
    # Format: (left, top, right, bottom), with right/bottom exclusive.
    plot_bounds: tuple[int, int, int, int] = (120, 38, 1218, 998)
    colorbar_bounds: tuple[int, int, int, int] = (1241, 37, 1272, 998)

    # World-coordinate bounds shown on the axes.
    x_range: tuple[float, float] = (-20.0, 100.0)
    y_range: tuple[float, float] = (-20.0, 100.0)

    # From the visible colorbar, the actual scale appears to be about -5 to 30.
    # The user mentioned -5 to 35, so we clamp to that wider range on output.
    z_range_visible: tuple[float, float] = (-5.0, 30.0)
    z_range_output: tuple[float, float] = (-5.0, 35.0)

    def __post_init__(self) -> None:
        img = Image.open(self.image_path).convert("RGB")
        self._img = np.asarray(img, dtype=np.uint8)

        l, t, r, b = self.plot_bounds
        self._plot_rgb = self._img[t:b, l:r].copy()
        self._h, self._w = self._plot_rgb.shape[:2]

        self._build_colorbar_model()
        self._build_height_grid()

    def _build_colorbar_model(self) -> None:
        l, t, r, b = self.colorbar_bounds
        cb = self._img[t:b, l:r].astype(np.float32)

        # Ignore the black outline of the colorbar by sampling the middle columns.
        inner = cb[:, max(2, cb.shape[1] // 4): min(cb.shape[1] - 2, 3 * cb.shape[1] // 4)]
        cb_rgb = inner.mean(axis=1)  # one RGB triplet per row

        # Top of colorbar = max height, bottom = min height.
        zmin, zmax = self.z_range_visible
        cb_z = np.linspace(zmax, zmin, cb_rgb.shape[0], dtype=np.float32)

        # JPEG introduces duplicate-ish colors; keep all rows and use nearest-neighbor in RGB space.
        self._cb_tree = cKDTree(cb_rgb)
        self._cb_z = cb_z

    def _rgb_to_height(self, rgb: np.ndarray) -> np.ndarray:
        """
        rgb: (..., 3) float32 or uint8 array
        returns: (...) float32 heights
        """
        flat = rgb.reshape(-1, 3).astype(np.float32)
        _, idx = self._cb_tree.query(flat, k=1)
        z = self._cb_z[idx]
        return z.reshape(rgb.shape[:-1])

    def _build_height_grid(self) -> None:
        rgb = self._plot_rgb.astype(np.float32)

        R = rgb[..., 0]
        G = rgb[..., 1]
        B = rgb[..., 2]

        # Map every pixel color to a height estimate.
        z = self._rgb_to_height(rgb)

        # Invalid pixels:
        # - black contour lines / black text
        # - axes lines / tick marks
        # - very bright annotation artifacts
        dark_mask = (R < 50) & (G < 50) & (B < 50)
        near_white_mask = (R > 235) & (G > 235) & (B > 235)

        invalid = dark_mask | near_white_mask

        # Detect red "house" region and force it to zero.
        red_mask = (R > 160) & (G < 90) & (B < 90)
        if np.any(red_mask):
            ys, xs = np.where(red_mask)
            x0, x1 = xs.min(), xs.max()
            y0, y1 = ys.min(), ys.max()

            # Expand a bit so the outlined border / white circle also get absorbed.
            pad = 12
            x0 = max(0, x0 - pad)
            x1 = min(self._w - 1, x1 + pad)
            y0 = max(0, y0 - pad)
            y1 = min(self._h - 1, y1 + pad)

            house_mask = np.zeros((self._h, self._w), dtype=bool)
            house_mask[y0:y1 + 1, x0:x1 + 1] = True
            z[house_mask] = 0.0
            invalid[house_mask] = False  # keep these as valid zero values

        # Fill invalid pixels from nearest valid neighbor.
        valid = ~invalid
        if not np.any(valid):
            raise RuntimeError("No valid map pixels found.")

        z_filled = z.copy()
        z_filled[invalid] = np.nan

        # distance_transform_edt with return_indices=True gives nearest valid pixel index.
        nearest_valid_idx = distance_transform_edt(~valid, return_distances=False, return_indices=True)
        z_filled[invalid] = z_filled[tuple(nearest_valid_idx[:, invalid])] # pyright: ignore[reportOptionalSubscript, reportArgumentType, reportCallIssue]

        self._zgrid = np.clip(z_filled.astype(np.float32), *self.z_range_output)

    def height(self, x: float, y: float) -> float:
        """
        Bilinearly interpolated height at world coordinate (x, y).
        """
        xmin, xmax = self.x_range
        ymin, ymax = self.y_range

        if not (xmin <= x <= xmax and ymin <= y <= ymax):
            raise ValueError(
                f"(x, y)=({x}, {y}) is out of bounds. "
                f"Expected {xmin} <= x <= {xmax} and {ymin} <= y <= {ymax}."
            )

        # Convert world coordinates to image-grid coordinates.
        # x increases to the right
        # y increases upward, but image rows increase downward
        px = (x - xmin) / (xmax - xmin) * (self._w - 1)
        py = (ymax - y) / (ymax - ymin) * (self._h - 1)

        x0 = int(np.floor(px))
        y0 = int(np.floor(py))
        x1 = min(x0 + 1, self._w - 1)
        y1 = min(y0 + 1, self._h - 1)

        dx = px - x0
        dy = py - y0

        z00 = self._zgrid[y0, x0]
        z10 = self._zgrid[y0, x1]
        z01 = self._zgrid[y1, x0]
        z11 = self._zgrid[y1, x1]

        z0 = z00 * (1.0 - dx) + z10 * dx
        z1 = z01 * (1.0 - dx) + z11 * dx
        z = z0 * (1.0 - dy) + z1 * dy

        return float(np.clip(z, *self.z_range_output))

    def height_array(self) -> np.ndarray:
        """
        Returns the cached 2D height grid for the whole map crop.
        Shape is (plot_height_px, plot_width_px).
        """
        return self._zgrid.copy()


@lru_cache(maxsize=1)
def load_topo_map(image_path: str = "HOUSE_TOPOLOGY.jpg") -> TopoMap:
    """
    Load and cache the topo map exactly once.
    """
    return TopoMap(image_path=image_path)


def get_height(x: float, y: float, image_path: str = "HOUSE_TOPOLOGY.jpg") -> int:
    """
    Convenience function: cached one-time load, then fast lookup.
    """
    topo = load_topo_map(image_path)
    return ceil(topo.height(x, y) + 0.6)  # round up to nearest integer, with a small fudge factor to ensure we err on the side of safety

def get_pipe_length(x: float, y: float, z_offset: float = 0.0, image_path: str = "HOUSE_TOPOLOGY.jpg") -> float:
    """
    Convenience function to get the pipe length from (x, y) to the house at (0, 0).
    Uses the cached topo map for height lookup.
    """
    topo = load_topo_map(image_path)
    z = topo.height(x, y)
    horizontal_dist = (x**2 + y**2)**0.5
    total_length = (horizontal_dist**2 + (z + z_offset)**2)**0.5
    return float(total_length)

TOPOLOGY_IMG_PATH = "HOUSE_TOPOLOGY.jpg"

if __name__ == "__main__":
    # Test some points and print their heights.
    print(get_height(-10,17))
    print(get_height(30, 80))
    print(get_height(20, 0))
    print(get_height(80, 80))
    print(get_height(40, 60))
    print(get_pipe_length(20, 0))
    print(get_pipe_length(80, 80))
    print(get_pipe_length(40, 60))