#!/bin/bash

NAME=scale_publisher

rm -f *.dot *.txt *.bc
rm -f $NAME.cpp.o.svf.ll

source ../../../SVF/setup.sh >/dev/null
ddfg $NAME.cpp.o.ll
opt -S $NAME.cpp.o.svf.bc -o $NAME.cpp.o.svf.ll
