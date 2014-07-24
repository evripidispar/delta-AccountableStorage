#!/bin/bash
python -m cProfile -o run1.prof  driver.py -b blocks/blk_100000_blocks_2048_sizeBytes.dat -g generator.txt -k 4 -n 1024 -w 8 --task 17 -r runs/100000____2048.txt -l 11;
python -m cProfile -o run2.prof driver.py -b blocks/blk_100000_blocks_2048_sizeBytes.dat -g generator.txt -k 4 -n 1024 -w 8 --task 17 -r runs/100000____2048.txt -l 11;
python -m cProfile -o run3.prof driver.py -b blocks/blk_100000_blocks_2048_sizeBytes.dat -g generator.txt -k 4 -n 1024 -w 8 --task 17 -r runs/100000____2048.txt -l 11;
