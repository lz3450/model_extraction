#!/bin/bash

clang -O0 -S -c -emit-llvm -fno-discard-value-names -Xclang -disable-O0-optnone -o example0.ll example0.c
opt -S -mem2reg example0.ll -o example0.ll

rm -f *.dot *.txt
source ~/SVF/setup.sh >/dev/null
# wpa -nander -dump-pag -stat=false example0.ll
# wpa -ander -svfg -dump-vfg -stat=false -write-svfg=svf.txt example0.ll
# saber -ander -dump-slice example0.ll > /dev/null
ddfg -write-svfg=svfg.txt example0.ll
