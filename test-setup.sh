#!/bin/bash

# setup

./comparer.py A B cleanup 1>/dev/null 2>/dev/null

git checkout A/moved/same.txt 2>/dev/null
git checkout A/changed-in-destination.txt 2>/dev/null
git checkout A/changed-in-source.txt 2>/dev/null
git checkout A/new.txt 2>/dev/null
git checkout A/same.txt 2>/dev/null
git checkout A/same/fichier*txt 2>/dev/null

git checkout B/to-be-moved/same.txt 2>/dev/null
git checkout B/changed-in-destination.txt 2>/dev/null
git checkout B/changed-in-source.txt 2>/dev/null
git checkout B/old.txt 2>/dev/null
git checkout B/same.txt 2>/dev/null
git checkout B/same/fichier*txt 2>/dev/null


touch A/changed-in-source.txt 2>/dev/null
touch B/changed-in-destination.txt 2>/dev/null

rm B/new.txt 2>/dev/null 2>/dev/null
rm B/moved/same.txt 2>/dev/null 2>/dev/null
rmdir B/moved 2>/dev/null 2>/dev/null

# tests

init=$(./comparer.py A B| grep -c ' files scanned')
a=$(./comparer.py A B| grep -e '^unchanged:')
b=$(./comparer.py A B add true |grep 'added:')
c=$(./comparer.py A B move true |grep -e '^moved:')
d=$(./comparer.py A B update true | grep 'source:')
e=$(./comparer.py A B restore true| grep 'destination:')
f=$(./comparer.py A B remove true| grep -e '^removed:')
g=$(./comparer.py A B| grep -e '^unchanged:')
h=$(./comparer.py A B cleanup |grep -c 'Removing')

a=$(echo $a|cut -f2 -d:|cut -f2 -d' ')
b=$(echo $b|cut -f2 -d:|cut -f2 -d' ')
c=$(echo $c|cut -f2 -d:|cut -f2 -d' ')
d=$(echo $d|cut -f2 -d:|cut -f2 -d' ')
e=$(echo $e|cut -f2 -d:|cut -f2 -d' ')
f=$(echo $f|cut -f2 -d:|cut -f2 -d' ')
g=$(echo $g|cut -f2 -d:|cut -f2 -d' ')

if [[ $init -eq 2 ]]; then
    echo "indexing ok ($init)"
fi
if [[ $a -eq 102 ]]; then
    echo "unchanged ok ($a)"
fi
if [[ $b -eq 1 ]]; then
    echo "add ok ($b)"
fi
if [[ $c -eq 1 ]]; then
    echo "move ok ($c)"
fi
if [[ $d -eq 1 ]]; then
    echo "update ok ($d)"
fi
if [[ $e -eq 1 ]]; then
    echo "restore ok ($e)"
fi
if [[ $f -eq 1 ]]; then
    echo "remove ok ($f)"
fi

if [[ $g -eq 106 ]]; then
    echo "all ok ($g)"
fi

if [[ $h -eq 2 ]]; then
    echo "cleanup ok ($h)"
fi

# teardown
git restore A/changed-in-destination.txt 2>/dev/null
git restore B/changed-in-source.txt 2>/dev/null
git restore B/old.txt 2>/dev/null
git restore B/to-be-moved/same.txt 2>/dev/null
