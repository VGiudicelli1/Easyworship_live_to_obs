# Easyworship_live_to_obs

The aim of this project is to extract informations from the current slide (live) of Easyworship to a file text. This file can be used as an text source in OSB or other streaming software.

I inspire myself from this github project [https://github.com/mikenor/ew2vm.git](https://github.com/mikenor/ew2vm.git) who exports frame title to an other streaming software.

> [!WARNING]
> As Michael Norton says about his project:
>
> > Because this program is critically dependent on unsupported use of an undocumented proprietary API for its core functionality, it should be considered highly experimental at all times. Please consider supporting [a feature request for an official EasyWorship API](https://support.easyworship.com/support/discussions/topics/6000033648).
>
> This is the same with my project. Please refere to the section [Compatibilities](#compatibilities) to see which version of Easyworship are compatibles or not. If you try with an other version, please contat-me so I can update this list.

## Compatibilities

| Easyworship version |       Compatible        |
| :-----------------: | :---------------------: |
|       unknow        | I hope because i use it |

| OBS version |       Compatible        |
| :---------: | :---------------------: |
|   unknow    | I hope because i use it |

## Status

|    date    |             status              |
| :--------: | :-----------------------------: |
| 2024.06.02 | In development, not operational |

## Build app with venv

### preparing venv

Create envir
`python3 -m venv envir`

Use envir
`source envir/bin/activate`

Download dependencies in envir
`pip install -r envir/requirements.txt`

### build app

#### MakeFile

Use `make` to build app

#### Old method

Create executable
`pyinstaller -F --paths envir/lib/python3.8/site-packages src/main.py --clean`

Create app (macos)
`mkdir dist/ew_to_txt.app; cp dist/main dist/ew_to_txt.app/ew_to_txt`

OR directly create app (macos):
`pyinstaller -w --paths envir/lib/python3.8/site-packages --icon images/ew_to_obs.png src/main.py --clean -y -n ew_to_txt`

Then, insert files from directory `public`

### DEV

Install tools (`pip-compile`) :
`pip install pip-tools`

Set all dependencies in `requirements.in`

Update `requirements.txt` : `pip-compile`  
Synchronize pip : `pip-sync`
