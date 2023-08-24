import concurrent.futures
import json
import os
import subprocess
import argparse


def generate_llvm_ir(compile_commands_file, output_directory):
    with open(compile_commands_file, 'r') as f:
        compile_commands = json.load(f)

    def run_cmd(cmd, cwd, output_log_file):
        with open(output_log_file, 'w') as f:
            subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)

    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = []
        for command in compile_commands:
            cmd = command['command'].split(' ')
            cmd: list
            if '-o' in cmd:
                output_index = cmd.index('-o') + 1
                output_file = os.path.join(output_directory, os.path.basename(cmd[output_index])) + '.ll'
                cmd[output_index] = output_file
            else:
                output_file = os.path.join(output_directory, os.path.basename(command['file'])) + '.ll'
                cmd.extend(['-o', output_file])

            # Check if the .ll file already exists
            if os.path.exists(output_file):
                print(f"Skipping {output_file}, already exists.")
                continue

            cmd.extend(['-S', '-emit-llvm', '-fno-discard-value-names'])
            # Start the process and add it to the list of futures
            output_log_file = os.path.join(output_directory, os.path.basename(command['file'])) + '.log'
            future = executor.submit(run_cmd, cmd, command['directory'], output_log_file)
            futures.append(future)

        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            future.result()

    print('Done generating LLVM IR files for', compile_commands_file)


def link_llvm_ir_files(directory, output_file):
    # Find all .ll files in the directory
    llvm_ir_files = [f for f in os.listdir(directory) if f.endswith('.ll')]

    # Prepare the command for llvm-link
    cmd = ['llvm-link', '-o', output_file] + llvm_ir_files

    # Run the command
    subprocess.run(cmd, cwd=directory, check=True)

    print(f'Linked {len(llvm_ir_files)} files into {output_file}')


def generate_llvm_ir_from_directory(directory, output_directory):
    # Create a subdirectory 'ir' in the output directory
    os.makedirs(output_directory, exist_ok=True)

    for root, dirs, files in os.walk(directory):
        if 'compile_commands.json' in files:
            generate_llvm_ir(os.path.join(root, 'compile_commands.json'), os.path.join(os.getcwd(), output_directory))

    link_llvm_ir_files(output_directory, "output.ir")

def main():
    parser = argparse.ArgumentParser(description='Generate LLVM IR files from compile_commands.json files in a directory.')
    parser.add_argument('directory', type=str, help='Directory containing compile_commands.json files')
    parser.add_argument('output_directory', type=str, help='Directory to store the generated .ll files')
    args = parser.parse_args()

    generate_llvm_ir_from_directory(args.directory, args.output_directory)


if __name__ == '__main__':
    main()
