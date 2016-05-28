#!/usr/bin/env python

from setuptools import setup, find_packages

required_modules = [
	'audiogen',
	'PyAudio',
	]

with open("README.rst", "rb") as f:
	readme = f.read()

setup(
	name="koch",
	version="0.0.2",
	description="Koch method Morse code training program",
	author="Christopher H. Casebeer",
	author_email="",
	url="https://github.com/casebeer/koch",

	packages=find_packages(exclude='tests'),
	install_requires=required_modules,

	tests_require=["nose"],
	test_suite="nose.collector",

	entry_points={
		"console_scripts": [
			"koch = koch.koch:main"
		]
	},

	long_description=readme,
	classifiers=[
		"Environment :: Console",
		"Topic :: Multimedia :: Sound/Audio",
		"Topic :: Communications :: Ham Radio",
		"Programming Language :: Python :: 2.7",
	]
)
