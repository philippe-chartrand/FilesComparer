#!/bin/bash
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