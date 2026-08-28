from MDSplus import Connection
import numpy as np

def load_mdsplus(server, tree, shot, signal):
    """
    Pobiera sygnał z serwera MDSplus.
    """
    conn = Connection(server)
    conn.openTree(tree, shot)
    data = conn.get(signal).data()
    time = conn.get(f"dim_of({signal})").data()
    return np.array(time), np.array(data)
