#!/bin/bash
# unit testing for comparer.py

function setup(){
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
}

function assert(){
  value=$1
  expected=$2
  message="$3"
  if [[ $value -eq $expected ]]; then
    echo "$message ok ($value)"
  else
    echo "$message: expected $expected, got $value"
    exit 1
  fi
}

function tests(){
  init=$(./comparer.py A B| grep -c ' files scanned')
  init1=$(./comparer.py A B| grep -e '^dir_one:')
  init2=$(./comparer.py A B| grep -e '^dir_two:')
  a=$(./comparer.py A B| grep -e '^unchanged:')
  b=$(./comparer.py A B add true |grep 'added:')
  b2=$(./comparer.py A B| grep -e '^dir_two:')
  c=$(./comparer.py A B move true |grep -e '^moved:')
  d=$(./comparer.py A B update true | grep 'source:')
  e=$(./comparer.py A B restore true| grep 'destination:')
  f=$(./comparer.py A B remove true| grep -e '^removed:')
  f2=$(./comparer.py A B| grep -e '^dir_two:')
  g=$(./comparer.py A B| grep -e '^unchanged:')
  h=$(./comparer.py A B cleanup |grep -c 'Removing')

  init1=$(echo $init1|cut -f2 -d:|cut -f2 -d' ')
  init2=$(echo $init2|cut -f2 -d:|cut -f2 -d' ')
  a=$(echo $a|cut -f2 -d:|cut -f2 -d' ')
  b=$(echo $b|cut -f2 -d:|cut -f2 -d' ')
  b2=$(echo $b2|cut -f2 -d:|cut -f2 -d' ')

  c=$(echo $c|cut -f2 -d:|cut -f2 -d' ')
  d=$(echo $d|cut -f2 -d:|cut -f2 -d' ')
  e=$(echo $e|cut -f2 -d:|cut -f2 -d' ')
  f=$(echo $f|cut -f2 -d:|cut -f2 -d' ')
  f2=$(echo $f2|cut -f2 -d:|cut -f2 -d' ')

  g=$(echo $g|cut -f2 -d:|cut -f2 -d' ')

  assert $init1 106 dir_one
  assert $init2 106 "dir two after add"
  assert $init 2 indexing
  assert $a 102 unchanged

  assert $b 1 add
  assert $b2 107 dir_two

  assert $c 1  move
  assert $d 1  update
  assert $e 1  restore
  assert $f 1  remove
  assert $f2 106 "dir two after remove"

  assert $g 106  all
  assert $h 2  cleanup
}

function teardown(){
  git restore A/changed-in-destination.txt 2>/dev/null
  git restore B/changed-in-source.txt 2>/dev/null
  git restore B/old.txt 2>/dev/null
  git restore B/to-be-moved/same.txt 2>/dev/null
}


setup
tests
teardown
setup