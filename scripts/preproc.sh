#!/bin/bash
cd ../src;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_100_blocks_1024_sizeBytes.dat -g generator.txt -k 4 -n 1024 -w 8 --task 200 -r runs/5____1024.txt  --tagload tags/tags_100_1024.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_1000_blocks_1024_sizeBytes.dat -g generator.txt -k 4 -n 1024 -w 8 --task 200 -r runs/5____1024.txt  --tagload tags/tags_1000_1024.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_10000_blocks_1024_sizeBytes.dat -g generator.txt -k 4 -n 1024 -w 8 --task 200 -r runs/5____1024.txt  --tagload tags/tags_10000_1024.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_100000_blocks_1024_sizeBytes.dat -g generator.txt -k 4 -n 1024 -w 8 --task 200 -r runs/5____1024.txt  --tagload tags/tags_100000_1024.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_500000_blocks_1024_sizeBytes.dat -g generator.txt -k 4 -n 1024 -w 8 --task 200 -r runs/5____1024.txt  --tagload tags/tags_500000_1024.dat --dt 1 --preprocmode;

python -m cProfile -o stat.prof  driver.py -b blocks/blk_100_blocks_2048_sizeBytes.dat -g generator.txt -k 4 -n 2048 -w 8 --task 200 -r runs/5____2048.txt  --tagload tags/tags_100_2048.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_1000_blocks_2048_sizeBytes.dat -g generator.txt -k 4 -n 2048 -w 8 --task 200 -r runs/5____2048.txt  --tagload tags/tags_1000_2048.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_10000_blocks_2048_sizeBytes.dat -g generator.txt -k 4 -n 2048 -w 8 --task 200 -r runs/5____2048.txt  --tagload tags/tags_10000_2048.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_100000_blocks_2048_sizeBytes.dat -g generator.txt -k 4 -n 2048 -w 8 --task 200 -r runs/5____2048.txt  --tagload tags/tags_100000_2048.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_500000_blocks_2048_sizeBytes.dat -g generator.txt -k 4 -n 2048 -w 8 --task 200 -r runs/5____2048.txt  --tagload tags/tags_500000_2048.dat --dt 1 --preprocmode;

python -m cProfile -o stat.prof  driver.py -b blocks/blk_100_blocks_4096_sizeBytes.dat -g generator.txt -k 4 -n 4096 -w 8 --task 200 -r runs/5____4096.txt  --tagload tags/tags_100_4096.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_1000_blocks_4096_sizeBytes.dat -g generator.txt -k 4 -n 4096 -w 8 --task 200 -r runs/5____4096.txt  --tagload tags/tags_1000_4096.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_10000_blocks_4096_sizeBytes.dat -g generator.txt -k 4 -n 4096 -w 8 --task 200 -r runs/5____4096.txt  --tagload tags/tags_10000_4096.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_100000_blocks_4096_sizeBytes.dat -g generator.txt -k 4 -n 4096 -w 8 --task 200 -r runs/5____4096.txt  --tagload tags/tags_100000_4096.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_500000_blocks_4096_sizeBytes.dat -g generator.txt -k 4 -n 4096 -w 8 --task 200 -r runs/5____4096.txt  --tagload tags/tags_500000_4096.dat --dt 1 --preprocmode;

python -m cProfile -o stat.prof  driver.py -b blocks/blk_100_blocks_8192_sizeBytes.dat -g generator.txt -k 4 -n 8192 -w 8 --task 200 -r runs/5____8192.txt  --tagload tags/tags_100_8192.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_1000_blocks_8192_sizeBytes.dat -g generator.txt -k 4 -n 8192 -w 8 --task 200 -r runs/5____8192.txt  --tagload tags/tags_1000_8192.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_10000_blocks_8192_sizeBytes.dat -g generator.txt -k 4 -n 8192 -w 8 --task 200 -r runs/5____8192.txt  --tagload tags/tags_10000_8192.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_100000_blocks_8192_sizeBytes.dat -g generator.txt -k 4 -n 8192 -w 8 --task 200 -r runs/5____8192.txt  --tagload tags/tags_100000_8192.dat --dt 1 --preprocmode;
python -m cProfile -o stat.prof  driver.py -b blocks/blk_500000_blocks_8192_sizeBytes.dat -g generator.txt -k 4 -n 8192 -w 8 --task 200 -r runs/5____8192.txt  --tagload tags/tags_500000_8192.dat --dt 1 --preprocmode;
