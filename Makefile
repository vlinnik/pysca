
clean:
	@find ./ -iname __pycache__  | xargs rm -rf

package:
	python -m build --wheel
	pip install ./dist/pysca-`git-versioner --short --python`-py3-none-any.whl --force-reinstall

release: 
	git-versioner --tag
	python -m build --wheel
	pip install ./dist/pysca-`git-versioner --short --python`-py3-none-any.whl --force-reinstall


.PHONY: dirs
