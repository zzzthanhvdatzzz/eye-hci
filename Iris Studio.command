#!/bin/zsh
cd -- "${0:A:h}" || exit 1
exec .venv/bin/python step6_hci.py --desktop
