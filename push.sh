#!/bin/bash
python3 tracker.py readme
git add README.md
git add --all
git commit -m 'updated worktime'
git push
