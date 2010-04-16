all:

check: all
	python -m CoverageTestRunner --ignore-missing-from=without-tests
	rm .coverage
	
clean:
	rm -f .coverage *.py[co] btree/*.py[co]
