import os
import shutil
import argparse
import xml.etree.ElementTree as ET


def collect_compile_commands(pkg_dir, search_dirs, output_directory):
    # Parse the package.xml file
    tree = ET.parse(os.path.join(pkg_dir, 'package.xml'))
    root = tree.getroot()

    # 
    package = root.find('name').text
    print("Package Name:", package)
    # Extract the names of the dependencies
    dependencies = [dep.text for dep in root.findall('depend')]

    all_packages = [package]
    all_packages.extend(dependencies)
    print("All Packages:", ', '.join(all_packages))

    # Collect compile_commands.json files from the package directory and its dependencies
    for search_dir in search_dirs:
        for root, dirs, files in os.walk(search_dir):
            if os.path.basename(root) in all_packages:
                if 'compile_commands.json' in files:
                    relative_root = os.path.relpath(root, search_dir)
                    new_dir = os.path.join(output_directory, relative_root)
                    os.makedirs(new_dir, exist_ok=True)
                    shutil.copy(os.path.join(root, 'compile_commands.json'),
                                os.path.join(new_dir, 'compile_commands.json'))

    print('Done collecting compile_commands.json files.')


def main():
    parser = argparse.ArgumentParser(description='Collect compile_commands.json files from ROS packages.')
    parser.add_argument('pkg_dir', type=str, help='Directory of the package.xml file')
    parser.add_argument('search_dirs', type=str, nargs='+', help='Directories to search for compile_commands.json')
    args = parser.parse_args()

    output_directory = 'collected_compile_commands'
    collect_compile_commands(args.pkg_dir, args.search_dirs, output_directory)


if __name__ == '__main__':
    main()
