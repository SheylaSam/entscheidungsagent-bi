.PHONY: config test

config:
	python -m scripts.render_streamlit_config

test:
	pytest tests/ -v
