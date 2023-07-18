#!/bin/bash

rm -f *.dot *.txt *.bc
rm -f turtle_tf2_listener.cpp.o.svf.ll

source ~/SVF/setup.sh >/dev/null
ddfg turtle_tf2_listener.cpp.o.ll
opt -S turtle_tf2_listener.cpp.o.svf.bc -o turtle_tf2_listener.cpp.o.svf.ll
