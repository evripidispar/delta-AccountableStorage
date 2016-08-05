#!/bin/bash

python driver.py -b blocks/blk_1000_blocks_1024_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____1024.txt --dt 0 --tagmode
python driver.py -b blocks/blk_1000_blocks_2048_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____2048.txt --dt 0 --tagmode
python driver.py -b blocks/blk_1000_blocks_4096_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____4096.txt --dt 0 --tagmode
python driver.py -b blocks/blk_1000_blocks_8192_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____8192.txt --dt 0 --tagmode

sleep 10

python driver.py -b blocks/blk_10000_blocks_1024_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____1024.txt --dt 0 --tagmode
python driver.py -b blocks/blk_10000_blocks_2048_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____2048.txt --dt 0 --tagmode
python driver.py -b blocks/blk_10000_blocks_4096_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____4096.txt --dt 0 --tagmode
python driver.py -b blocks/blk_10000_blocks_8192_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____8192.txt --dt 0 --tagmode

sleep 10

python driver.py -b blocks/blk_100000_blocks_1024_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 9 -r runs/1000____1024.txt --dt 0 --tagmode
python driver.py -b blocks/blk_100000_blocks_2048_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 19 -r runs/1000____2048.txt --dt 0 --tagmode
python driver.py -b blocks/blk_100000_blocks_4096_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 39 -r runs/1000____4096.txt --dt 0 --tagmode
python driver.py -b blocks/blk_100000_blocks_8192_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 78 -r runs/1000____8192.txt --dt 0 --tagmode

sleep 10