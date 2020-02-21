from ciede2000 import ciede2000
from ciede2000 import rgb2lab
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree
import functools
from graphviz import Graph
import colorsys
import math
import os


def rgb2hex(r, g, b):
    def clamp(x):
        return max(0, min(x, 255))
    return "#{0:02x}{1:02x}{2:02x}".format(clamp(r), clamp(g), clamp(b))

def inverse_rgb(rgb):
    inverse = (255 - rgb[0], 255 - rgb[1], 255 - rgb[2])
    return inverse

def average_rgb(rgb_A, rgb_B):
    rint = lambda x: int(round(x))
    diff = lambda x, y: rint(math.fabs(x-y)/2)
    diff_pos = lambda x: diff(rgb_A[x], rgb_B[x])
    return tuple([diff_pos(x) for x in [0, 1, 2]])


def round_by_step(value, step):
    return round(float(value) / step) * step

def rgb2gray_rgb(rgb):
    #l = 0.21 * rgb[0] + 0.72 * rgb[1] + 0.07 * rgb[2]
    l = sum(rgb)/3
    l = int(round_by_step(l, 250))
    if l < 0:
        l = 0
    if l > 255:
        l = 255
    return (l, l, l)

def rgb_to_hsv(r, g, b):
    R, G, B = colorsys.rgb_to_hsv(r, g, b)
    B = B/100
    return (R, G, B)

def read_gimp_palette(filename):
    data = []
    with open(filename, 'r') as datafile:
        firstline = datafile.readline()
        if firstline.strip() != "GIMP Palette":
            raise TypeError("It's not a GIMP Palette file")
        for line in datafile:
            if line.startswith('#'):
                continue
            if len(line.strip()) < 3:
                continue
            items = [x.strip() for x in line.split() if len(x.strip()) > 0]
            rgb = tuple([int(x) for x in items[:3] if x.isdigit()])
            if len(rgb) > 3:
                rgb = rgb[:3]
            if len(rgb) == 0:
                continue
            if len(rgb) < 3:
                # print(line)
                # print(items)
                # print(rgb)
                print(line)
                print(items)
                print(rgb)
                raise KeyError("Can't parse line")
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

def mst_matrix_from_matrix(matrix):
    # Minimum Spanning Tree
    matrix = csr_matrix(matrix)
    tcsr = minimum_spanning_tree(matrix)
    return [[y for y in x] for x in tcsr.toarray().astype(float)]

def calculate_threshold(rgb_list, matrix_function=ciede2000_matrix_from_rgb):
    tcsr = mst_matrix_from_matrix(matrix_function(rgb_list))
    return functools.reduce(max, [max(i) for i in tcsr])


def view_graph(rgb_list, matrix_function=ciede2000_matrix_from_rgb,
               filename='CIEDE2000', verbose=False, render=True,
               threshold_calculator=calculate_threshold, colorize=lambda x: x):
    matrix = matrix_function(rgb_list)
    threshold = calculate_threshold(rgb_list, matrix_function)
    graph = Graph('G', filename=filename+'.gv', format='png')
    graph.attr(label=r'\n\n'+filename)
    graph.attr(fontsize='20')

    nodes = {}
    for i in range(len(rgb_list)):
        nodes[i] = rgb2hex(*rgb_list[i]).upper()
        graph.node(nodes[i],
                   shape='circle',
                   style='filled',
                   color=rgb2hex(*rgb_list[i]),
                   fontcolor=rgb2hex(*rgb2gray_rgb(inverse_rgb(rgb_list[i]))))

    def replace_color(color):
        if color <= threshold:
            return int(round(color))
        else:
            return 0
    filtered_matrix = [list(map(replace_color, x)) for x in matrix]

    edges = set()
    for i in range(len(rgb_list)):
        for j in range(len(rgb_list)):
            if filtered_matrix[i][j] != 0:
                edges.add(tuple(sorted((i, j))))

    connections_histogram = {}
    for i, j in edges:
        graph.edge(nodes[i], nodes[j], label=str(filtered_matrix[i][j]))
        for i in [i, j]:
            connections_histogram[i] = connections_histogram.get(i, 0) + 1

    max_edges = max(list(connections_histogram.values()))
    max_digits = int(len(str(max_edges)))
    if verbose:
        for i, j in list(edges):
            edges.add((j, i))
        for i, j in list(sorted(edges,
                                key=lambda x: (connections_histogram[x[0]], x))):
            print(("{} ({: >" + str(max_digits) + "} con.)" " -- {: >3} --"
                   "{} ({: >" + str(max_digits) + "} con.)")
                  .format(nodes[i], connections_histogram[i],
                          int(round(filtered_matrix[i][j])),
                          nodes[j], connections_histogram[j]))
    graph.view()


from os import listdir
from os.path import isfile, join
files = [f for f in listdir("./") if isfile(join("./", f))]
for filepath in files:
    if not filepath.endswith('.gpl'):
        continue
    filename = filepath.replace('.gpl', '')
    print('Processing "{}"...'.format(filename))
    colors = tuple(read_gimp_palette(filepath))
    threshold = max(calculate_threshold(colors), 20)
    filtered_matrix = view_graph(colors, verbose=False, render=False)
    mst = mst_matrix_from_matrix(filtered_matrix)
    view_graph(colors, matrix_function=lambda x: mst, verbose=False,
               filename='{}-ramp'.format(filename),
               render=True, threshold_calculator=lambda x,y: threshold)
    view_graph(colors, filename='{}-diagram'.format(filename),
               verbose=False,
               render=True, threshold_calculator=lambda x,y: threshold)

    # def only_luminance(rgb):
    #     h, s, v = colorsys.rgb_to_hsv(*rgb)
    #     return colorsys.hsv_to_rgb(h, 0, v)

    # view_graph(colors, filename='{}-value-diagram'.format(filename),
    #            verbose=False,
    #            render=True, threshold_calculator=lambda x,y: threshold,
    #            colorize=only_luminance)

# thresholds = set()
# for i in filtered_matrix:
#     list(map(thresholds.add, i))
# thresholds = [i for i in thresholds if i > 0]
# thresholds.sort()

# for i in range(len(thresholds)):
#     view_graph(colors,
#                filename=('CIEDE2000-{:0>'
#                          + str(len(str(len(thresholds))))
#                          + '}').format(i),
#                render=True, threshold_calculator=lambda x, y: thresholds[i])

print("Done.")
