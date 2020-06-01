#!/bin/bash
parent=$(dirname "${PWD}")

PYTHONPATH="${PYTHONPATH}:${parent}" pytest tests/test*
