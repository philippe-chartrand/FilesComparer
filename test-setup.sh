#!/bin/bash
# Saving /home/philippe/Dev/FilesComparer/A infos to cache b4e8bfaa25fa562fc9ae580031999186
# Saving /home/philippe/Dev/FilesComparer/B infos to cache 15f9d924422f48ba9df8ee750ed3951a
rm b4e8bfaa25fa562fc9ae580031999186
rm 15f9d924422f48ba9df8ee750ed3951a
git checkout A/moved/same.txt
git checkout A/changed-in-destination.txt
git checkout A/changed-in-source.txt
git checkout A/new.txt
git checkout A/same.txt
git checkout A/same/fichier*txt

git checkout B/to-be-moved/same.txt
git checkout B/changed-in-destination.txt
git checkout B/changed-in-source.txt
git checkout B/old.txt
git checkout B/same.txt
git checkout B/same/fichier*txt

touch A/changed-in-source.txt
touch B/changed-in-destination.txt

rm B/new.txt 2>/dev/null
rm B/moved/same.txt 2>/dev/null
rmdir B/moved 2>/dev/null

wc -l  add.sh move.sh update.sh restore.sh remove.sh
#  1 add.sh
#  1 move.sh
#  3 update.sh
#  4 restore.sh
#  1 remove.sh
# 10 total
