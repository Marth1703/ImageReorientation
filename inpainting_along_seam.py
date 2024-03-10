from PIL import Image
import numba as nb
import numpy as np
import cv2
from scipy.ndimage import sobel

def _rgb2gray(rgb: np.ndarray) -> np.ndarray:
    coeffs = np.array([0.2125, 0.7154, 0.0721], dtype=np.float32)
    return (rgb @ coeffs).astype(rgb.dtype)

def _get_energy(gray: np.ndarray) -> np.ndarray:
    assert gray.ndim == 2
    gray = gray.astype(np.float32)
    grad_x = sobel(gray, axis=1)
    grad_y = sobel(gray, axis=0)
    energy = np.abs(grad_x) + np.abs(grad_y)
    return energy

@nb.njit(nb.int32[:](nb.float32[:, :]), cache=True)
def _get_backward_seam(energy: np.ndarray) -> np.ndarray:
    h, w = energy.shape
    inf = np.array([np.inf], dtype=np.float32)
    cost = np.concatenate((inf, energy[0], inf))
    parent = np.empty((h, w), dtype=np.int32)
    base_idx = np.arange(-1, w - 1, dtype=np.int32)

    for r in range(1, h):
        choices = np.vstack((cost[:-2], cost[1:-1], cost[2:]))
        min_idx = np.argmin(choices, axis=0) + base_idx
        parent[r] = min_idx
        cost[1:-1] = cost[1:-1][min_idx] + energy[r]

    c = np.argmin(cost[1:-1])
    seam = np.empty(h, dtype=np.int32)
    for r in range(h - 1, -1, -1):
        seam[r] = c
        c = parent[r, c]

    return seam

def get_single_seam_mask(src: np.ndarray, expand_height: bool):
    gray = src if src.ndim == 2 else _rgb2gray(src)
    height, width = src.shape[:2]
    if expand_height:
        gray = np.rot90(gray, k=1)
    energy = _get_energy(gray)
    seam = _get_backward_seam(energy)
    
    first_half_image = np.copy(src[:seam.max(), :, :])
    second_half_image = np.copy(src[seam.min():, :, :])
    
    if not expand_height:
        width, height = gray.shape[:2]
        first_half_image = np.copy(np.rot90(src, k=1)[:seam.max(), :, :])
        second_half_image = np.copy(np.rot90(src, k=1)[seam.min():, :, :])

    # extra_mask = np.zeros((height, width), dtype=bool)

    first_half_mask = np.zeros((seam.max(), width), dtype=bool)

    height_second_half = height - seam.min()
    second_half_mask = np.zeros((height_second_half, width), dtype=bool)
    
    additional_padding = 8;
    for c, r in enumerate(seam):
        # extra_mask[r, c] = True
        first_half_mask[r:, c] = True
        second_half_mask[:(r - seam.min()), c] = True
        
        if (r > additional_padding):
            first_half_mask[(r - additional_padding):, c] = True
        elif (r <= additional_padding):
            first_half_mask[0:, c] = True
        if ((r - seam.min()) >= second_half_image.shape[0] - additional_padding):
            second_half_mask[(r - seam.min()):, c] = True
        elif ((r - seam.min()) < second_half_image.shape[0] - additional_padding):
            second_half_mask[:(r - seam.min() + additional_padding), c] = True    
        
        first_half_image[r:, c] = [0, 0, 0]
        second_half_image[:(r - seam.min()), c] = [0, 0, 0]

    full_image_mask = np.vstack((first_half_mask, second_half_mask))
    full_image_array = np.vstack((first_half_image, second_half_image))
    if not expand_height:
        full_image_mask = np.rot90(full_image_mask, k=3)
        full_image_array = np.rot90(full_image_array, k=3)
    full_image_array = cv2.cvtColor(full_image_array, cv2.COLOR_RGB2BGR)
    
    # extra_seam_mask = Image.fromarray(extra_mask).convert("L")
    # extra_seam_mask = extra_seam_mask.rotate(90, expand=True)
    # extra_seam_mask.show()

    display_seam_mask = Image.fromarray(full_image_mask).convert("L")
    if not expand_height:
        display_seam_mask = display_seam_mask.rotate(90, expand=True)
    
    return [full_image_array, display_seam_mask]
    
    