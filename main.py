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

def matrix_from_rgb_comparator(rgb_list, comparator=ciede2000_from_rgb):
    matrix = []
    for color in rgb_list:
        matrix.append(list(map(functools.partial(comparator, color),
                               rgb_list)))
    return matrix

def ciede2000_matrix_from_rgb(rgb_list):
    # Creates a NxN matrix of CIEDE2000 differences
    return matrix_from_rgb_comparator(rgb_list, ciede2000_from_rgb)

def calculate_threshold(rgb_list, matrix_function=ciede2000_matrix_from_rgb):
    matrix = csr_matrix(matrix_function(rgb_list))
    tcsr = minimum_spanning_tree(matrix)
    return functools.reduce(max, [max(i) for i in tcsr.toarray().astype(float)])

colors = tuple(read_gimp_palette())
threshold = calculate_threshold(colors)
