dist/ew_to_txt.app: src/*.py
	rm -rf dist
	pyinstaller -F -w --paths lib/python3.8/site-packages --icon images/ew_to_obs.png src/main.py --clean -y -n ew_to_obs
	cp -r public dist/ew_to_obs.app/Contents/MacOS