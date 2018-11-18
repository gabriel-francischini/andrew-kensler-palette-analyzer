from ciede2000 import ciede2000
from ciede2000 import rgb2lab
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree
import functools


def read_gimp_palette(filename = "wolfpower.gpl"):
    data = []
    with open(filename, 'r') as datafile:
        firstline = datafile.readline()
        if firstline.strip() != "GIMP Palette":
            raise TypeError("It's not a GIMP Palette file")
        secondline = datafile.readline()
        for line in datafile:
            items = [x.strip() for x in line.split() if len(x.strip()) > 0]
            rgb = tuple([int(x) for x in items if x.isdigit()])
            if rgb != (0, 0, 0): # Skip placeholder colors
                data.append(rgb)
    data = set(data)
    data = sorted(list(data))
    return data

def ciede2000_from_rgb(rgb_A, rgb_B):
    return ciede2000(rgb2lab(rgb_A), rgb2lab(rgb_B))

def ciede2000_matrix_from_rgb(rgb_list):
    # Creates a NxN matrix of CIEDE2000 differences
    matrix = []
    for color in rgb_list:
        matrix.append(list(map(functools.partial(ciede2000_from_rgb, color),
                               rgb_list)))
    return matrix

def calculate_threshold(rgb_list):
    matrix = csr_matrix(ciede2000_matrix_from_rgb(rgb_list))
    tcsr = minimum_spanning_tree(matrix)
    return functools.reduce(max, [max(i) for i in tcsr.toarray().astype(float)])

colors = tuple(read_gimp_palette())
threshold = calculate_threshold(colors)
