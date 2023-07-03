#!/bin/bash

clang -O0 -S -c -emit-llvm -fno-discard-value-names -Xclang -disable-O0-optnone -o example1.ll example1.c
opt -S -mem2reg example1.ll -o example1.ll

rm -f *.dot *.txt
source ~/SVF/setup.sh >/dev/null

# wpa -nander -dump-pag -stat=false example1.ll
# wpa -ander -svfg -dump-vfg -stat=false -write-svfg=svf.txt example1.ll
# saber -ander -dump-slice example1.ll > /dev/null

ddfg -write-svfg svfg.txt example1.ll