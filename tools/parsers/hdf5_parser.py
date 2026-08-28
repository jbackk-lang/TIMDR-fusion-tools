import h5py
import numpy as np

def load_hdf5(path):
    with h5py.File(path, "r") as f:
        data = {}
        def walk(name, obj):
            if isinstance(obj, h5py.Dataset):
                data[name] = np.array(obj)
        f.visititems(walk)
    return data
