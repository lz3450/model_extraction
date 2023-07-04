import argparse
from typing import List, Set


def find_connected_nodes(nodes_to_keep: Set, dot_file: List[str]):
    # pass 2
    for i, line in enumerate(dot_file, start=1):
        print(f"\r{i} / {len(dot_file)}", end="\r")
        line_strip = line.strip()
        if '->' in line_strip:
            node1, node2 = line_strip.split(' -> ')
            node2 = node2.split('[')[0]
            nodes_to_keep.add(node1)
            nodes_to_keep.add(node2)
    print()

    return nodes_to_keep


def find_nodes_to_keep(dot_file: List[str]):
    nodes_to_keep = set()

    # pass 1: find initial nodes
    for i, line in enumerate(dot_file, start=1):
        print(f"\r[Pass 1] {i}/ {len(dot_file)}", end="\r")
        line_strip = line.strip()
        node_id = line_strip.split(' [')[0]
        if 'label' in line_strip and '%msg' in line_strip:
            nodes_to_keep.add(node_id)
    print(f"\n{len(nodes_to_keep)}")

    def find_connected_nodes(pass_num):
        # pass 2...
        for i, line in enumerate(dot_file, start=1):
            print(f"\r[Pass {pass_num}] {i} / {len(dot_file)}", end="\r")
            line_strip = line.strip()
            if '->' in line_strip:
                node1, node2 = line_strip.split(' -> ')
                node2 = node2.split('[')[0]
                if node1 in nodes_to_keep or node2 in nodes_to_keep:
                    nodes_to_keep.add(node1)
                    nodes_to_keep.add(node2)
        print(f"\n{len(nodes_to_keep)}")

    pass_num = 2
    while True:
        node_num = len(nodes_to_keep)
        find_connected_nodes(pass_num)
        if len(nodes_to_keep) <= node_num:
            break
        else:
            pass_num += 1

    return nodes_to_keep


def filter_dot_file(nodes_to_keep: Set, dot_file: List[str], output_file_path):
    with open(output_file_path, "w") as out:
        for i, line in enumerate(dot_file, start=1):
            print(f"\r{i} / {len(dot_file)}", end="\r")
            line_strip = line.strip()
            if line_strip.startswith('digraph') or line_strip.endswith('}'):
                out.write(line)
                continue
            node_id = line_strip.split(' ')[0]
            if '->' in line:
                node1, node2 = line_strip.split(' -> ')
                node2 = node2.split('[')[0]
                if node1 in nodes_to_keep or node2 in nodes_to_keep:
                    out.write(line)
            elif node_id in nodes_to_keep:
                out.write(line)
        print()


def main():
    parser = argparse.ArgumentParser(description='Process a dot file and remove nodes without certain labels.')
    parser.add_argument('dot_file_path', type=str, help='The path to the .dot file to be processed')
    parser.add_argument('output_file_path', type=str, help='The path to the output .dot file')

    args = parser.parse_args()

    with open(args.dot_file_path, "r") as f:
        dot_file = f.readlines()

    nodes_to_keep = find_nodes_to_keep(dot_file)
    filter_dot_file(nodes_to_keep, dot_file, args.output_file_path)


if __name__ == "__main__":
    main()
