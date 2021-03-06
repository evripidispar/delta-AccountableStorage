#!/bin/bash

python driver.py -b blocks/blk_100_blocks_1024_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/100____1024.txt --dt 0 --tagload tags/wtagskey_100_1024.dat --ibfload preproc/preproc_100_1024.data
python driver.py -b blocks/blk_100_blocks_2048_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/100____2048.txt --dt 0 --tagload tags/wtagskey_100_2048.dat --ibfload preproc/preproc_100_2048.data
python driver.py -b blocks/blk_100_blocks_4096_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/100____4096.txt --dt 0 --tagload tags/wtagskey_100_4096.dat --ibfload preproc/preproc_100_4096.data
python driver.py -b blocks/blk_100_blocks_8192_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/100____8192.txt --dt 0 --tagload tags/wtagskey_100_8192.dat --ibfload preproc/preproc_100_8192.data

sleep 10

python driver.py -b blocks/blk_1000_blocks_1024_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____1024.txt --dt 0 --tagload tags/wtagskey_1000_1024.dat --ibfload preproc/preproc_1000_1024.data
python driver.py -b blocks/blk_1000_blocks_2048_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____2048.txt --dt 0 --tagload tags/wtagskey_1000_2048.dat --ibfload preproc/preproc_1000_2048.data
python driver.py -b blocks/blk_1000_blocks_4096_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____4096.txt --dt 0 --tagload tags/wtagskey_1000_4096.dat --ibfload preproc/preproc_1000_4096.data
python driver.py -b blocks/blk_1000_blocks_8192_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/1000____8192.txt --dt 0 --tagload tags/wtagskey_1000_8192.dat --ibfload preproc/preproc_1000_8192.data

sleep 10

python driver.py -b blocks/blk_10000_blocks_1024_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/10000____1024.txt --dt 0 --tagload tags/wtagskey_10000_1024.dat --ibfload preproc/preproc_10000_1024.data
python driver.py -b blocks/blk_10000_blocks_2048_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/10000____2048.txt --dt 0 --tagload tags/wtagskey_10000_2048.dat --ibfload preproc/preproc_10000_2048.data
python driver.py -b blocks/blk_10000_blocks_4096_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/10000____4096.txt --dt 0 --tagload tags/wtagskey_10000_4096.dat --ibfload preproc/preproc_10000_4096.data
python driver.py -b blocks/blk_10000_blocks_8192_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/10000____8192.txt --dt 0 --tagload tags/wtagskey_10000_8192.dat --ibfload preproc/preproc_10000_8192.data

sleep 10

python driver.py -b blocks/blk_100000_blocks_1024_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/100000____1024.txt --dt 0 --tagload tags/wtagskey_100000_1024.dat --ibfload preproc/preproc_100000_1024.data

python driver.py -b blocks/blk_500000_blocks_1024_sizeBytes.dat -g generator.txt -k 6 -n 1024 -w 8 --task 1 -r runs/500000____1024.txt --dt 0 --tagload tags/wtagskey_500000_1024.dat --ibfload preproc/preproc_500000_1024.data