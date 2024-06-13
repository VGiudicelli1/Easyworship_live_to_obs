# Build app with venv

## preparing venv

Create envir
`python3 -m venv envir`

Use envir
`source envir/bin/activate`

Download dependencies in envir
`pip install -r envir/requirements.txt`

## build app

Create executable
`pyinstaller -F --paths envir/lib/python3.8/site-packages src/main.py --clean`

Create app (macos)
`mkdir dist/ew_to_txt.app; cp dist/main dist/ew_to_txt.app/ew_to_txt`

OR directly create app (macos):
`pyinstaller -w --paths envir/lib/python3.8/site-packages --icon images/ew_to_obs.png src/main.py --clean -y -n ew_to_txt`

## DEV

Install tools (`pip-compile`) :
`pip install pip-tools`

Set all dependencies in `envir/requirements.in`

Update `requirements.txt` : `cd envir; pip-compile; cd ..`
