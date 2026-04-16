#!/bin/bash
python tracker.py readme
git add README.md
git add --all
git commit -m 'updated worktime'
git push
