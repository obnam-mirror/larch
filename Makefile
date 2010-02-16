all:

check: all
	python -m CoverageTestRunner
	rm .coverage
	
clean:
	rm -f .coverage *.pyc *.pyo
