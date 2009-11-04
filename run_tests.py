#!/usr/bin/env python
# encoding: utf-8

import warnings
import nose

# Ignore import problems for optional features
warnings.filterwarnings("ignore", "This module needs")

nose.run()
