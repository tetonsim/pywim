import os
import stl

def load_from_file(name : str) -> stl.Mesh:
    this_dir = os.path.abspath(os.path.dirname(__file__))
    stl_file = os.path.join(this_dir, name)
    mesh = stl.Mesh.from_file(stl_file)
    return mesh
