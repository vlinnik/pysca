
clean:
	@find ./ -iname __pycache__  | xargs rm -rf

package:
	rm -rfd build/*
	python -m build --wheel
	pip install ./dist/pysca-`python -m setuptools_scm --strip-dev`-py3-none-any.whl --force-reinstall

release: 
	git-versioner --tag
	python -m build --wheel
	pip install ./dist/pysca-`git-versioner --short --python`-py3-none-any.whl --force-reinstall


.PHONY: dirs
