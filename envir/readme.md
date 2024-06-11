# Build app with venv

## preparing venv

Create envir
`python3 -m venv envir`

Use envir
`source envir/bin/activate`

Download dependencies in envir
`pip install -r envir/requirements.txt`

## build app

Create app
`pyinstaller -F --paths envir/lib/python3.8/site-packages src/main.py --clean`

## DEV

Install tools (`pip-compile`) :
`pip install pip-tools`

Set all dependencies in `envir/requirements.in`

Update `requirements.txt` : `cd envir; pip-compile; cd ..`
